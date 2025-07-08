"""Incremental document processor for handling large files without timeouts"""
import os
import time
import logging
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path
import hashlib
import json

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, CSVLoader, UnstructuredMarkdownLoader,
    Docx2txtLoader, UnstructuredExcelLoader, UnstructuredImageLoader
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from src.config import Config
from src.security import validate_vector_store_path

logger = logging.getLogger(__name__)


class IncrementalProcessor:
    """Process documents incrementally to handle large files"""
    
    def __init__(self):
        self.config = Config()
        
        # Suppress tokenization warnings
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*clean_up_tokenization_spaces.*")
            
            # Set environment variables to prevent HTTP requests
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"
            
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.EMBEDDING_MODEL,
                    model_kwargs={
                        'device': 'cpu',
                        'trust_remote_code': False,
                        'local_files_only': True
                    },
                    encode_kwargs={'normalize_embeddings': True}
                )
            except Exception as e:
                # Fallback without local_files_only
                print(f"Warning: Could not load embeddings with local_files_only: {e}")
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.EMBEDDING_MODEL,
                    model_kwargs={'device': 'cpu', 'trust_remote_code': False},
                    encode_kwargs={'normalize_embeddings': True}
                )
        
        # Processing state directory
        self.state_dir = Path("processing_state")
        self.state_dir.mkdir(exist_ok=True)
    
    def process_file_incremental(
        self,
        file_path: str,
        file_name: str,
        chunk_size: Optional[int] = None,
        batch_size: int = 50,
        progress_callback: Optional[callable] = None
    ) -> Tuple[str, int, int, float]:
        """
        Process a file incrementally in batches
        
        Args:
            file_path: Path to the file
            file_name: Original filename
            chunk_size: Size of text chunks
            batch_size: Number of chunks to process at once
            progress_callback: Function to call with progress updates
            
        Returns:
            Tuple of (document_id, pages, chunks, processing_time)
        """
        start_time = time.time()
        doc_id = self._generate_document_id(file_path)
        
        # Check if processing was already started
        state = self._load_state(doc_id)
        
        try:
            # Load document
            if progress_callback:
                progress_callback(0.1, "Loading document...")
            
            documents = self._load_document(file_path)
            total_pages = len(documents)
            
            # Split into chunks
            if progress_callback:
                progress_callback(0.2, "Splitting into chunks...")
            
            chunk_size = chunk_size or self.config.CHUNK_SIZE
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=self.config.CHUNK_OVERLAP,
                length_function=len,
                separators=["\n\n", "\n", " ", ""]
            )
            
            all_chunks = text_splitter.split_documents(documents)
            total_chunks = len(all_chunks)
            
            # Initialize or load vector store
            if state and 'processed_chunks' in state:
                # Resume from previous state
                vector_store = self._load_vector_store(doc_id)
                processed_chunks = state['processed_chunks']
                logger.info(f"Resuming from chunk {processed_chunks}/{total_chunks}")
            else:
                # Start fresh
                vector_store = None
                processed_chunks = 0
                self._save_state(doc_id, {
                    'total_chunks': total_chunks,
                    'processed_chunks': 0,
                    'file_name': file_name,
                    'total_pages': total_pages
                })
            
            # Process chunks in batches
            while processed_chunks < total_chunks:
                batch_start = processed_chunks
                batch_end = min(processed_chunks + batch_size, total_chunks)
                batch_chunks = all_chunks[batch_start:batch_end]
                
                if progress_callback:
                    progress = 0.2 + (0.7 * processed_chunks / total_chunks)
                    progress_callback(
                        progress,
                        f"Processing chunks {batch_start + 1}-{batch_end} of {total_chunks}..."
                    )
                
                # Process batch
                if vector_store is None:
                    # Create new vector store with first batch
                    vector_store = FAISS.from_documents(
                        batch_chunks,
                        self.embeddings
                    )
                else:
                    # Add to existing vector store
                    texts = [chunk.page_content for chunk in batch_chunks]
                    metadatas = [chunk.metadata for chunk in batch_chunks]
                    vector_store.add_texts(texts, metadatas)
                
                # Save progress
                processed_chunks = batch_end
                self._save_state(doc_id, {
                    'total_chunks': total_chunks,
                    'processed_chunks': processed_chunks,
                    'file_name': file_name,
                    'total_pages': total_pages
                })
                
                # Save vector store checkpoint
                self._save_vector_store(vector_store, doc_id)
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
            
            # Final save
            if progress_callback:
                progress_callback(0.9, "Finalizing...")
            
            # Save to permanent location
            permanent_path = self.config.VECTOR_STORE_DIR / f"{doc_id}.faiss"
            vector_store.save_local(str(permanent_path))
            
            # Save metadata
            metadata = {
                'filename': file_name,
                'pages': total_pages,
                'chunks': total_chunks,
                'upload_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                'chunk_size': chunk_size
            }
            
            metadata_path = self.config.VECTOR_STORE_DIR / f"{doc_id}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Clean up state
            self._clean_state(doc_id)
            
            processing_time = time.time() - start_time
            
            if progress_callback:
                progress_callback(1.0, "Complete!")
            
            logger.info(f"Processed {file_name}: {total_pages} pages, {total_chunks} chunks in {processing_time:.2f}s")
            
            return doc_id, total_pages, total_chunks, processing_time
            
        except Exception as e:
            logger.error(f"Error processing file incrementally: {e}")
            # Save error state
            if 'state' in locals():
                state = self._load_state(doc_id) or {}
                state['error'] = str(e)
                self._save_state(doc_id, state)
            raise
    
    def _generate_document_id(self, file_path: str) -> str:
        """Generate unique ID for document"""
        file_stat = os.stat(file_path)
        content = f"{file_path}_{file_stat.st_size}_{file_stat.st_mtime}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _load_document(self, file_path: str) -> List:
        """Load document based on file type"""
        file_ext = Path(file_path).suffix.lower()
        
        loaders = {
            '.pdf': PyPDFLoader,
            '.txt': TextLoader,
            '.csv': CSVLoader,
            '.md': UnstructuredMarkdownLoader,
            '.docx': Docx2txtLoader,
            '.xlsx': UnstructuredExcelLoader,
            '.xls': UnstructuredExcelLoader,
            '.png': UnstructuredImageLoader,
            '.jpg': UnstructuredImageLoader,
            '.jpeg': UnstructuredImageLoader
        }
        
        loader_class = loaders.get(file_ext)
        if not loader_class:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        loader = loader_class(file_path)
        return loader.load()
    
    def _save_state(self, doc_id: str, state: Dict[str, Any]) -> None:
        """Save processing state"""
        state_file = self.state_dir / f"{doc_id}_state.json"
        with open(state_file, 'w') as f:
            json.dump(state, f)
    
    def _load_state(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Load processing state"""
        state_file = self.state_dir / f"{doc_id}_state.json"
        if state_file.exists():
            with open(state_file, 'r') as f:
                return json.load(f)
        return None
    
    def _clean_state(self, doc_id: str) -> None:
        """Clean up processing state"""
        state_file = self.state_dir / f"{doc_id}_state.json"
        if state_file.exists():
            state_file.unlink()
        
        # Clean checkpoint
        checkpoint_path = self.state_dir / f"{doc_id}_checkpoint.faiss"
        if checkpoint_path.exists():
            import shutil
            shutil.rmtree(checkpoint_path)
    
    def _save_vector_store(self, vector_store: FAISS, doc_id: str) -> None:
        """Save vector store checkpoint"""
        checkpoint_path = self.state_dir / f"{doc_id}_checkpoint.faiss"
        vector_store.save_local(str(checkpoint_path))
    
    def _load_vector_store(self, doc_id: str) -> Optional[FAISS]:
        """Load vector store checkpoint"""
        checkpoint_path = self.state_dir / f"{doc_id}_checkpoint.faiss"
        if checkpoint_path.exists():
            # Validate path for security
            if not validate_vector_store_path(checkpoint_path, self.state_dir):
                logger.warning(f"Invalid checkpoint path: {checkpoint_path}")
                return None
                
            return FAISS.load_local(
                str(checkpoint_path),
                self.embeddings,
                allow_dangerous_deserialization=True  # Required by FAISS, but path is validated
            )
        return None
    
    def get_processing_status(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get current processing status"""
        state = self._load_state(doc_id)
        if state:
            progress = state.get('processed_chunks', 0) / state.get('total_chunks', 1)
            return {
                'status': 'error' if 'error' in state else 'processing',
                'progress': progress,
                'processed_chunks': state.get('processed_chunks', 0),
                'total_chunks': state.get('total_chunks', 0),
                'error': state.get('error')
            }
        return None