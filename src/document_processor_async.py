"""Async wrapper for document processing operations

This module provides async wrappers for CPU-bound document processing
operations to prevent blocking the event loop.
"""
import asyncio
from pathlib import Path
from typing import Tuple, Optional
import logging

from src.document_processor import DocumentProcessor
from src.async_io import (
    hash_file_async, save_json_async, run_cpu_bound_async,
    file_exists_async
)

logger = logging.getLogger(__name__)


class AsyncDocumentProcessor:
    """Async wrapper for DocumentProcessor"""
    
    def __init__(self, doc_processor: DocumentProcessor):
        self.doc_processor = doc_processor
        self.config = doc_processor.config
    
    async def generate_document_id_async(self, file_path: str) -> str:
        """Generate document ID asynchronously using file hash"""
        file_hash = await hash_file_async(Path(file_path))
        return file_hash[:16]
    
    async def process_file_async(
        self, 
        file_path: str, 
        filename: str, 
        chunk_size: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """Process a file asynchronously
        
        This runs the CPU-bound processing in a thread pool to avoid
        blocking the event loop.
        """
        # Generate document ID asynchronously
        doc_id = await self.generate_document_id_async(file_path)
        
        # Check if already processed
        vector_store_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        metadata_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.metadata"
        
        if await file_exists_async(vector_store_path) and await file_exists_async(metadata_path):
            logger.info(f"Document already processed: {doc_id}")
            # Load metadata to get stats
            import json
            from src.async_io import load_json_async
            metadata = await load_json_async(metadata_path)
            return doc_id, metadata.get('pages', 1), metadata.get('chunks', 0), 0.0
        
        # Run the CPU-bound processing in a thread pool
        result = await run_cpu_bound_async(
            self.doc_processor.process_file,
            file_path,
            filename,
            chunk_size
        )
        
        return result
    
    async def save_vector_store_async(self, vector_store, doc_id: str):
        """Save vector store asynchronously"""
        vector_store_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        await run_cpu_bound_async(
            vector_store.save_local,
            str(vector_store_path)
        )
    
    async def load_vector_store_async(self, doc_id: str):
        """Load vector store asynchronously"""
        return await run_cpu_bound_async(
            self.doc_processor.load_vector_store,
            doc_id
        )
    
    async def process_large_file_streaming(
        self,
        file_path: str,
        filename: str,
        chunk_size: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """Process large files with streaming to reduce memory usage
        
        This is particularly useful for very large PDFs or documents.
        """
        from src.incremental_processor import IncrementalProcessor
        
        # Create incremental processor
        incremental = IncrementalProcessor(
            self.doc_processor.embeddings,
            self.config,
            chunk_size=chunk_size or self.config.CHUNK_SIZE
        )
        
        # Process file incrementally
        result = await run_cpu_bound_async(
            incremental.process_file_incremental,
            file_path,
            filename,
            batch_size=10  # Process 10 chunks at a time
        )
        
        return result