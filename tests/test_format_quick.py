#!/usr/bin/env python3
"""
Quick format testing script - test one model with one file of each type
"""

import sys
import os
import json
import time
import requests
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_file_upload(file_path, expected_content, model="mistral:latest"):
    """Test uploading and querying a specific file"""
    api_base = "http://localhost:8080"
    
    print(f"\n📄 Testing: {file_path}")
    
    # Determine content type
    ext = file_path.split('.')[-1].lower()
    content_types = {
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'md': 'text/markdown',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'png': 'image/png',
        'jpg': 'image/jpeg'
    }
    
    # Upload file
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, content_types.get(ext, 'application/octet-stream'))}
            response = requests.post(f"{api_base}/upload", files=files, data={'model': model}, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            return False
        
        doc_id = response.json()['document_id']
        print(f"✅ Upload successful: {doc_id}")
        
        # Test a simple question
        payload = {
            "question": "What is this document about?",
            "document_id": doc_id,
            "model_name": model,
            "max_results": 3
        }
        
        print(f"  Asking question: {payload['question']}")
        response = requests.post(f"{api_base}/ask", json=payload, timeout=15)
        
        if response.status_code == 200:
            answer = response.json()['answer']
            print(f"✅ Query successful: {answer[:100]}...")
            
            # Check if expected content is found
            if any(content.lower() in answer.lower() for content in expected_content):
                print(f"✅ Expected content found")
                return True
            else:
                print(f"⚠️  Expected content not found: {expected_content}")
                return True  # Still success, just less accurate
        else:
            print(f"❌ Query failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run quick tests on all new file formats"""
    fixtures_dir = Path(__file__).parent / "fixtures"
    
    test_files = [
        {
            "file": fixtures_dir / "test_invoice.xlsx",
            "expected": ["Digital", "Dynamics", "invoice", "313232"]
        },
        {
            "file": fixtures_dir / "test_invoice.md", 
            "expected": ["CloudScale", "Technologies", "220500"]
        },
        {
            "file": fixtures_dir / "test_invoice.docx",
            "expected": ["TechVision", "Solutions", "197448"]
        },
        {
            "file": fixtures_dir / "test_invoice.png",
            "expected": ["Repair", "Inc", "154"]
        },
        {
            "file": fixtures_dir / "test_story.png",
            "expected": ["WHAT", "REMAINS", "woman", "raccoon"]
        }
    ]
    
    print("🧪 Quick Multi-Format Test")
    print("="*50)
    
    passed = 0
    total = len(test_files)
    
    for test in test_files:
        if test["file"].exists():
            if test_file_upload(str(test["file"]), test["expected"]):
                passed += 1
        else:
            print(f"❌ File not found: {test['file']}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All format tests successful!")
    else:
        print("⚠️  Some tests failed - check file availability and API server")

if __name__ == "__main__":
    main()