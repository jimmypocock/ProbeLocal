"""
Memory-safe embeddings wrapper to prevent GPU OOM errors
"""
import torch
from typing import List
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.embeddings import Embeddings


class MemorySafeEmbeddings(Embeddings):
    """Wrapper around HuggingFaceEmbeddings that processes in smaller batches"""
    
    def __init__(self, base_embeddings: HuggingFaceEmbeddings, batch_size: int = 2):
        self.base_embeddings = base_embeddings
        self.batch_size = batch_size
        # Copy essential attributes that FAISS might look for
        self.client = getattr(base_embeddings, 'client', None)
        self.model_name = getattr(base_embeddings, 'model_name', 'all-MiniLM-L6-v2')
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed documents in small batches to prevent OOM"""
        if not texts:
            return []
        
        # Process in small batches
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            
            try:
                # Embed this batch
                batch_embeddings = self.base_embeddings.embed_documents(batch)
                all_embeddings.extend(batch_embeddings)
                
                # Clear GPU cache after each batch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif torch.backends.mps.is_available():
                    # For Apple Silicon, we can't directly clear cache but we can suggest GC
                    import gc
                    gc.collect()
                    
            except Exception as e:
                print(f"Error embedding batch {i//self.batch_size}: {e}")
                # Fall back to CPU if GPU fails
                if hasattr(self.base_embeddings, 'model_kwargs'):
                    self.base_embeddings.model_kwargs['device'] = 'cpu'
                    batch_embeddings = self.base_embeddings.embed_documents(batch)
                    all_embeddings.extend(batch_embeddings)
                else:
                    raise
        
        return all_embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed a single query"""
        try:
            return self.base_embeddings.embed_query(text)
        except Exception as e:
            print(f"Error embedding query: {e}")
            # Try with CPU if GPU fails
            if hasattr(self.base_embeddings, 'model_kwargs'):
                original_device = self.base_embeddings.model_kwargs.get('device', 'cpu')
                self.base_embeddings.model_kwargs['device'] = 'cpu'
                result = self.base_embeddings.embed_query(text)
                self.base_embeddings.model_kwargs['device'] = original_device
                return result
            else:
                raise
    
    def __getattr__(self, name):
        """Proxy other attributes to base embeddings"""
        return getattr(self.base_embeddings, name)
