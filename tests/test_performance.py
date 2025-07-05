#!/usr/bin/env python3
"""
Performance Test Suite for Greg AI Playground
Tests load handling, memory usage, response times, and scalability
"""

import os
import sys
import time
import json
import psutil
import requests
import tempfile
import statistics
import concurrent.futures
from pathlib import Path
from datetime import datetime
import threading
import queue

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class PerformanceTester:
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
        self.uploaded_docs = []  # Track for cleanup
        
    def log(self, message, level="INFO"):
        """Log with timestamp"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {level}: {message}")
        
    def get_memory_usage(self):
        """Get current memory usage of the API process"""
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                if 'python' in proc.info['name'].lower() and 'main.py' in ' '.join(proc.cmdline()):
                    return proc.info['memory_info'].rss / (1024 * 1024)  # MB
            except:
                pass
        return 0
        
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
        
    def test_response_time_benchmark(self):
        """Test average response times for different operations"""
        benchmarks = {
            "health_check": {"times": [], "threshold": 0.1},  # 100ms
            "document_list": {"times": [], "threshold": 0.5},  # 500ms
            "small_upload": {"times": [], "threshold": 5.0},  # 5s
            "query": {"times": [], "threshold": 10.0}  # 10s
        }
        
        # Health check benchmark
        for _ in range(10):
            start = time.time()
            response = requests.get(f"{self.api_base}/health", timeout=5)
            benchmarks["health_check"]["times"].append(time.time() - start)
            
        # Document list benchmark
        for _ in range(10):
            start = time.time()
            response = requests.get(f"{self.api_base}/documents", timeout=5)
            benchmarks["document_list"]["times"].append(time.time() - start)
            
        # Small upload benchmark
        for i in range(3):
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(f'Small test document {i}\n'.encode() * 100)
                temp_file_path = temp_file.name
                
            with open(temp_file_path, 'rb') as f:
                files = {"file": (f"bench_{i}.txt", f, "text/plain")}
                start = time.time()
                response = requests.post(f"{self.api_base}/upload", files=files, timeout=30)
                benchmarks["small_upload"]["times"].append(time.time() - start)
                
                if response.status_code == 200:
                    self.uploaded_docs.append(response.json()['document_id'])
                    
            os.unlink(temp_file_path)
            
        # Query benchmark
        if self.uploaded_docs:
            for _ in range(5):
                payload = {
                    "question": "What is this document about?",
                    "document_id": self.uploaded_docs[0]
                }
                start = time.time()
                response = requests.post(f"{self.api_base}/ask", json=payload, timeout=30)
                benchmarks["query"]["times"].append(time.time() - start)
                
        # Analyze results
        all_pass = True
        for operation, data in benchmarks.items():
            if data["times"]:
                avg_time = statistics.mean(data["times"])
                max_time = max(data["times"])
                
                self.log(f"{operation}: avg={avg_time:.3f}s, max={max_time:.3f}s, threshold={data['threshold']}s")
                
                if avg_time > data["threshold"]:
                    self.log(f"✗ {operation} exceeds threshold!", "ERROR")
                    all_pass = False
                    
        return all_pass
        
    def test_concurrent_users(self):
        """Test system behavior with multiple concurrent users"""
        num_users = 10
        operations_per_user = 5
        
        def simulate_user(user_id):
            """Simulate a user performing operations"""
            results = []
            
            # Upload a document
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(f'User {user_id} document\n'.encode() * 500)
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {"file": (f"user_{user_id}.txt", f, "text/plain")}
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=30)
                    
                if response.status_code == 200:
                    doc_id = response.json()['document_id']
                    results.append(("upload", True))
                    
                    # Perform queries
                    for i in range(operations_per_user):
                        payload = {
                            "question": f"What is question {i} about this document?",
                            "document_id": doc_id
                        }
                        response = requests.post(f"{self.api_base}/ask", json=payload, timeout=30)
                        results.append(("query", response.status_code == 200))
                        
                    # Clean up
                    requests.delete(f"{self.api_base}/documents/{doc_id}")
                else:
                    results.append(("upload", False))
                    
            finally:
                os.unlink(temp_file_path)
                
            return results
            
        # Run concurrent users
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(simulate_user, i) for i in range(num_users)]
            all_results = []
            for future in concurrent.futures.as_completed(futures):
                all_results.extend(future.result())
                
        duration = time.time() - start_time
        
        # Analyze results
        total_ops = len(all_results)
        successful_ops = sum(1 for _, success in all_results if success)
        success_rate = (successful_ops / total_ops) * 100
        
        self.log(f"Concurrent users test: {successful_ops}/{total_ops} operations succeeded ({success_rate:.1f}%)")
        self.log(f"Total time: {duration:.2f}s, Ops/sec: {total_ops/duration:.1f}")
        
        # Success if at least 90% of operations succeed
        return success_rate >= 90
        
    def test_memory_usage_under_load(self):
        """Test memory usage doesn't grow excessively under load"""
        initial_memory = self.get_memory_usage()
        self.log(f"Initial memory usage: {initial_memory:.1f}MB")
        
        # Upload several documents
        for i in range(5):
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                # Create a 5MB document
                temp_file.write(b'X' * 5 * 1024 * 1024)
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {"file": (f"mem_test_{i}.txt", f, "text/plain")}
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=60)
                    
                if response.status_code == 200:
                    self.uploaded_docs.append(response.json()['document_id'])
                    
            finally:
                os.unlink(temp_file_path)
                
            current_memory = self.get_memory_usage()
            self.log(f"Memory after upload {i+1}: {current_memory:.1f}MB")
            
        # Perform many queries
        for _ in range(20):
            if self.uploaded_docs:
                payload = {
                    "question": "What is in this document?",
                    "document_id": self.uploaded_docs[0]
                }
                requests.post(f"{self.api_base}/ask", json=payload, timeout=30)
                
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        self.log(f"Final memory usage: {final_memory:.1f}MB")
        self.log(f"Memory increase: {memory_increase:.1f}MB")
        
        # Check if memory increase is reasonable (less than 500MB)
        return memory_increase < 500
        
    def test_large_document_handling(self):
        """Test handling of large documents"""
        # Create a 50MB document (under the 100MB limit)
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            # Write realistic content, not just repeated characters
            for i in range(50 * 1024):  # 50k iterations of 1KB each
                temp_file.write(f'Line {i}: This is a test sentence with some variety. ' * 20)
                temp_file.write(b'\n')
            temp_file_path = temp_file.name
            
        file_size_mb = os.path.getsize(temp_file_path) / (1024 * 1024)
        self.log(f"Created test file: {file_size_mb:.1f}MB")
        
        try:
            # Test upload
            start_time = time.time()
            with open(temp_file_path, 'rb') as f:
                files = {"file": ("large_doc.txt", f, "text/plain")}
                response = requests.post(f"{self.api_base}/upload", files=files, timeout=300)
                
            upload_time = time.time() - start_time
            
            if response.status_code == 200:
                doc_id = response.json()['document_id']
                chunks = response.json()['chunks']
                self.uploaded_docs.append(doc_id)
                
                self.log(f"Upload successful: {upload_time:.1f}s, {chunks} chunks")
                
                # Test query on large document
                start_time = time.time()
                payload = {
                    "question": "What is the main topic of this document?",
                    "document_id": doc_id
                }
                response = requests.post(f"{self.api_base}/ask", json=payload, timeout=60)
                query_time = time.time() - start_time
                
                if response.status_code == 200:
                    self.log(f"Query successful: {query_time:.1f}s")
                    
                    # Success if both operations complete in reasonable time
                    return upload_time < 60 and query_time < 30
                else:
                    self.log(f"Query failed: {response.status_code}", "ERROR")
                    return False
            else:
                self.log(f"Upload failed: {response.status_code}", "ERROR")
                return False
                
        finally:
            os.unlink(temp_file_path)
            
    def test_rate_limiting(self):
        """Test that rate limiting is properly enforced"""
        # Test upload rate limit (10/minute)
        upload_times = []
        
        for i in range(12):  # Try to exceed the limit
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
                temp_file.write(f'Rate limit test {i}'.encode())
                temp_file_path = temp_file.name
                
            try:
                with open(temp_file_path, 'rb') as f:
                    files = {"file": (f"rate_{i}.txt", f, "text/plain")}
                    start = time.time()
                    response = requests.post(f"{self.api_base}/upload", files=files, timeout=10)
                    upload_times.append((time.time() - start, response.status_code))
                    
                    if response.status_code == 200:
                        self.uploaded_docs.append(response.json()['document_id'])
                    elif response.status_code == 429:
                        self.log(f"Rate limit hit at upload {i+1} - Good!")
                        
            finally:
                os.unlink(temp_file_path)
                
        # Check that rate limiting kicked in
        rate_limited = any(status == 429 for _, status in upload_times)
        
        if not rate_limited:
            self.log("Rate limiting not enforced for uploads!", "ERROR")
            return False
            
        # Test query rate limit (60/minute)
        if self.uploaded_docs:
            query_count = 0
            rate_limited = False
            
            # Try to make many rapid queries
            for i in range(70):
                payload = {
                    "question": f"Quick question {i}?",
                    "document_id": self.uploaded_docs[0]
                }
                response = requests.post(f"{self.api_base}/ask", json=payload, timeout=5)
                
                if response.status_code == 429:
                    self.log(f"Query rate limit hit at {i+1} - Good!")
                    rate_limited = True
                    break
                    
            if not rate_limited:
                self.log("Rate limiting might not be working for queries", "WARN")
                
        return True
        
    def test_error_recovery(self):
        """Test system recovery from various error conditions"""
        # Test recovery from invalid document ID
        payload = {
            "question": "Test question",
            "document_id": "invalid-id-12345"
        }
        response = requests.post(f"{self.api_base}/ask", json=payload, timeout=10)
        
        if response.status_code != 404:
            self.log("Invalid document ID not properly handled", "ERROR")
            return False
            
        # Test recovery from malformed request
        response = requests.post(f"{self.api_base}/ask", json={"invalid": "data"}, timeout=10)
        
        if response.status_code != 422:
            self.log("Malformed request not properly handled", "ERROR")
            return False
            
        # System should still be responsive after errors
        response = requests.get(f"{self.api_base}/health", timeout=5)
        
        return response.status_code == 200
        
    def cleanup(self):
        """Clean up uploaded documents"""
        for doc_id in self.uploaded_docs:
            try:
                requests.delete(f"{self.api_base}/documents/{doc_id}")
            except:
                pass
                
    def run_all_tests(self):
        """Run all performance tests"""
        self.log("Starting Performance Test Suite")
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
            ("Response Time Benchmarks", self.test_response_time_benchmark),
            ("Concurrent Users (10 users)", self.test_concurrent_users),
            ("Memory Usage Under Load", self.test_memory_usage_under_load),
            ("Large Document Handling (50MB)", self.test_large_document_handling),
            ("Rate Limiting Enforcement", self.test_rate_limiting),
            ("Error Recovery", self.test_error_recovery),
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            time.sleep(2)  # Brief pause between tests
            
        # Cleanup
        self.cleanup()
        
        # Save results
        results_file = Path(__file__).parent / "results" / "performance_test_results.json"
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
            
        # Print summary
        self.log("=" * 60)
        self.log("PERFORMANCE TEST SUMMARY:")
        self.log(f"Total tests: {self.test_results['summary']['total']}")
        self.log(f"Passed: {self.test_results['summary']['passed']}")
        self.log(f"Failed: {self.test_results['summary']['failed']}")
        self.log(f"Success rate: {(self.test_results['summary']['passed'] / self.test_results['summary']['total'] * 100):.1f}%")
        self.log(f"Results saved to: {results_file}")
        
        # Performance recommendations
        if self.test_results['summary']['failed'] > 0:
            self.log("\n⚠️  PERFORMANCE RECOMMENDATIONS:")
            self.log("1. Consider caching frequently accessed data")
            self.log("2. Implement connection pooling for better concurrency")
            self.log("3. Add request queuing for heavy operations")
            self.log("4. Monitor memory usage in production")
        
        return self.test_results['summary']['failed'] == 0

if __name__ == "__main__":
    tester = PerformanceTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)