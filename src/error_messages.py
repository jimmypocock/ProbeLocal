"""Centralized error messages for better user experience"""
from typing import Dict, Optional
import traceback


class ErrorMessages:
    """Provides specific, helpful error messages for common issues"""
    
    # Service connection errors
    OLLAMA_NOT_RUNNING = """
    🔴 **Ollama Service Not Running**
    
    Please start Ollama with:
    ```bash
    ollama serve
    ```
    
    Then ensure you have a model installed:
    ```bash
    ollama pull mistral
    ```
    """
    
    OLLAMA_NO_MODELS = """
    🟡 **No AI Models Found**
    
    Please install at least one model:
    ```bash
    ollama pull mistral
    ollama pull llama2
    ```
    """
    
    API_CONNECTION_FAILED = """
    🔴 **Cannot Connect to Backend API**
    
    The API server may not be running. Please ensure:
    1. The API is started (`python main.py`)
    2. It's running on port 8080
    3. No firewall is blocking the connection
    """
    
    # Document processing errors
    DOCUMENT_NOT_FOUND = """
    📄 **Document Not Found**
    
    The document you're trying to access no longer exists.
    It may have been deleted or expired.
    """
    
    DOCUMENT_PROCESSING_FAILED = """
    ⚠️ **Document Processing Failed**
    
    Unable to process your document. This might be due to:
    - Corrupted file format
    - Unsupported content type
    - File too large (max {max_size}MB)
    
    Please try uploading a different file.
    """
    
    VECTOR_STORE_ERROR = """
    💾 **Storage Error**
    
    Unable to save document embeddings. This might be due to:
    - Insufficient disk space
    - Permission issues in the vector_stores directory
    - Corrupted vector store
    
    Try clearing old documents or checking disk space.
    """
    
    # Model-specific errors
    MODEL_422_ERROR = """
    🤖 **Model Configuration Error**
    
    The model '{model_name}' requires different parameters.
    
    Try:
    1. Switching to a different model (e.g., mistral)
    2. Running model compatibility test:
       ```bash
       python test_models.py --models {model_name}
       ```
    """
    
    MODEL_TIMEOUT = """
    ⏱️ **Model Response Timeout**
    
    The AI model took too long to respond. This might be due to:
    - Model is still loading (first query)
    - Question is too complex
    - System resources are limited
    
    Try:
    - Asking a simpler question
    - Waiting a moment and trying again
    - Reducing the context sources in settings
    """
    
    # File upload errors
    FILE_TOO_LARGE = """
    📦 **File Too Large**
    
    Your file exceeds the maximum size of {max_size}MB.
    
    Try:
    - Compressing the file
    - Splitting into smaller documents
    - Using a different file format
    """
    
    UNSUPPORTED_FILE_TYPE = """
    ❌ **Unsupported File Type**
    
    File type '{file_type}' is not supported.
    
    Supported formats:
    - Documents: PDF, TXT, MD, DOCX
    - Data: CSV, XLSX
    - Images: PNG, JPG, JPEG
    """
    
    # Network errors
    RATE_LIMIT_EXCEEDED = """
    🚦 **Rate Limit Exceeded**
    
    You've made too many requests. Please wait a moment before trying again.
    
    Limits:
    - Questions: 60/minute
    - Web searches: 30/minute
    - Uploads: 10/minute
    """
    
    WEB_SEARCH_FAILED = """
    🌐 **Web Search Failed**
    
    Unable to search the web. This might be due to:
    - Network connection issues
    - Search service temporarily unavailable
    - Rate limiting from search provider
    
    Try again in a few moments or disable web search.
    """
    
    # Memory errors
    OUT_OF_MEMORY = """
    💭 **Out of Memory**
    
    The system is running low on memory. Try:
    - Closing other applications
    - Reducing chunk size in settings
    - Processing smaller documents
    - Restarting the application
    
    Current memory usage: {memory_percent}%
    """
    
    @staticmethod
    def get_specific_error(error: Exception, context: Optional[Dict] = None) -> str:
        """Convert generic exceptions to specific error messages"""
        error_str = str(error).lower()
        context = context or {}
        
        # Connection errors
        if "connection refused" in error_str or "failed to connect" in error_str:
            if "11434" in error_str:
                return ErrorMessages.OLLAMA_NOT_RUNNING
            elif "8080" in error_str:
                return ErrorMessages.API_CONNECTION_FAILED
        
        # Model errors
        elif "422" in error_str or "unprocessable entity" in error_str:
            model_name = context.get('model_name', 'unknown')
            return ErrorMessages.MODEL_422_ERROR.format(model_name=model_name)
        
        # File errors
        elif "file too large" in error_str or "413" in error_str:
            max_size = context.get('max_size', 50)
            return ErrorMessages.FILE_TOO_LARGE.format(max_size=max_size)
        
        elif "unsupported file" in error_str:
            file_type = context.get('file_type', 'unknown')
            return ErrorMessages.UNSUPPORTED_FILE_TYPE.format(file_type=file_type)
        
        # Document errors
        elif "document not found" in error_str or "404" in error_str:
            return ErrorMessages.DOCUMENT_NOT_FOUND
        
        # Memory errors
        elif "memory" in error_str or "oom" in error_str:
            import psutil
            memory = psutil.virtual_memory()
            return ErrorMessages.OUT_OF_MEMORY.format(memory_percent=memory.percent)
        
        # Rate limiting
        elif "rate limit" in error_str or "429" in error_str:
            return ErrorMessages.RATE_LIMIT_EXCEEDED
        
        # Timeout
        elif "timeout" in error_str or "timed out" in error_str:
            return ErrorMessages.MODEL_TIMEOUT
        
        # Web search
        elif "web search" in error_str or "duckduckgo" in error_str:
            return ErrorMessages.WEB_SEARCH_FAILED
        
        # Default with details
        else:
            return f"""
            ❌ **Error: {error.__class__.__name__}**
            
            {str(error)}
            
            If this persists, please check:
            - All services are running (Ollama, API)
            - You have sufficient disk space
            - Your network connection is stable
            """
    
    @staticmethod
    def format_traceback(error: Exception) -> str:
        """Format exception traceback for technical details"""
        tb = traceback.format_exc()
        return f"""
        <details>
        <summary>🔍 Technical Details</summary>
        
        ```python
        {tb}
        ```
        
        </details>
        """