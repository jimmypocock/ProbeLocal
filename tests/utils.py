"""
Shared utilities for test scripts
"""
import ollama
from typing import List, Dict, Optional

# Model name mappings from short names to full names with tags
MODEL_MAPPINGS = {
    'deepseek-llm': 'deepseek-llm:7b-chat',
    'deepseek-coder': 'deepseek-coder:6.7b-instruct', 
    'llama3': 'llama3:8b',
    'mistral': 'mistral:latest',
    'phi': 'phi:latest',
    'qwen': 'qwen:latest'
}

def get_model_full_name(model_short_name: str) -> str:
    """
    Convert a short model name to full name with tag.
    If already a full name or not in mappings, return as is.
    """
    if ':' in model_short_name:
        # Already has a tag
        return model_short_name
    
    return MODEL_MAPPINGS.get(model_short_name, model_short_name)

def get_available_models() -> List[str]:
    """
    Get list of available models from Ollama.
    Returns short names for known models, full names for others.
    """
    try:
        models = ollama.list()
        model_list = []
        
        for model in models['models']:
            full_name = model['name']
            
            # Check if this matches any of our known models
            added = False
            for short_name, mapped_name in MODEL_MAPPINGS.items():
                if full_name == mapped_name or full_name.startswith(short_name + ':'):
                    model_list.append(short_name)
                    added = True
                    break
            
            # If not a known model, add the full name
            if not added:
                model_list.append(full_name)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_models = []
        for model in model_list:
            if model not in seen:
                seen.add(model)
                unique_models.append(model)
        
        return unique_models
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

def parse_model_list(models_arg: Optional[List[str]]) -> List[str]:
    """
    Parse model list from command line arguments.
    Converts short names to full names.
    """
    if not models_arg:
        return None
    
    return [get_model_full_name(model) for model in models_arg]