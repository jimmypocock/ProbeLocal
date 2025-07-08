"""Enhanced QA Chain with proper streaming support"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Generator
import time
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from langchain.chains import RetrievalQA
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from src.qa_chain_enhanced import EnhancedQAChain
from src.streaming_handler import StreamingResponseHandler, AsyncStreamingResponseHandler


class StreamingQAChain(EnhancedQAChain):
    """QA Chain with streaming response support"""
    
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=1)
    
    def answer_question_streaming(
        self,
        question: str,
        document_id: str,
        use_web: bool = False,
        max_results: int = 5,
        model_name: str = None,
        temperature: float = None
    ) -> Generator[str, None, None]:
        """Answer question with streaming response"""
        start_time = time.time()
        
        # Get vector store or handle web-only
        if not document_id or document_id == "web_only":
            vector_store = None
            retriever = self._get_web_only_retriever(question, max_results)
        else:
            try:
                vector_store = self.doc_processor.load_vector_store(document_id)
                retriever = self._create_hybrid_retriever(vector_store, question, use_web)
            except ValueError as e:
                if use_web:
                    retriever = self._get_web_only_retriever(question, max_results)
                else:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    return
        
        # Get LLM
        llm = self._get_llm_for_model(model_name, temperature)
        
        # Create streaming handler
        handler = StreamingResponseHandler()
        
        try:
            # Create QA chain with streaming
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": self.prompt_template,
                    "verbose": False
                },
                callbacks=[handler]
            )
            
            # Start generation in background thread
            future = self.executor.submit(qa_chain, {"query": question})
            
            # Stream tokens as they come
            full_response = ""
            while True:
                token = handler.queue.get()
                if token is None:
                    break
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Get the result for sources
            result = future.result()
            sources = self._format_sources(result['source_documents'])
            
            # Send final message with metadata
            processing_time = time.time() - start_time
            final_data = {
                'done': True,
                'sources': sources,
                'processing_time': processing_time,
                'document_id': document_id,
                'used_web_search': use_web
            }
            yield f"data: {json.dumps(final_data)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
    async def answer_question_streaming_async(
        self,
        question: str,
        document_id: str,
        use_web: bool = False,
        max_results: int = 5,
        model_name: str = None,
        temperature: float = None
    ) -> AsyncGenerator[str, None]:
        """Answer question with async streaming response"""
        start_time = time.time()
        
        # Convert to sync streaming and yield
        loop = asyncio.get_event_loop()
        
        # Run the sync version in a thread
        def _sync_generator():
            return self.answer_question_streaming(
                question, document_id, use_web, max_results, model_name, temperature
            )
        
        # Stream from the sync generator
        gen = await loop.run_in_executor(None, _sync_generator)
        for chunk in gen:
            yield chunk
    
    def _get_web_only_retriever(self, question: str, max_results: int):
        """Get retriever for web-only searches"""
        web_docs = self._search_web_for_context(question, num_results=max_results)
        
        if not web_docs:
            # Return empty retriever
            class EmptyRetriever:
                def get_relevant_documents(self, query: str):
                    return []
                def as_retriever(self, **kwargs):
                    return self
            return EmptyRetriever()
        
        # Create temporary vector store
        texts = [doc.page_content for doc in web_docs]
        metadatas = [doc.metadata for doc in web_docs]
        
        from langchain_community.vectorstores import FAISS
        temp_vector_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas
        )
        
        return temp_vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": min(len(web_docs), 3)}
        )