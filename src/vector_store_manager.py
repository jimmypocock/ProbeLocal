"""Vector store management with automatic cleanup and monitoring"""
import os
import time
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import threading
import json

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """Manages vector stores with automatic cleanup and monitoring"""
    
    def __init__(self, vector_store_dir: Path, upload_dir: Path):
        self.vector_store_dir = Path(vector_store_dir)
        self.upload_dir = Path(upload_dir)
        self.vector_store_dir.mkdir(exist_ok=True)
        
        # Configuration
        self.max_documents = int(os.getenv('MAX_DOCUMENTS', '20'))
        self.cleanup_days = int(os.getenv('CLEANUP_DAYS', '7'))
        self.cleanup_interval = int(os.getenv('CLEANUP_INTERVAL_HOURS', '1')) * 3600
        
        # Thread safety
        self._cleanup_lock = threading.Lock()
        self._last_cleanup = 0
        
        logger.info(f"VectorStoreManager initialized: max_docs={self.max_documents}, "
                   f"cleanup_days={self.cleanup_days}, interval={self.cleanup_interval}s")
    
    def should_cleanup(self) -> bool:
        """Check if cleanup should run"""
        return time.time() - self._last_cleanup > self.cleanup_interval
    
    def cleanup_old_stores(self, force: bool = False) -> Dict[str, any]:
        """Remove old vector stores based on age and count limits
        
        Args:
            force: Force cleanup even if interval hasn't passed
            
        Returns:
            Dict with cleanup statistics
        """
        if not force and not self.should_cleanup():
            return {"skipped": True, "reason": "cleanup interval not reached"}
        
        with self._cleanup_lock:
            try:
                self._last_cleanup = time.time()
                stats = {
                    "removed_by_age": [],
                    "removed_by_count": [],
                    "errors": [],
                    "total_before": 0,
                    "total_after": 0
                }
                
                # Get all vector stores with metadata
                stores = self._get_all_stores()
                stats["total_before"] = len(stores)
                
                if not stores:
                    return stats
                
                # Remove by age first
                current_time = time.time()
                cutoff_time = current_time - (self.cleanup_days * 24 * 3600)
                
                remaining_stores = []
                for store_info in stores:
                    if store_info['modified_time'] < cutoff_time:
                        if self._remove_store(store_info['doc_id']):
                            stats["removed_by_age"].append({
                                "doc_id": store_info['doc_id'],
                                "age_days": (current_time - store_info['modified_time']) / (24 * 3600)
                            })
                        else:
                            stats["errors"].append(store_info['doc_id'])
                    else:
                        remaining_stores.append(store_info)
                
                # Sort remaining by modification time (oldest first)
                remaining_stores.sort(key=lambda x: x['modified_time'])
                
                # Remove by count limit
                while len(remaining_stores) > self.max_documents:
                    store_info = remaining_stores.pop(0)
                    if self._remove_store(store_info['doc_id']):
                        stats["removed_by_count"].append(store_info['doc_id'])
                    else:
                        stats["errors"].append(store_info['doc_id'])
                
                stats["total_after"] = len(remaining_stores)
                
                # Log summary
                total_removed = len(stats["removed_by_age"]) + len(stats["removed_by_count"])
                if total_removed > 0:
                    logger.info(f"Vector store cleanup: removed {total_removed} stores "
                              f"({len(stats['removed_by_age'])} by age, "
                              f"{len(stats['removed_by_count'])} by count)")
                
                return stats
                
            except Exception as e:
                logger.error(f"Error during vector store cleanup: {e}")
                return {"error": str(e)}
    
    def _get_all_stores(self) -> List[Dict]:
        """Get information about all vector stores"""
        stores = []
        
        for metadata_file in self.vector_store_dir.glob("*.metadata"):
            try:
                doc_id = metadata_file.stem
                vector_store_path = self.vector_store_dir / f"{doc_id}.faiss"
                
                # Check if vector store exists
                if not vector_store_path.exists():
                    logger.warning(f"Orphaned metadata file: {metadata_file}")
                    continue
                
                # Get file stats
                stat = metadata_file.stat()
                
                # Load metadata
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                stores.append({
                    "doc_id": doc_id,
                    "metadata_file": metadata_file,
                    "vector_store_path": vector_store_path,
                    "modified_time": stat.st_mtime,
                    "size": stat.st_size,
                    "metadata": metadata
                })
                
            except Exception as e:
                logger.warning(f"Error reading metadata for {metadata_file}: {e}")
                continue
        
        return stores
    
    def _remove_store(self, doc_id: str) -> bool:
        """Remove a vector store and its metadata"""
        try:
            # Remove vector store directory
            vector_store_path = self.vector_store_dir / f"{doc_id}.faiss"
            if vector_store_path.exists():
                if vector_store_path.is_dir():
                    shutil.rmtree(vector_store_path)
                else:
                    vector_store_path.unlink()
            
            # Remove metadata file
            metadata_file = self.vector_store_dir / f"{doc_id}.metadata"
            if metadata_file.exists():
                metadata_file.unlink()
            
            logger.info(f"Removed vector store: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing vector store {doc_id}: {e}")
            return False
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        try:
            stores = self._get_all_stores()
            
            total_size = 0
            oldest_time = time.time()
            newest_time = 0
            
            for store in stores:
                # Calculate total size
                if store['vector_store_path'].is_dir():
                    size = sum(f.stat().st_size for f in store['vector_store_path'].rglob('*'))
                else:
                    size = store['vector_store_path'].stat().st_size
                total_size += size + store['size']  # Include metadata size
                
                # Track age
                oldest_time = min(oldest_time, store['modified_time'])
                newest_time = max(newest_time, store['modified_time'])
            
            return {
                "total_documents": len(stores),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_days": round((time.time() - oldest_time) / (24 * 3600), 1) if stores else 0,
                "newest_days": round((time.time() - newest_time) / (24 * 3600), 1) if stores else 0,
                "max_documents": self.max_documents,
                "cleanup_days": self.cleanup_days,
                "next_cleanup_minutes": round((self._last_cleanup + self.cleanup_interval - time.time()) / 60, 1)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {"error": str(e)}
    
    def cleanup_orphaned_files(self) -> int:
        """Clean up orphaned files in upload directory"""
        try:
            cleaned = 0
            
            # Clean old uploaded files
            for file_path in self.upload_dir.glob("*"):
                try:
                    # Skip directories
                    if file_path.is_dir():
                        continue
                    
                    # Check age
                    age_hours = (time.time() - file_path.stat().st_mtime) / 3600
                    if age_hours > 24:  # Remove uploaded files older than 24 hours
                        file_path.unlink()
                        cleaned += 1
                        logger.info(f"Removed old upload file: {file_path.name}")
                        
                except Exception as e:
                    logger.warning(f"Error cleaning upload file {file_path}: {e}")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning upload directory: {e}")
            return 0