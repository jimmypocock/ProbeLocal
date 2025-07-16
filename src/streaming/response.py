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
            Server-Sent Events formatted chunks
        """
        try:
            # Use the QA chain's streaming method
            async for chunk in self.qa_chain.answer_question_streaming_async(
                question=question,
                document_id=document_id or "web_only" if search_web else None,
                use_web=search_web,
                max_results=max_results,
                model_name=model_name
            ):
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
    
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