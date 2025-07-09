"""Streaming response handlers for large query results

This module provides streaming responses for Q&A results to improve
perceived performance and reduce memory usage.
"""
import asyncio
import json
from typing import AsyncIterator, Dict, Any, Optional, TYPE_CHECKING
import logging
from datetime import datetime

from ..web_search import WebSearcher

if TYPE_CHECKING:
    from ..qa_chain_streaming import StreamingQAChain

logger = logging.getLogger(__name__)


class StreamingResponseHandler:
    """Handles streaming responses for Q&A queries"""
    
    def __init__(self, qa_chain: "StreamingQAChain"):
        self.qa_chain = qa_chain
        
    async def stream_answer(
        self,
        question: str,
        document_id: Optional[str] = None,
        max_results: int = 3,
        model_name: Optional[str] = None,
        search_web: bool = False
    ) -> AsyncIterator[str]:
        """Stream the answer to a question
        
        Yields:
            JSON-encoded chunks of the response
        """
        try:
            # Start with metadata
            yield json.dumps({
                "type": "metadata",
                "timestamp": datetime.now().isoformat(),
                "model": model_name or "default",
                "document_id": document_id,
                "search_web": search_web
            }) + "\n"
            
            if search_web:
                # Stream web search results
                searcher = WebSearcher()
                
                # Send search status
                yield json.dumps({
                    "type": "status",
                    "message": "Searching the web..."
                }) + "\n"
                
                # Perform search
                search_results = await asyncio.get_event_loop().run_in_executor(
                    None,
                    searcher.search,
                    question,
                    5  # num_results
                )
                
                # Send search results
                yield json.dumps({
                    "type": "search_results",
                    "results": search_results[:3]  # Limit to top 3
                }) + "\n"
                
                # Generate answer based on search results
                context = "\n\n".join([
                    f"Source: {r['url']}\n{r['content'][:500]}"
                    for r in search_results[:3]
                ])
                
                # Stream the answer generation
                async for chunk in self._stream_llm_response(question, context, model_name):
                    yield json.dumps({
                        "type": "answer_chunk",
                        "content": chunk
                    }) + "\n"
            else:
                # Regular document-based Q&A
                if not document_id:
                    yield json.dumps({
                        "type": "error",
                        "message": "No document ID provided"
                    }) + "\n"
                    return
                
                # Send status
                yield json.dumps({
                    "type": "status",
                    "message": "Searching document..."
                }) + "\n"
                
                # Get context from vector store
                context_docs = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.qa_chain._get_context,
                    question,
                    document_id,
                    max_results
                )
                
                if not context_docs:
                    yield json.dumps({
                        "type": "answer",
                        "content": "I couldn't find relevant information in the document."
                    }) + "\n"
                    return
                
                # Send context preview
                yield json.dumps({
                    "type": "context",
                    "num_chunks": len(context_docs),
                    "preview": context_docs[0][:200] + "..." if context_docs else ""
                }) + "\n"
                
                # Stream the answer
                context = "\n\n".join(context_docs)
                async for chunk in self._stream_llm_response(question, context, model_name):
                    yield json.dumps({
                        "type": "answer_chunk",
                        "content": chunk
                    }) + "\n"
            
            # Send completion signal
            yield json.dumps({
                "type": "complete",
                "timestamp": datetime.now().isoformat()
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield json.dumps({
                "type": "error",
                "message": str(e)
            }) + "\n"
    
    async def _stream_llm_response(
        self,
        question: str,
        context: str,
        model_name: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Stream LLM response in chunks"""
        # For now, we'll simulate streaming by breaking the response into words
        # In a real implementation, this would use the LLM's streaming API
        
        try:
            # Generate full response (non-streaming for now)
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.qa_chain._generate_answer,
                question,
                context,
                model_name
            )
            
            # Simulate streaming by yielding words
            words = response.split()
            buffer = []
            
            for i, word in enumerate(words):
                buffer.append(word)
                
                # Yield every 5 words or at the end
                if len(buffer) >= 5 or i == len(words) - 1:
                    yield " ".join(buffer) + " "
                    buffer = []
                    await asyncio.sleep(0.05)  # Small delay to simulate streaming
                    
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            yield f"Error: {str(e)}"


class StreamingExportHandler:
    """Handles streaming exports of documents"""
    
    @staticmethod
    async def stream_document_export(
        document_id: str,
        format: str = "json"
    ) -> AsyncIterator[bytes]:
        """Stream document export in various formats
        
        Args:
            document_id: Document ID to export
            format: Export format (json, csv, txt)
            
        Yields:
            Chunks of exported data
        """
        # Load document metadata
        from ..async_io import load_json_async
        from ..config import Config
        
        config = Config()
        metadata_path = config.VECTOR_STORE_DIR / f"{document_id}.metadata"
        
        try:
            metadata = await load_json_async(metadata_path)
            
            if format == "json":
                # Stream JSON export
                yield b'{\n'
                yield f'  "document_id": "{document_id}",\n'.encode()
                yield f'  "filename": "{metadata.get("filename", "unknown")}",\n'.encode()
                yield f'  "upload_date": "{metadata.get("upload_date", "")}",\n'.encode()
                yield b'  "chunks": [\n'
                
                # TODO: Stream chunks from vector store
                yield b'  ]\n'
                yield b'}\n'
                
            elif format == "txt":
                # Stream plain text export
                yield f"Document: {metadata.get('filename', 'unknown')}\n".encode()
                yield f"ID: {document_id}\n".encode()
                yield f"Date: {metadata.get('upload_date', '')}\n".encode()
                yield b"\n---\n\n"
                
                # TODO: Stream document content
                
        except Exception as e:
            logger.error(f"Error exporting document: {e}")
            yield f"Error: {str(e)}".encode()