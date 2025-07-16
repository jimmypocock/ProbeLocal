#!/usr/bin/env python3
"""
Preprocess test documents into a separate unified vector store for testing
This avoids interfering with the user's actual documents
"""
import os
import sys
import glob
import shutil
from pathlib import Path
from typing import List

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config
from src.unified_document_processor import UnifiedDocumentProcessor


def preprocess_test_documents(test_documents_path: str = "test_documents"):
    """Process test documents into a separate vector store"""
    print("🚀 Test Document Preprocessing Script")
    print("=" * 40)
    
    # Create test paths
    test_docs_path = Path(test_documents_path)
    test_vector_path = Path("test_vector_stores")
    
    if not test_docs_path.exists():
        print(f"❌ Test documents folder '{test_documents_path}' not found")
        return False
    
    # Clear test vector stores
    if test_vector_path.exists():
        print("🗑️  Clearing test vector stores...")
        shutil.rmtree(test_vector_path)
    test_vector_path.mkdir(exist_ok=True)
    
    # Get test documents
    supported_extensions = ['.pdf', '.txt', '.csv', '.md', '.docx', '.xlsx', '.xls', '.png', '.jpg', '.jpeg']
    documents = []
    
    for ext in supported_extensions:
        pattern = str(test_docs_path / f"*{ext}")
        files = glob.glob(pattern)
        documents.extend(files)
    
    if not documents:
        print(f"❌ No documents found in {test_documents_path}/")
        return False
    
    print(f"\n📚 Found {len(documents)} test document(s) to process:")
    for doc in sorted(documents):
        print(f"   - {os.path.basename(doc)}")
    
    # Create processor with test paths
    processor = UnifiedDocumentProcessor()
    
    # Override the vector store directory to use test location
    original_dir = processor.config.VECTOR_STORE_DIR
    processor.config.VECTOR_STORE_DIR = test_vector_path
    
    try:
        # Process documents
        print("\n📚 Creating test unified vector store...")
        result = processor.process_documents(documents)
        
        if result and isinstance(result, dict) and result.get('total_chunks', 0) > 0:
            print("\n✅ Test unified vector store created successfully!")
            print(f"📁 Location: {test_vector_path}/unified_store.faiss")
            print(f"📊 Total chunks: {result.get('total_chunks', 0)}")
            print(f"📄 Total documents: {result.get('total_documents', 0)}")
            return True
        else:
            print("\n❌ Failed to create test unified vector store")
            if result:
                print(f"Result: {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Restore original directory
        processor.config.VECTOR_STORE_DIR = original_dir


if __name__ == "__main__":
    # Allow custom test documents path from command line
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', default='test_documents', help='Path to test documents folder')
    args = parser.parse_args()
    
    success = preprocess_test_documents(args.path)
    sys.exit(0 if success else 1)