from typing import List, Dict, Any
import time
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from src.config import Config
from src.local_llm import OptimizedLLM
from src.document_processor import DocumentProcessor

class QAChain:
    def __init__(self):
        self.config = Config()
        self.doc_processor = DocumentProcessor()
        self.llm_system = OptimizedLLM(self.config)
        self.llm = self.llm_system.get_llm()
        self.prompt_template = self._create_prompt_template()

    def _create_prompt_template(self) -> PromptTemplate:
        """Optimized prompt for local models"""
        template = """You are analyzing a document. When asked about numbers, amounts, or totals, 
look for EXACT values in the context. Do not calculate or estimate - only report what is explicitly written.

For invoices: Look for labels like "Total:", "Grand Total:", "Amount Due:", "Subtotal:", "Balance:".
For dates: Look for date formats and return them exactly as written.
For names/addresses: Return them exactly as they appear.

Context:
{context}

Question: {question}

Important: If you cannot find the exact information, say "I cannot find that specific information in the provided context."

Answer:"""

        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

    def answer_question(
        self,
        question: str,
        document_id: str,
        max_results: int = 5,
        stream: bool = False,
        model_name: str = None
    ) -> Dict[str, Any]:
        """Answer with optional streaming"""
        start_time = time.time()
        
        # Use specified model or default
        if model_name and model_name != self.config.LOCAL_LLM_MODEL:
            # Create a new LLM instance with the requested model
            from langchain_community.llms import Ollama as LangchainOllama
            llm = LangchainOllama(
                model=model_name,
                temperature=self.config.TEMPERATURE,
                top_p=self.config.TOP_P,
                num_ctx=self.config.MAX_CONTEXT_LENGTH,
                num_thread=self.config.NUM_THREADS,
                repeat_penalty=1.1,
                stop=["Human:", "Question:"]
            )
        else:
            llm = self.llm

        # Load vector store
        vector_store = self.doc_processor.load_vector_store(document_id)

        # Create retriever with similarity search
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": max_results}
        )

        # Configure callbacks for streaming
        callbacks = [StreamingStdOutCallbackHandler()] if stream else []

        # Create QA chain with the selected LLM
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,  # Use the dynamic LLM
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

        # Format sources with page numbers
        sources = []
        seen_pages = set()

        for doc in result['source_documents']:
            page = doc.metadata.get('page', 'N/A')
            if page not in seen_pages:
                sources.append({
                    'content': doc.page_content[:200] + "...",
                    'page': page,
                    'chunk_index': doc.metadata.get('chunk_index', 'N/A')
                })
                seen_pages.add(page)

        processing_time = time.time() - start_time

        return {
            'answer': result['result'].strip(),
            'sources': sources[:3],  # Limit to top 3 sources
            'document_id': document_id,
            'processing_time': processing_time,
            'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL
        }