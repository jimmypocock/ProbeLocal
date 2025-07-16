"""Security utilities for the Greg AI Playground.

This module provides security functions to prevent common vulnerabilities
like path traversal, injection attacks, and unsafe deserialization.
"""

import os
import re
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Union
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Constants for validation
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'md', 'docx', 'xlsx', 'png', 'jpg', 'jpeg'}
MAX_FILENAME_LENGTH = 255
SAFE_CHARS_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')

# Model whitelist for validation
ALLOWED_MODELS = {
    'mistral', 'mistral:latest',
    'llama2', 'llama2:latest', 'llama2:7b', 'llama2:13b',
    'llama3', 'llama3:latest', 'llama3:8b', 'llama3:70b',
    'phi', 'phi:latest', 'phi3', 'phi3:latest',
    'deepseek-coder', 'deepseek-coder:latest', 'deepseek-coder:6.7b-instruct',
    'deepseek-llm', 'deepseek-llm:latest', 'deepseek-llm:7b-chat',
    'neural-chat', 'neural-chat:latest',
    'dolphin-mistral', 'dolphin-mistral:latest',
    'mixtral', 'mixtral:latest'
}

# Parameter bounds for validation
PARAMETER_BOUNDS = {
    'chunk_size': (100, 5000),
    'chunk_overlap': (0, 1000),
    'batch_size': (1, 100),
    'temperature': (0.0, 2.0),
    'max_tokens': (1, 8192),
    'max_results': (1, 20),
    'top_k': (1, 100),
    'top_p': (0.0, 1.0),
    'num_ctx': (128, 32768),
    'repeat_penalty': (0.0, 2.0),
    'seed': (0, 2147483647)
}


def sanitize_filename(filename: str) -> Optional[str]:
    """Sanitize a filename to prevent path traversal attacks.
    
    Args:
        filename: The original filename
        
    Returns:
        Sanitized filename or None if invalid
    """
    if not filename:
        return None
        
    # Use werkzeug's secure_filename to remove dangerous characters
    safe_name = secure_filename(filename)
    
    # Additional validation
    if not safe_name:
        logger.warning(f"Filename '{filename}' resulted in empty string after sanitization")
        return None
        
    # Check length
    if len(safe_name) > MAX_FILENAME_LENGTH:
        # Preserve extension if possible
        name, ext = os.path.splitext(safe_name)
        max_name_length = MAX_FILENAME_LENGTH - len(ext) - 1
        safe_name = name[:max_name_length] + ext
        
    # Ensure it has an allowed extension
    ext = safe_name.rsplit('.', 1)[-1].lower() if '.' in safe_name else ''
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"File extension '{ext}' not in allowed list")
        return None
        
    return safe_name


