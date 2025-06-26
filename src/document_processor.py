import os
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict
import pickle
import time
from datetime import datetime

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
import numpy as np

from src.config import Config
from src.local_llm import OptimizedLLM

class DocumentProcessor:
    def __init__(self):
        self.config = Config()
        self.config.create_directories()

        # Initialize LLM and embeddings
        self.llm_system = OptimizedLLM(self.config)
        self.embeddings = self.llm_system.get_embeddings()

        # Get optimal settings
        optimal = self.config.get_optimal_settings()

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=optimal["chunk_size"],
            chunk_overlap=self.config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    def generate_document_id(self, file_path: str) -> str:
        """Generate unique ID for document"""
        with open(file_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        return file_hash[:16]

    def process_pdf(self, file_path: str, filename: str) -> Tuple[str, int, int, float]:
        """Process PDF with progress tracking"""
        start_time = time.time()

        print(f"Loading PDF: {filename}")
        loader = PyPDFLoader(file_path)
        documents = loader.load()

        doc_id = self.generate_document_id(file_path)

        print(f"Splitting into chunks...")
        chunks = self.text_splitter.split_documents(documents)

        # Add metadata
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'document_id': doc_id,
                'filename': filename,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'page': chunk.metadata.get('page', 0)
            })

        print(f"Creating embeddings for {len(chunks)} chunks...")

        # Process in batches to manage memory
        batch_size = self.config.BATCH_SIZE
        all_embeddings = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_texts = [chunk.page_content for chunk in batch]

            # Generate embeddings
            batch_embeddings = self.embeddings.embed_documents(batch_texts)
            all_embeddings.extend(batch_embeddings)

            # Progress indicator
            progress = min(100, (i + batch_size) / len(chunks) * 100)
            print(f"Progress: {progress:.1f}%")

        # Create FAISS index
        print("Building vector index...")
        vector_store = FAISS.from_embeddings(
            text_embeddings=list(zip([c.page_content for c in chunks], all_embeddings)),
            embedding=self.embeddings,
            metadatas=[c.metadata for c in chunks]
        )

        # Save vector store
        vector_store_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
        vector_store.save_local(str(vector_store_path))

        # Save metadata
        processing_time = time.time() - start_time
        metadata = {
            'document_id': doc_id,
            'filename': filename,
            'pages': len(documents),
            'chunks': len(chunks),
            'upload_date': datetime.now(),
            'processing_time': processing_time,
            'file_size_mb': os.path.getsize(file_path) / (1024 * 1024),
            'model_used': self.config.LOCAL_LLM_MODEL
        }

        metadata_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.metadata"
        with open(metadata_path, 'wb') as f:
            pickle.dump(metadata, f)

        print(f"Processing complete in {processing_time:.1f} seconds")
        
        # Auto-cleanup old documents if needed
        self._cleanup_old_documents()
        
        return doc_id, len(documents), len(chunks), processing_time

    def load_vector_store(self, document_id: str) -> FAISS:
        """Load existing vector store"""
        vector_store_path = self.config.VECTOR_STORE_DIR / f"{document_id}.faiss"
        if not vector_store_path.exists():
            raise ValueError(f"Document {document_id} not found")

        return FAISS.load_local(
            str(vector_store_path),
            self.embeddings,
            allow_dangerous_deserialization=True
        )
    
    def _cleanup_old_documents(self):
        """Remove old documents to manage storage"""
        try:
            max_docs = int(os.getenv('MAX_DOCUMENTS', '20'))
            cleanup_days = int(os.getenv('CLEANUP_DAYS', '7'))
            
            # Get all metadata files with their modification times
            metadata_files = []
            for f in self.config.VECTOR_STORE_DIR.glob("*.metadata"):
                metadata_files.append((f, f.stat().st_mtime))
            
            # Sort by modification time (oldest first)
            metadata_files.sort(key=lambda x: x[1])
            
            # Remove oldest documents if we exceed max count
            if len(metadata_files) > max_docs:
                files_to_remove = len(metadata_files) - max_docs
                for i in range(files_to_remove):
                    metadata_file = metadata_files[i][0]
                    doc_id = metadata_file.stem
                    
                    # Remove vector store
                    vector_store_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
                    if vector_store_path.exists():
                        import shutil
                        shutil.rmtree(vector_store_path)
                    
                    # Remove metadata
                    metadata_file.unlink()
                    
                    print(f"Auto-removed old document: {doc_id}")
            
            # Also remove documents older than cleanup_days
            current_time = time.time()
            for metadata_file, mtime in metadata_files:
                age_days = (current_time - mtime) / (24 * 3600)
                if age_days > cleanup_days:
                    doc_id = metadata_file.stem
                    
                    # Remove vector store
                    vector_store_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
                    if vector_store_path.exists():
                        import shutil
                        shutil.rmtree(vector_store_path)
                    
                    # Remove metadata
                    metadata_file.unlink()
                    
                    print(f"Auto-removed expired document: {doc_id} (age: {age_days:.1f} days)")
                    
        except Exception as e:
            print(f"Cleanup error: {e}")
            # Don't fail the main process if cleanup fails
            pass