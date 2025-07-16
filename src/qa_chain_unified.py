"""Unified QA Chain with all necessary features consolidated"""
from typing import List, Dict, Any, Optional, Tuple
import time
import json
from enum import Enum
from pathlib import Path
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import Config
from src.local_llm import OptimizedLLM
from src.document_processor import DocumentProcessor
from src.web_search import WebSearcher, SearchResult
from src.memory_safe_embeddings import MemorySafeEmbeddings
import os


class QueryIntent(Enum):
    """Query intent classification"""
    DOCUMENT_QUESTION = "document_question"
    CASUAL_CHAT = "casual_chat"
    CLARIFICATION = "clarification"
    WEB_SEARCH = "web_search"
    AMBIGUOUS = "ambiguous"


class UnifiedQAChain:
    """Unified QA Chain with intelligent routing and all necessary features"""
    
    def __init__(self):
        self.config = Config()
        self.doc_processor = DocumentProcessor()
        self.llm = None  # Lazy load
        self.web_searcher = WebSearcher()
        self.embeddings = None  # Lazy load
        
        # Don't initialize embeddings yet - will be done on demand
        
        # Classification patterns for quick routing
        self.casual_patterns = [
            "hello", "hi", "hey", "how are you", "what's up", "good morning",
            "good afternoon", "good evening", "thanks", "thank you", "bye",
            "goodbye", "how's it going", "how's your day", "nice to meet"
        ]
        
        self.document_patterns = [
            "document", "file", "pdf", "csv", "spreadsheet", "invoice", "total",
            "amount", "page", "section", "paragraph", "quote", "extract", "find",
            "search", "what does", "according to", "in the", "show me"
        ]
        
        self.web_patterns = [
            "weather", "news", "current", "today", "latest", "stock", "price",
            "real-time", "live", "update", "happening now"
        ]
        
        # Initialize model parameters
        self._init_model_params()
    
    def _ensure_llm_initialized(self):
        """Ensure LLM is initialized when needed"""
        if self.llm is None:
            self.llm = OptimizedLLM(self.config)
    
    def _ensure_embeddings_initialized(self):
        """Ensure embeddings are initialized when needed"""
        if self.embeddings is None:
            self._init_embeddings()
    
    def _init_embeddings(self):
        """Initialize embeddings with memory safety"""
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")
            
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            
            try:
                base_embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.EMBEDDING_MODEL,
                    model_kwargs={
                        'device': 'cpu',
                        'trust_remote_code': False,
                        'local_files_only': True
                    },
                    encode_kwargs={'normalize_embeddings': True}
                )
            except Exception:
                base_embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu', 'trust_remote_code': False},
                    encode_kwargs={'normalize_embeddings': True}
                )
            
            self.embeddings = MemorySafeEmbeddings(
                base_embeddings, 
                batch_size=getattr(self.config, 'EMBEDDING_BATCH_SIZE', 2)
            )
    
    def _init_model_params(self):
        """Initialize model parameters from config"""
        self.model_params_file = Path(__file__).parent / "model_config.json"
        try:
            with open(self.model_params_file, 'r') as f:
                self.model_params = json.load(f)
        except:
            self.model_params = {}
    
    def classify_query_intent(
        self,
        question: str,
        use_llm: bool = False
    ) -> Tuple[QueryIntent, float]:
        """
        Classify the intent of a query
        
        Args:
            question: The user's question
            use_llm: Whether to use LLM for classification (slower but more accurate)
            
        Returns:
            Tuple of (intent, confidence)
        """
        question_lower = question.lower().strip()
        
        # Quick pattern-based classification first
        # Check for casual conversation
        if any(pattern in question_lower for pattern in self.casual_patterns):
            if len(question_lower.split()) < 10:  # Short casual queries
                return QueryIntent.CASUAL_CHAT, 0.9
        
        # Check for document-related queries
        doc_score = sum(1 for pattern in self.document_patterns if pattern in question_lower)
        if doc_score >= 2:
            return QueryIntent.DOCUMENT_QUESTION, 0.8
        
        # Check for web search needs
        if any(pattern in question_lower for pattern in self.web_patterns):
            return QueryIntent.WEB_SEARCH, 0.7
        
        # If pattern matching is inconclusive and LLM classification is enabled
        if use_llm and doc_score == 0:
            return self._classify_with_llm(question)
        
        # Default to document question with low confidence
        return QueryIntent.DOCUMENT_QUESTION, 0.5
    
    def _classify_with_llm(self, question: str) -> Tuple[QueryIntent, float]:
        """Use a small LLM to classify the query intent"""
        try:
            classifier_llm = Ollama(
                model="mistral",
                temperature=0.1,
                num_ctx=512
            )
            
            classification_prompt = f"""Classify this query into ONE category:
1. DOCUMENT_QUESTION - Questions about specific documents, files, or their contents
2. CASUAL_CHAT - Greetings, small talk, general conversation
3. WEB_SEARCH - Questions requiring current information, news, or web data
4. CLARIFICATION - Unclear questions that need more context

Query: "{question}"

Respond with ONLY the category name and confidence (0-1), like: CASUAL_CHAT 0.9

Classification:"""
            
            response = classifier_llm.invoke(classification_prompt).strip()
            
            parts = response.split()
            if len(parts) >= 2:
                intent_str = parts[0].upper()
                confidence = float(parts[1])
                
                intent_map = {
                    "DOCUMENT_QUESTION": QueryIntent.DOCUMENT_QUESTION,
                    "CASUAL_CHAT": QueryIntent.CASUAL_CHAT,
                    "WEB_SEARCH": QueryIntent.WEB_SEARCH,
                    "CLARIFICATION": QueryIntent.CLARIFICATION
                }
                
                intent = intent_map.get(intent_str, QueryIntent.AMBIGUOUS)
                return intent, confidence
                
        except Exception as e:
            print(f"LLM classification failed: {e}")
        
        return QueryIntent.AMBIGUOUS, 0.3
    
    def answer_question(
        self,
        question: str,
        document_id: str = None,
        use_web: bool = False,
        max_results: int = 15,
        model_name: str = None,
        temperature: float = None,
        streaming: bool = True  # Default to streaming for better UX
    ) -> Dict[str, Any]:
        """
        Main entry point for answering questions with intelligent routing
        
        Args:
            question: The user's question
            document_id: Document ID to search in, or "all" for unified search
            use_web: Whether to include web search results
            max_results: Maximum number of results to retrieve
            model_name: Optional model override
            temperature: Optional temperature override
            streaming: Whether to return streaming response
            
        Returns:
            Dict containing answer, sources, metadata
        """
        start_time = time.time()
        
        # Classify the query intent
        intent, confidence = self.classify_query_intent(question, use_llm=False)
        print(f"Query classified as: {intent.value} (confidence: {confidence})")
        
        # Route based on intent
        if intent == QueryIntent.CASUAL_CHAT and confidence > 0.7:
            result = self._handle_casual_chat(
                question, model_name, temperature, start_time
            )
        elif intent == QueryIntent.WEB_SEARCH or (use_web and confidence < 0.5):
            result = self._handle_web_search(
                question, max_results, model_name, temperature, start_time
            )
        else:
            result = self._handle_document_question(
                question, document_id, use_web, max_results, 
                model_name, temperature, start_time, intent, confidence
            )
        
        # Add intent information to result
        result['query_intent'] = intent.value
        result['intent_confidence'] = confidence
        
        if streaming:
            return self._convert_to_streaming(result)
        
        return result
    
    def _handle_casual_chat(
        self,
        question: str,
        model_name: str,
        temperature: float,
        start_time: float
    ) -> Dict[str, Any]:
        """Handle casual conversation without document context"""
        llm = self._get_llm(
            model_name, 
            temperature if temperature is not None else 0.7
        )
        
        chat_prompt = f"""You are a helpful and friendly AI assistant. Respond naturally to the user's message.

User: {question}
Assistant:"""
        
        response = llm.invoke(chat_prompt)
        
        return {
            'answer': response,
            'sources': [],
            'processing_time': time.time() - start_time,
            'document_id': 'none',
            'used_web_search': False
        }
    
    def _handle_web_search(
        self,
        question: str,
        max_results: int,
        model_name: str,
        temperature: float,
        start_time: float
    ) -> Dict[str, Any]:
        """Handle web search queries"""
        web_docs = self._search_web_for_context(question, num_results=max_results)
        
        if not web_docs:
            return {
                'answer': "I couldn't find relevant information on the web for your query.",
                'sources': [],
                'processing_time': time.time() - start_time,
                'document_id': 'web_only',
                'used_web_search': True
            }
        
        context = "\n\n".join([doc.page_content for doc in web_docs[:3]])
        llm = self._get_llm(model_name, temperature)
        
        web_prompt = f"""Based on the following web search results, answer the user's question.

Web search results:
{context}

Question: {question}

Answer based on the web search results above:"""
        
        response = llm.invoke(web_prompt)
        sources = self._format_sources(web_docs)
        
        return {
            'answer': response,
            'sources': sources,
            'processing_time': time.time() - start_time,
            'document_id': 'web_only',
            'used_web_search': True
        }
    
    def _handle_document_question(
        self,
        question: str,
        document_id: str,
        use_web: bool,
        max_results: int,
        model_name: str,
        temperature: float,
        start_time: float,
        intent: QueryIntent,
        confidence: float
    ) -> Dict[str, Any]:
        """Handle document-based questions"""
        # Create appropriate prompt
        prompt_template = self._create_flexible_prompt(intent, confidence)
        
        # Get retriever
        if not document_id or document_id == "web_only":
            retriever = self._get_web_only_retriever(question, max_results)
        elif document_id in ["unified", "all"]:
            try:
                from src.unified_document_processor import UnifiedDocumentProcessor
                unified_processor = UnifiedDocumentProcessor()
                vector_store = unified_processor.load_unified_store()
                retriever = self._create_hybrid_retriever(vector_store, question, use_web, max_results)
            except ValueError:
                if use_web:
                    retriever = self._get_web_only_retriever(question, max_results)
                else:
                    raise
        else:
            try:
                vector_store = self.doc_processor.load_vector_store(document_id)
                retriever = self._create_hybrid_retriever(vector_store, question, use_web, max_results)
            except ValueError:
                if use_web:
                    retriever = self._get_web_only_retriever(question, max_results)
                else:
                    raise
        
        # Get LLM
        llm = self._get_llm(model_name, temperature)
        
        # Create QA chain
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={
                "prompt": prompt_template,
                "verbose": False
            }
        )
        
        # Run the chain
        result = qa_chain.invoke({"query": question})
        
        # Format response
        source_docs = result.get('source_documents', [])
        sources = self._format_sources(source_docs)
        
        return {
            'answer': result.get('result', ''),
            'sources': sources,
            'processing_time': time.time() - start_time,
            'document_id': document_id,
            'used_web_search': use_web
        }
    
    def _create_flexible_prompt(self, intent: QueryIntent, confidence: float) -> PromptTemplate:
        """Create a flexible prompt based on query intent and confidence"""
        metadata = self._load_document_metadata()
        
        doc_list = ""
        if metadata and 'documents' in metadata:
            doc_list = "\nAvailable documents:\n"
            for doc in metadata['documents']:
                file_type = doc.get('file_type', 'unknown').upper()
                pages = doc.get('pages', 'unknown')
                doc_list += f"- {doc['filename']} ({file_type}, {pages} page{'s' if pages != 1 else ''})\n"
        
        if confidence < 0.6:
            template = f"""You are a helpful AI assistant.{doc_list}

Context (may or may not be relevant):
{{context}}

Question: {{question}}

Instructions:
- If the context contains relevant information, use it to answer the question
- If the context doesn't seem relevant to the question, provide a helpful response based on general knowledge
- Be clear about whether your answer comes from the provided documents or general knowledge

Answer:"""
        else:
            template = f"""You are a helpful AI assistant analyzing documents.{doc_list}

Context from documents:
{{context}}

Question: {{question}}

Instructions:
- First check if the provided context is relevant to the question
- If relevant, answer based on the context and cite specific information
- If not relevant or if you can't find the information, say so clearly and provide any helpful general information
- For specific values (numbers, dates, names), only report what's explicitly in the context

Answer:"""
        
        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def _get_llm(self, model_name: str = None, temperature: float = None):
        """Get LLM instance with appropriate parameters"""
        # Ensure LLM system is initialized
        self._ensure_llm_initialized()
        
        model = model_name or self.config.LOCAL_LLM_MODEL
        temp = temperature if temperature is not None else self.config.TEMPERATURE
        
        model_params = self._get_model_parameters(model)
        
        return Ollama(
            model=model,
            temperature=temp,
            num_ctx=model_params.get("num_ctx", 4096)
        )
    
    def _get_model_parameters(self, model_name: str) -> Dict[str, Any]:
        """Get parameters for a specific model"""
        for model_info in self.model_params.get("models", []):
            if model_info["model"] == model_name:
                return model_info["parameters"]
        
        return {
            "num_ctx": 4096,
            "num_thread": 8,
            "repeat_penalty": 1.1,
            "stop": ["Human:", "Question:"]
        }
    
    def _create_hybrid_retriever(self, vector_store, question: str, use_web: bool, max_results: int):
        """Create a hybrid retriever that combines vector store and web search"""
        if not use_web:
            return vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": max_results}
            )
        
        # Get documents from vector store
        vector_docs = vector_store.similarity_search(question, k=max_results)
        
        # Get web search results
        web_docs = self._search_web_for_context(question, num_results=3)
        
        # Combine results
        all_docs = vector_docs + web_docs
        
        # Create temporary vector store with combined results
        if all_docs:
            texts = [doc.page_content for doc in all_docs]
            metadatas = [doc.metadata for doc in all_docs]
            
            # Ensure embeddings are initialized
            self._ensure_embeddings_initialized()
            
            temp_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embeddings,
                metadatas=metadatas
            )
            
            return temp_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": min(len(all_docs), max_results)}
            )
        
        return vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": max_results}
        )
    
    def _get_web_only_retriever(self, question: str, max_results: int):
        """Get retriever for web-only searches"""
        web_docs = self._search_web_for_context(question, num_results=max_results)
        
        if not web_docs:
            class EmptyRetriever:
                def get_relevant_documents(self, query: str):
                    return []
                def as_retriever(self, **kwargs):
                    return self
            return EmptyRetriever()
        
        texts = [doc.page_content for doc in web_docs]
        metadatas = [doc.metadata for doc in web_docs]
        
        # Ensure embeddings are initialized
        self._ensure_embeddings_initialized()
        
        temp_vector_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas
        )
        
        return temp_vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": min(len(web_docs), 3)}
        )
    
    def _search_web_for_context(self, query: str, num_results: int = 3) -> List[Document]:
        """Search web and convert results to documents"""
        results = self.web_searcher.search(query, num_results=num_results)
        
        documents = []
        for result in results:
            doc = Document(
                page_content=f"{result.title}\n\n{result.content}",
                metadata={
                    "source": result.url,
                    "title": result.title,
                    "source_type": "web"
                }
            )
            documents.append(doc)
        
        return documents
    
    def _format_sources(self, source_docs: List[Document]) -> List[Dict[str, Any]]:
        """Format source documents for response"""
        sources = []
        seen_sources = set()
        
        for doc in source_docs:
            source = doc.metadata.get('source', '')
            if source and source not in seen_sources:
                seen_sources.add(source)
                sources.append({
                    'source': source,
                    'title': doc.metadata.get('title', 'Document'),
                    'type': doc.metadata.get('source_type', 'document')
                })
        
        return sources
    
    def _load_document_metadata(self) -> Dict[str, Any]:
        """Load metadata about available documents"""
        try:
            metadata_path = Path(self.config.VECTOR_STORE_DIR) / "unified_store.metadata"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Could not load document metadata: {e}")
        return {}
    
    def _convert_to_streaming(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Convert result to streaming format for API compatibility"""
        def generate():
            answer = result['answer']
            chunk_size = 20
            
            # Stream answer in chunks
            for i in range(0, len(answer), chunk_size):
                chunk = answer[i:i+chunk_size]
                yield f"data: {json.dumps({'token': chunk})}\n\n"
            
            # Send final message with metadata
            final_data = {
                'done': True,
                'sources': result['sources'],
                'processing_time': result['processing_time'],
                'document_id': result['document_id'],
                'used_web_search': result['used_web_search'],
                'query_intent': result.get('query_intent'),
                'intent_confidence': result.get('intent_confidence')
            }
            yield f"data: {json.dumps(final_data)}\n\n"
        
        return {
            'stream': generate(),
            'is_streaming': True
        }