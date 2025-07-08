"""Streaming file upload handler for large files

This module provides streaming upload capabilities to handle very large files
without loading them entirely into memory.
"""
import asyncio
import hashlib
import tempfile
from pathlib import Path
from typing import AsyncIterator, Tuple, Optional
import logging

from src.async_io import save_file_from_stream_async, hash_file_async, delete_file_async
from src.document_processor_async import AsyncDocumentProcessor
from src.config import Config

logger = logging.getLogger(__name__)


class StreamingUploadHandler:
    """Handles streaming uploads for large files"""
    
    def __init__(self, config: Config):
        self.config = config
        self.chunk_size = 1024 * 1024  # 1MB chunks
        
    async def process_upload_stream(
        self,
        filename: str,
        file_stream: AsyncIterator[bytes],
        content_length: Optional[int] = None,
        chunk_size: Optional[int] = None
    ) -> Tuple[str, int, int, float]:
        """Process a file upload stream
        
        Args:
            filename: Name of the file being uploaded
            file_stream: Async iterator yielding file chunks
            content_length: Expected file size (if known)
            chunk_size: Document chunk size for processing
            
        Returns:
            Tuple of (document_id, pages, chunks, processing_time)
        """
        # Create temporary file
        temp_dir = Path(tempfile.gettempdir()) / "greg_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        # Generate temporary filename
        temp_file = temp_dir / f"upload_{hashlib.md5(filename.encode()).hexdigest()}.tmp"
        
        try:
            # Stream to temporary file with size tracking
            total_size = 0
            hasher = hashlib.sha256()
            
            async with asyncio.create_task_group() as tg:
                # Create a queue for chunks
                chunk_queue = asyncio.Queue(maxsize=10)
                
                # Producer task: read from stream
                async def producer():
                    nonlocal total_size
                    async for chunk in file_stream:
                        total_size += len(chunk)
                        hasher.update(chunk)
                        
                        # Check size limit
                        if total_size > self.config.MAX_FILE_SIZE_BYTES:
                            raise ValueError(f"File too large. Maximum size is {self.config.MAX_FILE_SIZE_MB}MB")
                        
                        await chunk_queue.put(chunk)
                    
                    # Signal end of stream
                    await chunk_queue.put(None)
                
                # Consumer task: write to file
                async def consumer():
                    chunks = []
                    while True:
                        chunk = await chunk_queue.get()
                        if chunk is None:
                            break
                        chunks.append(chunk)
                    
                    # Write all chunks at once
                    await save_file_from_stream_async(temp_file, async_iter(chunks))
                
                # Run producer and consumer concurrently
                tg.create_task(producer())
                tg.create_task(consumer())
            
            # Log upload stats
            logger.info(f"Streamed upload: {filename} ({total_size / 1024 / 1024:.1f}MB)")
            
            # Process the file
            from src.document_processor import get_doc_processor
            processor = get_doc_processor()
            async_processor = AsyncDocumentProcessor(processor)
            
            # Use streaming processing for very large files (>10MB)
            if total_size > 10 * 1024 * 1024:
                result = await async_processor.process_large_file_streaming(
                    str(temp_file),
                    filename,
                    chunk_size=chunk_size
                )
            else:
                result = await async_processor.process_file_async(
                    str(temp_file),
                    filename,
                    chunk_size=chunk_size
                )
            
            return result
            
        finally:
            # Clean up temporary file
            if temp_file.exists():
                await delete_file_async(temp_file)


async def async_iter(items):
    """Convert a list to an async iterator"""
    for item in items:
        yield item


class ChunkedFileReader:
    """Read a file in chunks for streaming responses"""
    
    def __init__(self, file_path: Path, chunk_size: int = 1024 * 1024):
        self.file_path = file_path
        self.chunk_size = chunk_size
        
    async def read_chunks(self) -> AsyncIterator[bytes]:
        """Read file in chunks"""
        from src.async_io import stream_file_async
        async for chunk in stream_file_async(self.file_path, self.chunk_size):
            yield chunk
    
    async def read_text_chunks(self) -> AsyncIterator[str]:
        """Read text file in chunks"""
        async for chunk in self.read_chunks():
            yield chunk.decode('utf-8', errors='ignore')