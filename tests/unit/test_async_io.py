"""Unit tests for async I/O operations"""
import pytest
import asyncio
import json
from pathlib import Path
import tempfile

from src.async_io import (
    read_file_async, write_file_async, hash_file_async,
    save_json_async, load_json_async, delete_file_async,
    file_exists_async, stream_file_async, process_files_batch_async
)


@pytest.mark.asyncio
async def test_read_write_text():
    """Test async text file read/write"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        # Write text
        test_content = "Hello, async world!"
        await write_file_async(temp_path, test_content)
        
        # Read text
        content = await read_file_async(temp_path)
        assert content == test_content
        
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_read_write_binary():
    """Test async binary file read/write"""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        # Write binary
        test_content = b"Binary data \x00\x01\x02"
        await write_file_async(temp_path, test_content, mode='wb')
        
        # Read binary
        content = await read_file_async(temp_path, mode='rb')
        assert content == test_content
        
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_hash_file():
    """Test async file hashing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        temp_path = Path(f.name)
        f.write("Test content for hashing")
    
    try:
        # Generate hash
        file_hash = await hash_file_async(temp_path)
        
        # Verify it's a valid SHA256 hash
        assert len(file_hash) == 64  # SHA256 produces 64 hex characters
        assert all(c in '0123456789abcdef' for c in file_hash)
        
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_json_operations():
    """Test async JSON save/load"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
        temp_path = Path(f.name)
    
    try:
        # Test data
        test_data = {
            "string": "value",
            "number": 42,
            "list": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        # Save JSON
        await save_json_async(temp_path, test_data)
        
        # Load JSON
        loaded_data = await load_json_async(temp_path)
        assert loaded_data == test_data
        
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_file_exists():
    """Test async file existence check"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        # File exists
        assert await file_exists_async(temp_path) is True
        
        # Delete file
        temp_path.unlink()
        
        # File doesn't exist
        assert await file_exists_async(temp_path) is False
        
    finally:
        if temp_path.exists():
            temp_path.unlink()


@pytest.mark.asyncio
async def test_delete_file():
    """Test async file deletion"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = Path(f.name)
        f.write(b"test")
    
    assert temp_path.exists()
    
    # Delete file
    await delete_file_async(temp_path)
    
    assert not temp_path.exists()


@pytest.mark.asyncio
async def test_stream_file():
    """Test async file streaming"""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
        temp_path = Path(f.name)
        # Write 10KB of data
        test_data = b"x" * 10240
        f.write(test_data)
    
    try:
        # Stream file in 1KB chunks
        chunks = []
        async for chunk in stream_file_async(temp_path, chunk_size=1024):
            chunks.append(chunk)
        
        # Should have 10 chunks
        assert len(chunks) == 10
        assert all(len(chunk) == 1024 for chunk in chunks)
        assert b"".join(chunks) == test_data
        
    finally:
        temp_path.unlink()


@pytest.mark.asyncio
async def test_process_files_batch():
    """Test batch file processing"""
    # Create test files
    temp_dir = Path(tempfile.mkdtemp())
    test_files = []
    
    try:
        for i in range(5):
            file_path = temp_dir / f"test_{i}.txt"
            file_path.write_text(f"Content {i}")
            test_files.append(file_path)
        
        # Process files
        async def process_file(path):
            content = await read_file_async(path)
            return content.upper()
        
        results = await process_files_batch_async(
            test_files,
            process_file,
            max_concurrent=3
        )
        
        # Verify results
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == f"CONTENT {i}"
        
    finally:
        # Cleanup
        for file_path in test_files:
            if file_path.exists():
                file_path.unlink()
        temp_dir.rmdir()


@pytest.mark.asyncio
async def test_concurrent_file_operations():
    """Test concurrent file operations don't interfere"""
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        # Create multiple files concurrently
        async def create_file(i):
            path = temp_dir / f"concurrent_{i}.txt"
            await write_file_async(path, f"File {i} content")
            return path
        
        # Create 10 files concurrently
        paths = await asyncio.gather(*[create_file(i) for i in range(10)])
        
        # Verify all files exist and have correct content
        for i, path in enumerate(paths):
            content = await read_file_async(path)
            assert content == f"File {i} content"
        
    finally:
        # Cleanup
        for file in temp_dir.glob("*"):
            file.unlink()
        temp_dir.rmdir()