def validate_file_path(file_path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """Validate that a file path is within the allowed base directory.
    
    Args:
        file_path: The path to validate
        base_dir: The allowed base directory
        
    Returns:
        True if the path is safe, False otherwise
    """
    try:
        # Convert to Path objects
        file_path = Path(file_path).resolve()
        base_dir = Path(base_dir).resolve()
        
        # Check if the file path is within the base directory
        file_path.relative_to(base_dir)
        return True
    except (ValueError, OSError):
        logger.warning(f"Path validation failed: {file_path} not within {base_dir}")
        return False


def sanitize_query_string(query: str, max_length: int = 1000) -> str:
    """Sanitize user query strings to prevent injection attacks.
    
    Args:
        query: The user's query string
        max_length: Maximum allowed length
        
    Returns:
        Sanitized query string
    """
    if not query:
        return ""
        
    # Remove null bytes
    query = query.replace('\x00', '')
    
    # Limit length
    query = query[:max_length]
    
    # Remove control characters except newlines and tabs
    query = ''.join(char for char in query if char == '\n' or char == '\t' or not ord(char) < 32)
    
    # Strip leading/trailing whitespace
    return query.strip()


def validate_model_name(model_name: str) -> bool:
    """Validate that a model name is in the allowed list.
    
    Args:
        model_name: The model name to validate
        
    Returns:
        True if the model is allowed, False otherwise
    """
    return model_name.lower() in ALLOWED_MODELS


def validate_parameter_bounds(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and clamp parameters to safe bounds.
    
    Args:
        params: Dictionary of parameters to validate
        
    Returns:
        Dictionary with validated and clamped parameters
    """
    validated = {}
    
    for key, value in params.items():
        if key in PARAMETER_BOUNDS:
            min_val, max_val = PARAMETER_BOUNDS[key]
            
            try:
                # Convert to appropriate type
                if isinstance(min_val, float):
                    value = float(value)
                else:
                    value = int(value)
                    
                # Clamp to bounds
                value = max(min_val, min(value, max_val))
                validated[key] = value
                
            except (ValueError, TypeError):
                logger.warning(f"Invalid value for parameter '{key}': {value}")
                # Skip invalid parameters
                continue
        else:
            # Pass through parameters not in bounds check
            validated[key] = value
            
    return validated


def sanitize_error_message(error: Exception, show_details: bool = False) -> str:
    """Sanitize error messages to prevent information disclosure.
    
    Args:
        error: The exception to sanitize
        show_details: Whether to show detailed error info (for debugging)
        
    Returns:
        Safe error message for users
    """
    error_type = type(error).__name__
    
    # Map specific errors to user-friendly messages
    error_map = {
        'FileNotFoundError': "The requested file could not be found.",
        'PermissionError': "You don't have permission to access this resource.",
        'ValueError': "Invalid input provided. Please check your request.",
        'TimeoutError': "The operation timed out. Please try again.",
        'MemoryError': "Not enough memory to complete the operation.",
        'ConnectionError': "Connection error. Please check your network.",
    }
    
    # Get user-friendly message
    user_message = error_map.get(error_type, "An error occurred while processing your request.")
    
    # Log the actual error for debugging
    logger.error(f"Sanitized error: {error_type}: {str(error)}")
    
    # Only show details in development mode
    if show_details:
        return f"{user_message} (Details: {error_type})"
    
    return user_message


def create_safe_file_path(filename: str, base_dir: Union[str, Path]) -> Optional[Path]:
    """Create a safe file path within the base directory.
    
    Args:
        filename: The filename to use
        base_dir: The base directory for files
        
    Returns:
        Safe Path object or None if invalid
    """
    # Sanitize the filename first
    safe_filename = sanitize_filename(filename)
    if not safe_filename:
        return None
        
    # Create the full path
    base_path = Path(base_dir).resolve()
    file_path = base_path / safe_filename
    
    # Validate it's within the base directory
    if not validate_file_path(file_path, base_path):
        return None
        
    return file_path


def is_safe_url(url: str) -> bool:
    """Check if a URL is safe to fetch.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if the URL appears safe, False otherwise
    """
    # Basic URL validation
    if not url or not isinstance(url, str):
        return False
        
    # Check for common URL schemes
    allowed_schemes = {'http', 'https'}
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return parsed.scheme in allowed_schemes and bool(parsed.netloc)
    except Exception:
        return False


def validate_vector_store_path(store_path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """Validate that a vector store path is safe to load.
    
    Args:
        store_path: Path to the vector store
        base_dir: Expected base directory for vector stores
        
    Returns:
        True if the path is valid and safe
    """
    try:
        store_path = Path(store_path).resolve()
        base_dir = Path(base_dir).resolve()
        
        # Check path is within base directory
        store_path.relative_to(base_dir)
        
        # Check file exists and has reasonable size
        if not store_path.exists():
            logger.warning(f"Vector store does not exist: {store_path}")
            return False
            
        # Check size (vector stores shouldn't be gigantic)
        max_size = 2 * 1024 * 1024 * 1024  # 2GB max
        
        # Handle both file and directory cases (FAISS can save as either)
        if store_path.is_file():
            if store_path.stat().st_size > max_size:
                logger.warning(f"Vector store too large: {store_path}")
                return False
        elif store_path.is_dir():
            # Check total size of directory
            total_size = sum(f.stat().st_size for f in store_path.rglob('*') if f.is_file())
            if total_size > max_size:
                logger.warning(f"Vector store directory too large: {store_path}")
                return False
        else:
            logger.warning(f"Vector store path is neither file nor directory: {store_path}")
            return False
            
        return True
        
    except (ValueError, OSError) as e:
        logger.warning(f"Vector store validation failed: {e}")
        return False