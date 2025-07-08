"""UI utility functions"""
import subprocess
import psutil
import requests
from typing import Dict, Any, Optional, List


def get_system_info() -> Dict[str, float]:
    """Get current system resource information"""
    memory = psutil.virtual_memory()
    return {
        "total_memory_gb": memory.total / (1024**3),
        "available_memory_gb": memory.available / (1024**3),
        "memory_percent": memory.percent
    }


def check_ollama() -> bool:
    """Check if Ollama service is running"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=2)
        return result.returncode == 0
    except:
        return False


def get_document_info(doc_id: str) -> Optional[Dict]:
    """Get information about a specific document"""
    try:
        response = requests.get("http://localhost:8080/documents", timeout=2)
        if response.status_code == 200:
            docs = response.json().get('documents', [])
            for doc in docs:
                if doc['document_id'] == doc_id:
                    return doc
    except:
        pass
    return None


def get_model_info(models_data: Dict, model_name: str) -> Dict:
    """Get information about a specific model"""
    for model in models_data.get('models', []):
        if model['name'] == model_name:
            size_gb = model.get('size', 0) / (1024**3)
            # Determine model characteristics
            if 'phi' in model_name.lower():
                speed = "⚡ Lightning Fast"
                quality = "Good for simple tasks"
            elif 'mistral' in model_name.lower():
                speed = "🚀 Fast"
                quality = "Excellent all-around"
            elif 'deepseek' in model_name.lower():
                speed = "💨 Very Fast"
                quality = "Great for technical content"
            elif 'llama' in model_name.lower():
                speed = "⚖️ Balanced"
                quality = "Best comprehension"
            else:
                speed = "🔄 Variable"
                quality = "Good general use"

            return {
                'size': f"{size_gb:.1f}GB",
                'speed': speed,
                'quality': quality
            }
    return {'size': 'Unknown', 'speed': 'Unknown', 'quality': 'Unknown'}


def get_available_models() -> List[str]:
    """Get list of available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models_data = response.json()
            return [model['name'] for model in models_data.get('models', [])]
    except:
        return ["mistral"]  # Default fallback
    return ["mistral"]


def get_storage_stats() -> Optional[Dict]:
    """Get storage statistics from the backend"""
    try:
        response = requests.get("http://localhost:8080/storage-stats", timeout=2)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None
