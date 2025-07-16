"""Model warm-up utilities to prevent cold start delays"""
import logging
import time
from typing import Optional
import requests
import threading

from src.config import Config
from src.local_llm import OptimizedLLM

logger = logging.getLogger(__name__)


class ModelWarmup:
    """Handles model preloading and warm-up to avoid cold starts"""
    
    def __init__(self):
        self.config = Config()
        self.warmed_up = set()
        self._warmup_lock = threading.Lock()
    
    def warmup_model(self, model_name: str = None) -> bool:
        """Warm up a specific model by running a simple query"""
        model_name = model_name or self.config.LOCAL_LLM_MODEL
        
        # Check if already warmed up
        with self._warmup_lock:
            if model_name in self.warmed_up:
                logger.info(f"Model {model_name} already warmed up")
                return True
        
        try:
            logger.info(f"Warming up model: {model_name}")
            start_time = time.time()
            
            # Simple test query to load the model
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": model_name,
                    "prompt": "Hello",
                    "stream": False,
                    "options": {
                        "num_predict": 1,  # Just one token
                        "temperature": 0.1
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                elapsed = time.time() - start_time
                logger.info(f"Model {model_name} warmed up in {elapsed:.2f}s")
                
                with self._warmup_lock:
                    self.warmed_up.add(model_name)
                
                return True
            else:
                logger.error(f"Failed to warm up model {model_name}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error warming up model {model_name}: {e}")
            return False
    
    def warmup_embeddings(self) -> bool:
        """Warm up the embedding model"""
        try:
            logger.info("Warming up embeddings model...")
            start_time = time.time()
            
            # Initialize embeddings which will download/load the model
            llm_system = OptimizedLLM(self.config)
            embeddings = llm_system.get_embeddings()
            
            # Run a test embedding
            test_text = "Hello world"
            _ = embeddings.embed_query(test_text)
            
            elapsed = time.time() - start_time
            logger.info(f"Embeddings model warmed up in {elapsed:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Error warming up embeddings: {e}")
            return False
    
    def warmup_all_models(self) -> None:
        """Warm up the configured model in the background"""
        def _warmup():
            try:
                # Only warm up the configured model
                configured_model = self.config.LOCAL_LLM_MODEL
                logger.info(f"Warming up configured model: {configured_model}")
                
                # Warm up the configured model
                self.warmup_model(configured_model)
                
                # Also warm up embeddings
                self.warmup_embeddings()
                
            except Exception as e:
                logger.error(f"Error in background warmup: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=_warmup, daemon=True)
        thread.start()
    
    def ensure_model_ready(self, model_name: str) -> bool:
        """Ensure a model is ready before use"""
        with self._warmup_lock:
            if model_name in self.warmed_up:
                return True
        
        # Warm up synchronously
        return self.warmup_model(model_name)


# Global instance
model_warmup = ModelWarmup()


def start_background_warmup():
    """Start warming up models in the background"""
    model_warmup.warmup_all_models()


def ensure_model_ready(model_name: str = None) -> bool:
    """Ensure a specific model is ready for use"""
    return model_warmup.ensure_model_ready(model_name or Config().LOCAL_LLM_MODEL)