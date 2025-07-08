"""Async I/O utilities for file operations

This module provides async wrappers for common file operations to improve
performance and prevent blocking in the FastAPI application.
"""
import aiofiles
import asyncio
import json
import hashlib
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, AsyncIterator
import logging

logger = logging.getLogger(__name__)


async def read_file_async(path: Path, mode: str = 'r', encoding: Optional[str] = 'utf-8') -> str:
    """Read a file asynchronously
    
    Args:
        path: Path to the file
        mode: File open mode ('r' for text, 'rb' for binary)
        encoding: Text encoding (ignored for binary mode)
        
    Returns:
        File contents as string (text mode) or bytes (binary mode)
    """
    if 'b' in mode:
        async with aiofiles.open(path, mode) as f:
            return await f.read()
    else:
        async with aiofiles.open(path, mode, encoding=encoding) as f:
            return await f.read()


async def write_file_async(path: Path, content: Any, mode: str = 'w', encoding: Optional[str] = 'utf-8'):
    """Write content to a file asynchronously
    
    Args:
        path: Path to the file
        content: Content to write
        mode: File open mode ('w' for text, 'wb' for binary)
        encoding: Text encoding (ignored for binary mode)
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)
    
    if 'b' in mode:
        async with aiofiles.open(path, mode) as f:
            await f.write(content)
    else:
        async with aiofiles.open(path, mode, encoding=encoding) as f:
            await f.write(content)


async def hash_file_async(path: Path, chunk_size: int = 8192) -> str:
    """Generate SHA256 hash of a file asynchronously
    
    Args:
        path: Path to the file
        chunk_size: Size of chunks to read (default 8KB)
        
    Returns:
        Hexadecimal hash string
    """
    hasher = hashlib.sha256()
    async with aiofiles.open(path, 'rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


async def copy_file_async(src: Path, dst: Path):
    """Copy a file asynchronously
    
    Args:
        src: Source file path
        dst: Destination file path
    """
    # Ensure destination directory exists
    dst.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiofiles.open(src, 'rb') as src_file:
        async with aiofiles.open(dst, 'wb') as dst_file:
            while True:
                chunk = await src_file.read(8192)
                if not chunk:
                    break
                await dst_file.write(chunk)


async def delete_file_async(path: Path):
    """Delete a file asynchronously
    
    Args:
        path: Path to the file to delete
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, path.unlink, True)  # missing_ok=True


async def delete_directory_async(path: Path):
    """Delete a directory and its contents asynchronously
    
    Args:
        path: Path to the directory to delete
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, shutil.rmtree, str(path), True)  # ignore_errors=True


async def save_json_async(path: Path, data: Dict[str, Any], indent: int = 2):
    """Save data as JSON asynchronously
    
    Args:
        path: Path to save the JSON file
        data: Dictionary to serialize
        indent: JSON indentation level
    """
    json_str = json.dumps(data, indent=indent, default=str)
    await write_file_async(path, json_str)


async def load_json_async(path: Path) -> Dict[str, Any]:
    """Load JSON data asynchronously
    
    Args:
        path: Path to the JSON file
        
    Returns:
        Parsed JSON data as dictionary
    """
    content = await read_file_async(path)
    return json.loads(content)


async def file_exists_async(path: Path) -> bool:
    """Check if a file exists asynchronously
    
    Args:
        path: Path to check
        
    Returns:
        True if file exists, False otherwise
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, path.exists)


async def get_file_size_async(path: Path) -> int:
    """Get file size asynchronously
    
    Args:
        path: Path to the file
        
    Returns:
        File size in bytes
    """
    loop = asyncio.get_event_loop()
    stat = await loop.run_in_executor(None, path.stat)
    return stat.st_size


async def stream_file_async(path: Path, chunk_size: int = 1024 * 1024) -> AsyncIterator[bytes]:
    """Stream a file in chunks asynchronously
    
    Args:
        path: Path to the file
        chunk_size: Size of each chunk (default 1MB)
        
    Yields:
        Chunks of file content
    """
    async with aiofiles.open(path, 'rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            yield chunk


async def save_file_from_stream_async(path: Path, stream: AsyncIterator[bytes]):
    """Save a file from an async stream
    
    Args:
        path: Path to save the file
        stream: Async iterator yielding chunks of data
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(path, 'wb') as f:
        async for chunk in stream:
            await f.write(chunk)


# CPU-bound operations that should use thread pool
async def run_cpu_bound_async(func, *args, **kwargs):
    """Run a CPU-bound function in a thread pool
    
    Args:
        func: Function to run
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Function result
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


# Batch operations for efficiency
async def process_files_batch_async(
    file_paths: list[Path], 
    process_func, 
    max_concurrent: int = 5
) -> list:
    """Process multiple files concurrently with concurrency limit
    
    Args:
        file_paths: List of file paths to process
        process_func: Async function to process each file
        max_concurrent: Maximum number of concurrent operations
        
    Returns:
        List of results from processing each file
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(path):
        async with semaphore:
            try:
                return await process_func(path)
            except Exception as e:
                logger.error(f"Error processing {path}: {e}")
                return None
    
    tasks = [process_with_semaphore(path) for path in file_paths]
    return await asyncio.gather(*tasks)