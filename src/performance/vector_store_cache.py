"""Optimized vector store with caching and indexing"""
import time
import pickle
import hashlib
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import numpy as np
from collections import OrderedDict
import faiss
from langchain.schema import Document
from langchain_community.vectorstores import FAISS

from src.config import Config


class OptimizedVectorStore:
    """Optimized vector store with query caching and better indexing"""
    
    def __init__(self, cache_size: int = 1000):
        self.config = Config()
        self.cache_size = cache_size
        self.query_cache = OrderedDict()
        self.index_cache = {}
        
        # Create cache directory
        self.cache_dir = Path("cache/vector_queries")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, query: str, k: int, document_id: str) -> str:
        """Generate cache key for a query"""
        key_data = f"{document_id}:{query}:{k}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def cached_similarity_search(
        self, 
        vector_store: FAISS, 
        query: str, 
        k: int, 
        document_id: str
    ) -> List[Document]:
        """Perform similarity search with caching"""
        cache_key = self._get_cache_key(query, k, document_id)
        
        # Check cache
        if cache_key in self.query_cache:
            # Move to end (LRU)
            self.query_cache.move_to_end(cache_key)
            cached_result = self.query_cache[cache_key]
            
            # Check if cache is still valid (5 minutes)
            if time.time() - cached_result['timestamp'] < 300:
                return cached_result['documents']
        
        # Perform actual search
        documents = vector_store.similarity_search(query, k=k)
        
        # Cache result
        self.query_cache[cache_key] = {
            'documents': documents,
            'timestamp': time.time()
        }
        
        # Maintain cache size
        if len(self.query_cache) > self.cache_size:
            self.query_cache.popitem(last=False)
        
        return documents
    
    def optimize_index(self, vector_store: FAISS) -> FAISS:
        """Optimize FAISS index for faster queries"""
        # Get the raw index
        index = vector_store.index
        
        # If index is large enough, add IVF for faster search
        if index.ntotal > 1000:
            # Create an IVF index for faster search
            d = index.d  # dimensionality
            nlist = min(100, int(np.sqrt(index.ntotal)))  # number of clusters
            
            # Create IVF index
            quantizer = faiss.IndexFlatL2(d)
            index_ivf = faiss.IndexIVFFlat(quantizer, d, nlist)
            
            # Train the index
            if index.ntotal > 0:
                # Get all vectors
                vectors = index.reconstruct_n(0, index.ntotal)
                index_ivf.train(vectors)
                index_ivf.add(vectors)
                
                # Update vector store's index
                vector_store.index = index_ivf
        
        return vector_store
    
    def batch_similarity_search(
        self,
        vector_store: FAISS,
        queries: List[str],
        k: int = 5
    ) -> List[List[Document]]:
        """Perform batch similarity search for multiple queries"""
        # Get embeddings for all queries at once
        # The embedding_function is set when loading the vector store
        embeddings = vector_store.embedding_function.embed_documents(queries)
        
        # Convert to numpy array
        query_vectors = np.array(embeddings).astype('float32')
        
        # Perform batch search
        distances, indices = vector_store.index.search(query_vectors, k)
        
        # Convert results to documents
        results = []
        for i, query_indices in enumerate(indices):
            docs = []
            for j, idx in enumerate(query_indices):
                if idx >= 0:  # Valid index
                    doc = vector_store.docstore.search(vector_store.index_to_docstore_id[idx])
                    if doc:
                        docs.append(doc)
            results.append(docs)
        
        return results
    
    def create_hierarchical_index(self, documents: List[Document]) -> Dict[str, List[int]]:
        """Create hierarchical index for faster filtering"""
        index = {
            'by_page': {},
            'by_type': {},
            'by_source': {},
            'by_section': {}
        }
        
        for i, doc in enumerate(documents):
            metadata = doc.metadata
            
            # Index by page
            page = metadata.get('page', 'unknown')
            if page not in index['by_page']:
                index['by_page'][page] = []
            index['by_page'][page].append(i)
            
            # Index by type
            doc_type = metadata.get('type', 'unknown')
            if doc_type not in index['by_type']:
                index['by_type'][doc_type] = []
            index['by_type'][doc_type].append(i)
            
            # Index by source
            source = metadata.get('source', 'unknown')
            if source not in index['by_source']:
                index['by_source'][source] = []
            index['by_source'][source].append(i)
            
            # Index by section
            section = metadata.get('section', 'default')
            if section not in index['by_section']:
                index['by_section'][section] = []
            index['by_section'][section].append(i)
        
        return index
    
    def filtered_search(
        self,
        vector_store: FAISS,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Perform filtered similarity search"""
        if not filter_dict:
            return self.cached_similarity_search(vector_store, query, k, "default")
        
        # Get all documents that match filters
        all_docs = []
        for i in range(vector_store.index.ntotal):
            doc = vector_store.docstore.search(vector_store.index_to_docstore_id[i])
            if doc and self._matches_filter(doc, filter_dict):
                all_docs.append(doc)
        
        if not all_docs:
            return []
        
        # Create temporary vector store with filtered docs
        texts = [doc.page_content for doc in all_docs]
        metadatas = [doc.metadata for doc in all_docs]
        
        temp_store = FAISS.from_texts(
            texts=texts,
            embedding=vector_store.embedding_function,
            metadatas=metadatas
        )
        
        # Search in filtered store
        return temp_store.similarity_search(query, k=k)
    
    def _matches_filter(self, doc: Document, filter_dict: Dict[str, Any]) -> bool:
        """Check if document matches filter criteria"""
        for key, value in filter_dict.items():
            if key not in doc.metadata:
                return False
            if doc.metadata[key] != value:
                return False
        return True
    
    def save_cache_stats(self) -> None:
        """Save cache statistics for monitoring"""
        stats = {
            'cache_size': len(self.query_cache),
            'cache_hits': sum(1 for v in self.query_cache.values() 
                            if time.time() - v['timestamp'] < 300),
            'timestamp': time.time()
        }
        
        stats_path = self.cache_dir / "cache_stats.pkl"
        with open(stats_path, 'wb') as f:
            pickle.dump(stats, f)