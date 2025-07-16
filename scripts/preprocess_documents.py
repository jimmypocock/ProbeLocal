#!/usr/bin/env python3
"""
Preprocess all documents in the documents/ folder into a unified vector store
Clears existing vector stores and creates a single unified store with source metadata
"""
import os
import sys
import glob
import requests
import hashlib
import shutil
from pathlib import Path
from typing import List

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.unified_document_processor import UnifiedDocumentProcessor


def ensure_vector_stores_dir():
    """Ensure vector_stores directory exists"""
    vector_store_path = Path("vector_stores")
    if not vector_store_path.exists():
        vector_store_path.mkdir(exist_ok=True)
        print("📁 Created vector_stores directory")


def clear_uploads():
    """Clear uploads directory"""
    uploads_path = Path("uploads")
    if uploads_path.exists():
        print("🗑️  Clearing uploads directory...")
        shutil.rmtree(uploads_path)
        uploads_path.mkdir(exist_ok=True)
        print("✅ Uploads directory cleared")
    else:
        uploads_path.mkdir(exist_ok=True)


def get_documents_to_process():
    """Get all documents from the documents folder"""
    documents_path = Path("documents")
    if not documents_path.exists():
        documents_path.mkdir(exist_ok=True)
        print("📁 Created documents directory")
        return []
    
    # Supported file extensions
    extensions = ['*.pdf', '*.txt', '*.csv', '*.md', '*.docx', '*.xlsx', '*.png', '*.jpg', '*.jpeg']
    
    documents = []
    for ext in extensions:
        documents.extend(documents_path.glob(ext))
    
    # Sort for consistent processing order
    documents.sort()
    
    return documents


def process_documents_unified(documents: List[Path]):
    """Process all documents into a unified vector store"""
    print("\n📚 Creating unified vector store...")
    
    # Initialize the unified processor
    processor = UnifiedDocumentProcessor()
    
    # Convert Path objects to strings
    file_paths = [str(doc) for doc in documents]
    
    try:
        # Process all documents together
        def progress_callback(current, total, filename):
            print(f"   [{current}/{total}] Processing {filename}...")
        
        metadata = processor.process_documents(file_paths, progress_callback)
        
        print(f"\n✅ Unified vector store created successfully!")
        print(f"   - Documents: {metadata['total_documents']}")
        print(f"   - Total chunks: {metadata['total_chunks']}")
        print(f"   - Processing time: {metadata['processing_time']:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating unified vector store: {str(e)}")
        return False


def main():
    """Main preprocessing function"""
    print("🚀 Unified Document Preprocessing Script")
    print("=======================================\n")
    
    # Ensure directories exist (vector stores already cleared by run.sh)
    ensure_vector_stores_dir()
    clear_uploads()
    
    # Get documents to process
    documents = get_documents_to_process()
    
    if not documents:
        print("\n⚠️  No documents found in documents/ folder")
        print("💡 Add PDF, TXT, CSV, MD, DOCX, or image files to the documents/ folder")
        return
    
    print(f"\n📚 Found {len(documents)} document(s) to process:")
    for doc in documents:
        print(f"   - {doc.name}")
    
    # Process all documents into unified store
    success = process_documents_unified(documents)
    
    # Summary
    print("\n" + "="*50)
    if success:
        print("✅ All documents successfully processed into unified vector store!")
    else:
        print("❌ Failed to create unified vector store")
        print("💡 Check the error messages above for details")
    
    print("\n🎉 Preprocessing complete! Ready to launch app.")


if __name__ == "__main__":
    main()