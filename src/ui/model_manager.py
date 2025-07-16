"""Model management utilities for efficient switching"""
import streamlit as st
import ollama
import time
from typing import Optional


def switch_model(new_model: str, old_model: Optional[str] = None) -> None:
    """
    Efficiently switch between models by unloading old and preloading new
    
    Args:
        new_model: Model to switch to
        old_model: Current model to unload (if different)
    """
    if old_model and old_model != new_model:
        # Unload the old model to free memory
        try:
            # Send empty prompt with 0 keep_alive to unload
            ollama.generate(
                model=old_model,
                prompt="",
                keep_alive=0
            )
            st.toast(f"📦 Unloaded {old_model}", icon="✅")
            time.sleep(0.5)  # Brief pause for memory cleanup
        except Exception as e:
            st.toast(f"⚠️ Could not unload {old_model}: {str(e)}", icon="⚠️")
    
    # Pre-load the new model
    with st.spinner(f"🔄 Loading {new_model}..."):
        try:
            start_time = time.time()
            # Quick generation to load model with 24h keep_alive
            ollama.generate(
                model=new_model,
                prompt="Hello",
                keep_alive="24h",
                options={'num_predict': 1}
            )
            load_time = time.time() - start_time
            st.toast(f"✅ Loaded {new_model} in {load_time:.1f}s", icon="🚀")
        except Exception as e:
            st.error(f"Failed to load {new_model}: {str(e)}")
            raise


def get_loaded_models() -> list:
    """Get list of currently loaded models in memory"""
    try:
        # This is a bit hacky - Ollama doesn't have a direct API for this
        # We check which models respond quickly (already loaded)
        loaded = []
        models = ollama.list()['models']
        
        for model in models:
            model_name = model['name'].split(':')[0]
            if model_name not in loaded:
                # Try a minimal request with very short timeout
                try:
                    start = time.time()
                    ollama.generate(
                        model=model_name,
                        prompt="",
                        keep_alive="24h",  # Keep it loaded
                        options={'num_predict': 0}
                    )
                    # If response is very fast, model was already loaded
                    if time.time() - start < 0.5:
                        loaded.append(model_name)
                except:
                    pass
        
        return loaded
    except:
        return []


def estimate_model_memory(model_name: str) -> float:
    """Estimate memory usage for a model in GB"""
    # Updated estimates based on actual ollama ps output
    size_map = {
        'phi': 2.3,
        'gemma:2b': 2.5,
        'qwen:4b': 3.5,
        'deepseek-coder': 5.5,
        'codellama': 5.5,
        'deepseek-llm': 5.8,
        'mistral': 5.9,
        'neural-chat': 5.9,
        'llama3': 6.7,
        'llama3:8b': 6.7,
        'mixtral': 26.0,  # Much larger!
    }
    
    # Check exact match first
    if model_name in size_map:
        return size_map[model_name]
    
    # Check base model name
    base_name = model_name.split(':')[0]
    return size_map.get(base_name, 4.0)  # Default 4GB