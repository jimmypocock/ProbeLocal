"""Enhanced QA Chain with Web Search Integration"""
from typing import List, Dict, Any, Optional
import time
import json
import os
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import Ollama as LangchainOllama
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import Config
from src.local_llm import OptimizedLLM
from src.document_processor import DocumentProcessor
from src.web_search import WebSearcher, SearchResult
from src.qa_chain import QAChain


class EnhancedQAChain(QAChain):
    """QA Chain with web search capabilities"""
    
    def __init__(self):
        super().__init__()
        self.web_searcher = WebSearcher()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP,
            length_function=len
        )
        # Use the same embeddings as document processor
        # Suppress tokenization warnings
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")
            
            # Set environment variables to prevent HTTP requests
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.EMBEDDING_MODEL,
                    model_kwargs={
                        'device': 'cpu',
                        'trust_remote_code': False,
                        'local_files_only': True
                    },
                    encode_kwargs={'normalize_embeddings': True}
                )
            except Exception as e:
                # Fallback without local_files_only
                print(f"Warning: Could not load embeddings with local_files_only: {e}")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu', 'trust_remote_code': False},
                    encode_kwargs={'normalize_embeddings': True}
                )
        
    def _create_prompt_template(self) -> PromptTemplate:
        """Enhanced prompt that handles both document and web sources"""
        template = """You are analyzing information from multiple sources. When answering:
1. Prioritize information from the uploaded document if available
2. Use web search results to supplement or provide context
3. Clearly indicate which source you're using (📄 Document or 🌐 Web)
4. For numbers, amounts, or specific data, only report EXACT values found in the sources

Context from sources:
{context}

Question: {question}

Important: 
- Start your answer by indicating the primary source used
- If information comes from both sources, mention both
- If you cannot find specific information in either source, say so clearly

Answer:"""

        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )
    
    def _search_web_for_context(self, question: str, num_results: int = 3) -> List[Document]:
        """Search the web and convert results to Documents"""
        search_results = self.web_searcher.search_and_extract(question, num_results)
        
        documents = []
        for i, result in enumerate(search_results):
            # Create a document from each search result
            content = f"Title: {result.title}\nURL: {result.url}\n"
            if result.content:
                content += f"Content: {result.content[:1000]}..."
            else:
                content += f"Snippet: {result.snippet}"
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": "web",
                    "url": result.url,
                    "title": result.title,
                    "search_rank": i + 1
                }
            )
            documents.append(doc)
            
        return documents
    
    def _create_hybrid_retriever(self, vector_store, question: str, use_web: bool, web_weight: float = 0.3):
        """Create a retriever that combines document and web sources"""
        if not use_web:
            # Just use document retriever
            return vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 5}
            )
        
        # Get documents from vector store
        doc_retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 3}
        )
        doc_results = doc_retriever.get_relevant_documents(question)
        
        # Get web results
        web_docs = self._search_web_for_context(question, num_results=2)
        
        # Combine results (documents first, then web)
        combined_docs = doc_results + web_docs
        
        # Create a simple retriever that returns our combined docs
        class HybridRetriever:
            def get_relevant_documents(self, query: str):
                return combined_docs
            
            def as_retriever(self, **kwargs):
                return self
        
        return HybridRetriever()
    
    def answer_question_with_web(
        self,
        question: str,
        document_id: str,
        use_web: bool = False,
        max_results: int = 5,
        stream: bool = False,
        model_name: str = None,
        temperature: float = None
    ) -> Dict[str, Any]:
        """Answer question using document and optionally web search"""
        start_time = time.time()
        
        # If no document, just use web search
        if not document_id or document_id == "web_only":
            return self._answer_from_web_only(
                question, max_results, stream, model_name, temperature
            )
        
        # Validate document exists
        try:
            vector_store = self.doc_processor.load_vector_store(document_id)
        except ValueError as e:
            if use_web:
                # Fall back to web-only search
                return self._answer_from_web_only(
                    question, max_results, stream, model_name, temperature
                )
            else:
                raise e
        
        # Use specified model or default
        llm = self._get_llm_for_model(model_name, temperature)
        
        try:
            # Create hybrid retriever if web search is enabled
            retriever = self._create_hybrid_retriever(
                vector_store, question, use_web
            )
            
            # Configure callbacks for streaming
            callbacks = [StreamingStdOutCallbackHandler()] if stream else []
            
            # Create QA chain
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": self.prompt_template,
                    "verbose": False
                },
                callbacks=callbacks
            )
            
            # Get answer
            result = qa_chain({"query": question})
            
            # Format sources
            sources = self._format_sources(result['source_documents'])
            
            processing_time = time.time() - start_time
            
            return {
                'answer': result['result'].strip(),
                'sources': sources,
                'document_id': document_id,
                'processing_time': processing_time,
                'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL,
                'used_web_search': use_web
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            return self._format_error_response(e, document_id, processing_time, model_name)
    
    def _answer_from_web_only(
        self,
        question: str,
        max_results: int,
        stream: bool,
        model_name: str,
        temperature: float
    ) -> Dict[str, Any]:
        """Answer question using only web search"""
        start_time = time.time()
        
        # Get web search results
        web_docs = self._search_web_for_context(question, num_results=max_results)
        
        if not web_docs:
            return {
                'answer': "I couldn't find any relevant information on the web for your question.",
                'sources': [],
                'document_id': 'web_only',
                'processing_time': time.time() - start_time,
                'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL,
                'used_web_search': True
            }
        
        # Create a temporary vector store from web results
        texts = [doc.page_content for doc in web_docs]
        metadatas = [doc.metadata for doc in web_docs]
        
        temp_vector_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas
        )
        
        # Use the base answer_question method with the temp store
        llm = self._get_llm_for_model(model_name, temperature)
        
        try:
            retriever = temp_vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": min(len(web_docs), 3)}
            )
            
            callbacks = [StreamingStdOutCallbackHandler()] if stream else []
            
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": self.prompt_template,
                    "verbose": False
                },
                callbacks=callbacks
            )
            
            result = qa_chain({"query": question})
            sources = self._format_sources(result['source_documents'])
            
            return {
                'answer': f"🌐 Web Search Results:\n\n{result['result'].strip()}",
                'sources': sources,
                'document_id': 'web_only',
                'processing_time': time.time() - start_time,
                'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL,
                'used_web_search': True
            }
            
        except Exception as e:
            return self._format_error_response(
                e, 'web_only', time.time() - start_time, model_name
            )
    
    def _get_llm_for_model(self, model_name: str, temperature: float) -> Any:
        """Get LLM instance for specified model"""
        if model_name and model_name != self.config.LOCAL_LLM_MODEL:
            try:
                model_params = self._get_model_parameters(model_name)
                return LangchainOllama(
                    model=model_name,
                    temperature=temperature if temperature is not None else self.config.TEMPERATURE,
                    top_p=self.config.TOP_P,
                    **model_params
                )
            except Exception as e:
                # Fallback to minimal config
                return LangchainOllama(
                    model=model_name,
                    temperature=temperature if temperature is not None else self.config.TEMPERATURE,
                    top_p=self.config.TOP_P,
                    num_ctx=1024
                )
        else:
            if temperature is not None and temperature != self.config.TEMPERATURE:
                return LangchainOllama(
                    model=self.config.LOCAL_LLM_MODEL,
                    temperature=temperature,
                    top_p=self.config.TOP_P,
                    num_ctx=self.config.MAX_CONTEXT_LENGTH
                )
            return self.llm
    
    def _format_sources(self, source_documents: List[Document]) -> List[Dict[str, Any]]:
        """Format source documents for response"""
        sources = []
        seen_sources = set()
        
        for doc in source_documents:
            # Create unique identifier
            if doc.metadata.get('source') == 'web':
                source_id = doc.metadata.get('url', 'unknown')
                source_type = 'web'
            else:
                page = doc.metadata.get('page', 'N/A')
                source_id = f"page_{page}"
                source_type = 'document'
            
            if source_id not in seen_sources:
                if source_type == 'web':
                    sources.append({
                        'type': 'web',
                        'title': doc.metadata.get('title', 'Web Page'),
                        'url': doc.metadata.get('url', ''),
                        'content': doc.page_content[:200] + "...",
                        'rank': doc.metadata.get('search_rank', 0)
                    })
                else:
                    sources.append({
                        'type': 'document',
                        'content': doc.page_content[:200] + "...",
                        'page': doc.metadata.get('page', 'N/A'),
                        'chunk_index': doc.metadata.get('chunk_index', 'N/A')
                    })
                seen_sources.add(source_id)
        
        return sources[:5]  # Limit to top 5 sources
    
    def _format_error_response(
        self,
        error: Exception,
        document_id: str,
        processing_time: float,
        model_name: str
    ) -> Dict[str, Any]:
        """Format error response"""
        error_msg = str(error)
        
        if "422" in error_msg:
            error_msg = f"Model {model_name} returned 422 error. This model may require different parameters."
        
        return {
            'answer': f"Error processing question: {error_msg}",
            'sources': [],
            'document_id': document_id,
            'processing_time': processing_time,
            'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL,
            'error': error_msg
        }