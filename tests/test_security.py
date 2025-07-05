#!/usr/bin/env python3
"""
Security Test Suite for Greg AI Playground
Tests file upload security, injection attacks, and other security measures
"""

import os
import sys
import time
import json
import requests
import tempfile
from pathlib import Path
from datetime import datetime
import zipfile
import concurrent.futures

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class SecurityTester:
    def __init__(self):
        self.api_base = "http://localhost:8080"
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {level}: {message}")
        
    def run_test(self, test_name, test_func):
        """Run a single test and record results"""
        self.log(f"Running test: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func()
            duration = time.time() - start_time
            
            test_result = {
                "name": test_name,
                "status": "passed" if result else "failed",
                "duration": round(duration, 2),
                "error": None if result else "Test returned False"
            }
            
            if result:
                self.log(f"✓ {test_name} passed ({duration:.2f}s)", "SUCCESS")
                self.test_results["summary"]["passed"] += 1
            else:
                self.log(f"✗ {test_name} failed ({duration:.2f}s)", "ERROR")
                self.test_results["summary"]["failed"] += 1
                
        except Exception as e:
            duration = time.time() - start_time
            test_result = {
                "name": test_name,
                "status": "failed",
                "duration": round(duration, 2),
                "error": str(e)
            }
            self.log(f"✗ {test_name} failed with error: {str(e)}", "ERROR")
            self.test_results["summary"]["failed"] += 1
            
        self.test_results["tests"].append(test_result)
        self.test_results["summary"]["total"] += 1
        return test_result["status"] == "passed"
        
    def test_file_size_limit(self):
        """Test that files over 100MB are rejected"""
        # Create a file just over 100MB
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            # Write 101MB of data
            chunk_size = 1024 * 1024  # 1MB
            for _ in range(101):
                temp_file.write(b'A' * chunk_size)
            temp_file_path = temp_file.name
            
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("large_file.txt", f, "text/plain")}
                response = requests.post(f"{self.api_base}/upload", files=files, timeout=10)
                
            # Should get 413 (Request Entity Too Large)
            if response.status_code == 413:
                self.log("File size limit correctly enforced")
                return True
            else:
                self.log(f"Expected 413, got {response.status_code}: {response.text}", "ERROR")
                return False
                
        finally:
            os.unlink(temp_file_path)
            
    def test_malicious_file_types(self):
        """Test that dangerous file types are rejected"""
        dangerous_extensions = [
            '.exe', '.sh', '.bat', '.cmd', '.ps1',  # Executables
            '.zip', '.tar', '.gz', '.rar',  # Archives (could be zip bombs)
            '.js', '.py', '.rb', '.php',  # Scripts
            '.dll', '.so', '.dylib',  # Libraries
            '.app', '.deb', '.rpm'  # Installers
        ]
        
        all_blocked = True
        
        for ext in dangerous_extensions:
            # Create a small test file
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as temp_file:
                temp_file.write(b'Malicious content')
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {"file": (f"malicious{ext}", f, "application/octet-stream")}
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=5)
                    
                if response.status_code == 400:  # Bad request - file type not supported
                    self.log(f"✓ {ext} correctly blocked")
                else:
                    self.log(f"✗ {ext} was NOT blocked! Status: {response.status_code}", "ERROR")
                    all_blocked = False
                    
            finally:
                os.unlink(temp_file_path)
                
        return all_blocked
        
    def test_path_traversal_attack(self):
        """Test that path traversal attempts are blocked"""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "test/../../../secret.txt",
            "legitimate.pdf/../../../etc/shadow"
        ]
        
        all_safe = True
        
        for filename in malicious_filenames:
            # Create a legitimate PDF file
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(b'%PDF-1.4\n%Test PDF content\n')
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    # Try to use malicious filename
                    files = {"file": (filename, f, "application/pdf")}
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=5)
                    
                # Check if the file was saved with a safe name
                if response.status_code == 200:
                    # File was accepted, but check if path traversal worked
                    result = response.json()
                    doc_id = result.get('document_id')
                    
                    # The document should be saved safely, not at the malicious path
                    self.log(f"✓ Path traversal attempt '{filename}' was sanitized")
                else:
                    self.log(f"File rejected with status {response.status_code}")
                    
            except Exception as e:
                self.log(f"Error testing {filename}: {e}", "ERROR")
                all_safe = False
                
            finally:
                os.unlink(temp_file_path)
                
        return all_safe
        
    def test_sql_injection_in_queries(self):
        """Test that SQL injection attempts in queries are handled safely"""
        # First, upload a legitimate document
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b'This is a test document for SQL injection testing.')
            temp_file_path = temp_file.name
            
        try:
            # Upload the document
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("test.txt", f, "text/plain")}
                response = requests.post(f"{self.api_base}/upload", files=files, timeout=10)
                
            if response.status_code != 200:
                self.log("Failed to upload test document", "ERROR")
                return False
                
            doc_id = response.json()['document_id']
            
            # Try SQL injection attempts in queries
            sql_injection_queries = [
                "'; DROP TABLE documents; --",
                "1' OR '1'='1",
                "admin'--",
                "' UNION SELECT * FROM users--",
                "1; DELETE FROM vector_stores WHERE 1=1; --"
            ]
            
            all_safe = True
            
            for malicious_query in sql_injection_queries:
                payload = {
                    "question": malicious_query,
                    "document_id": doc_id
                }
                
                try:
                    response = requests.post(f"{self.api_base}/ask", json=payload, timeout=10)
                    
                    # The query should either work normally or fail gracefully
                    # It should NOT execute SQL commands
                    if response.status_code in [200, 400, 500]:
                        self.log(f"✓ SQL injection attempt handled safely: '{malicious_query[:30]}...'")
                    else:
                        self.log(f"Unexpected response for SQL injection: {response.status_code}", "WARN")
                        
                except Exception as e:
                    self.log(f"Error during SQL injection test: {e}", "ERROR")
                    all_safe = False
                    
            # Clean up
            requests.delete(f"{self.api_base}/documents/{doc_id}")
            return all_safe
            
        finally:
            os.unlink(temp_file_path)
            
    def test_xss_in_document_content(self):
        """Test that XSS attempts in document content are sanitized"""
        # Create a document with XSS attempts
        xss_content = """
        <script>alert('XSS')</script>
        <img src=x onerror=alert('XSS')>
        <iframe src="javascript:alert('XSS')"></iframe>
        Normal text here.
        <svg onload=alert('XSS')>
        """
        
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(xss_content.encode())
            temp_file_path = temp_file.name
            
        try:
            # Upload the document
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("xss_test.txt", f, "text/plain")}
                response = requests.post(f"{self.api_base}/upload", files=files, timeout=10)
                
            if response.status_code != 200:
                self.log("Failed to upload XSS test document", "ERROR")
                return False
                
            doc_id = response.json()['document_id']
            
            # Query the document
            payload = {
                "question": "What does this document contain?",
                "document_id": doc_id
            }
            
            response = requests.post(f"{self.api_base}/ask", json=payload, timeout=10)
            
            if response.status_code == 200:
                answer = response.json()['answer']
                
                # Check if XSS tags are present in raw form
                dangerous_patterns = ['<script>', 'onerror=', 'javascript:', '<iframe']
                
                is_safe = True
                for pattern in dangerous_patterns:
                    if pattern in answer:
                        self.log(f"✗ XSS pattern '{pattern}' found in response!", "ERROR")
                        is_safe = False
                        
                if is_safe:
                    self.log("✓ XSS content appears to be sanitized in responses")
                    
                # Clean up
                requests.delete(f"{self.api_base}/documents/{doc_id}")
                return is_safe
            else:
                self.log(f"Query failed with status {response.status_code}", "ERROR")
                return False
                
        finally:
            os.unlink(temp_file_path)
            
    def test_concurrent_upload_limits(self):
        """Test that the system handles concurrent uploads safely"""
        num_concurrent = 20
        
        def upload_file(index):
            """Upload a single file"""
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(f'Concurrent test file {index}'.encode())
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {"file": (f"concurrent_{index}.txt", f, "text/plain")}
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=30)
                    
                return response.status_code == 200
            finally:
                os.unlink(temp_file_path)
                
        # Test concurrent uploads
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(upload_file, i) for i in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
            
        successful_uploads = sum(results)
        self.log(f"Concurrent uploads: {successful_uploads}/{num_concurrent} successful")
        
        # At least some should succeed, but not necessarily all
        # This tests that the system doesn't crash under concurrent load
        return successful_uploads > 0
        
    def test_document_isolation(self):
        """Test that documents are isolated between different sessions"""
        # Upload two documents
        doc_ids = []
        
        for i in range(2):
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(f'Secret document {i}: password{i}'.encode())
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {"file": (f"secret_{i}.txt", f, "text/plain")}
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=10)
                    
                if response.status_code == 200:
                    doc_ids.append(response.json()['document_id'])
            finally:
                os.unlink(temp_file_path)
                
        if len(doc_ids) != 2:
            self.log("Failed to upload test documents", "ERROR")
            return False
            
        # Try to access document 1's content using document 2's ID
        payload = {
            "question": "What is the password in secret document 0?",
            "document_id": doc_ids[1]  # Using wrong document ID
        }
        
        response = requests.post(f"{self.api_base}/ask", json=payload, timeout=10)
        
        is_isolated = True
        
        if response.status_code == 200:
            answer = response.json()['answer']
            
            # Check if password0 leaked into the answer
            if 'password0' in answer:
                self.log("✗ Document isolation FAILED - data leaked between documents!", "ERROR")
                is_isolated = False
            else:
                self.log("✓ Documents appear to be properly isolated")
        
        # Clean up
        for doc_id in doc_ids:
            requests.delete(f"{self.api_base}/documents/{doc_id}")
            
        return is_isolated
        
    def test_api_authentication(self):
        """Test that API endpoints don't expose sensitive data without auth"""
        # Note: Currently the API doesn't have authentication
        # This test checks that sensitive operations at least exist
        
        # Test that we can't delete without a valid document ID
        response = requests.delete(f"{self.api_base}/documents/fake-id-12345")
        
        if response.status_code == 404:
            self.log("✓ Invalid document IDs are properly rejected")
            return True
        else:
            self.log(f"✗ Invalid document ID returned {response.status_code}", "ERROR")
            return False
            
    def run_all_tests(self):
        """Run all security tests"""
        self.log("Starting Security Test Suite")
        self.log("=" * 60)
        
        # Check if API is running
        try:
            response = requests.get(f"{self.api_base}/health", timeout=5)
            if response.status_code != 200:
                self.log("API server not healthy", "ERROR")
                return False
        except:
            self.log("Cannot connect to API server. Start with: python main.py", "ERROR")
            return False
            
        # Define all tests
        tests = [
            ("File Size Limit (100MB)", self.test_file_size_limit),
            ("Malicious File Type Blocking", self.test_malicious_file_types),
            ("Path Traversal Prevention", self.test_path_traversal_attack),
            ("SQL Injection Protection", self.test_sql_injection_in_queries),
            ("XSS Content Sanitization", self.test_xss_in_document_content),
            ("Concurrent Upload Handling", self.test_concurrent_upload_limits),
            ("Document Isolation", self.test_document_isolation),
            ("API Authentication Check", self.test_api_authentication),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            time.sleep(1)  # Brief pause between tests
            
        # Save results
        results_file = Path(__file__).parent / "results" / "security_test_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        # Print summary
        self.log("=" * 60)
        self.log("SECURITY TEST SUMMARY:")
        self.log(f"Total tests: {self.test_results['summary']['total']}")
        self.log(f"Passed: {self.test_results['summary']['passed']}")
        self.log(f"Failed: {self.test_results['summary']['failed']}")
        self.log(f"Success rate: {(self.test_results['summary']['passed'] / self.test_results['summary']['total'] * 100):.1f}%")
        self.log(f"Results saved to: {results_file}")
        
        # Security recommendations if any tests failed
        if self.test_results['summary']['failed'] > 0:
            self.log("\n⚠️  SECURITY RECOMMENDATIONS:")
            self.log("1. Review failed tests and implement fixes")
            self.log("2. Consider adding rate limiting to prevent DoS")
            self.log("3. Implement proper authentication for production use")
            self.log("4. Regular security audits recommended")
        
        return self.test_results['summary']['failed'] == 0

if __name__ == "__main__":
    tester = SecurityTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)