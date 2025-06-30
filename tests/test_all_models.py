#!/usr/bin/env python3
"""
Comprehensive Model Testing Suite for ProbeLocal
Tests all models with actual PDF processing and Q&A
"""

import sys
import os
import json
import time
import asyncio
import argparse
from typing import Dict, List, Tuple, Any
from datetime import datetime
import requests
from pathlib import Path

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from config import Config
import ollama
from tests.utils import get_model_full_name, get_available_models as get_available_models_util, parse_model_list

class ModelTester:
    """Base class for model testing functionality"""
    def __init__(self):
        self.config = Config()
        self.api_base = "http://localhost:8080"
        
    async def upload_document(self, pdf_path: str, model: str) -> str:
        """Upload a document and return its ID"""
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
                response = requests.post(
                    f"{self.api_base}/upload",
                    files=files,
                    data={'model': model}
                )
                
            if response.status_code == 200:
                return response.json()['document_id']
            else:
                print(f"Upload failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Upload error: {e}")
            return None
    
    async def ask_question(self, doc_id: str, question: str, model: str) -> Dict:
        """Ask a question about a document"""
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.api_base}/ask",
                json={
                    'document_id': doc_id,
                    'question': question,
                    'model': model
                }
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'answer': result['answer'],
                    'response_time': response_time,
                    'status': 'success'
                }
            else:
                return {
                    'error': f"{response.status_code}: {response.text}",
                    'response_time': response_time,
                    'status': 'error'
                }
        except Exception as e:
            return {
                'error': str(e),
                'response_time': time.time() - start_time,
                'status': 'error'
            }
    
    async def delete_document(self, doc_id: str):
        """Delete a document"""
        try:
            requests.delete(f"{self.api_base}/documents/{doc_id}")
        except:
            pass
    
    async def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama"""
        try:
            models = ollama.list()
            return [model['name'].split(':')[0] for model in models['models']]
        except Exception as e:
            print(f"Error getting models: {e}")
            return []


class ComprehensiveTester(ModelTester):
    def __init__(self, pdf_path: str = None):
        super().__init__()
        self.pdf_path = pdf_path or "tests/fixtures/test_invoice.pdf"
        self.test_questions = [
            # Basic retrieval questions
            {"question": "What is the invoice number?", "expected_keywords": ["INV-2025-001"]},
            {"question": "What is the total amount due?", "expected_keywords": ["32,550", "32550"]},
            {"question": "Who is being billed?", "expected_keywords": ["Tech Startup Inc"]},
            {"question": "What is the tax rate?", "expected_keywords": ["8.5%", "8.5"]},
            
            # More complex questions
            {"question": "What services were provided in this invoice?", "expected_keywords": ["AI Model", "Data Processing", "API"]},
            {"question": "When is the payment due?", "expected_keywords": ["30 days", "thirty days"]},
            {"question": "What discount is offered for early payment?", "expected_keywords": ["2%", "2 percent", "10 days"]},
            {"question": "When is the training session scheduled?", "expected_keywords": ["July 15", "July"]},
            
            # Calculation questions (harder)
            {"question": "How much would I save with the early payment discount?", "expected_keywords": ["651", "discount"]},
            {"question": "What is the hourly rate for data processing?", "expected_keywords": ["150", "per hour", "hourly"]},
        ]
        
        self.test_results = {
            "test_date": datetime.now().isoformat(),
            "pdf_file": self.pdf_path,
            "models": {},
            "summary": {}
        }
    
    def check_services(self) -> Dict[str, bool]:
        """Check if required services are running"""
        services = {
            "ollama": False,
            "api": False,
            "models_available": False
        }
        
        # Check Ollama
        try:
            models = ollama.list()
            services["ollama"] = True
            services["models_available"] = len(models['models']) > 0
        except:
            pass
        
        # Check API
        try:
            response = requests.get(f"{self.api_base}/health", timeout=2)
            services["api"] = response.status_code == 200
        except:
            pass
        
        return services
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return get_available_models_util()
    
    def upload_pdf(self) -> Tuple[bool, str, str]:
        """Upload PDF and return success status, document_id, and message"""
        if not os.path.exists(self.pdf_path):
            return False, None, f"PDF not found: {self.pdf_path}"
        
        try:
            with open(self.pdf_path, 'rb') as f:
                files = {'file': ('test_invoice.pdf', f, 'application/pdf')}
                response = requests.post(f"{self.api_base}/upload", files=files, timeout=300)
            
            if response.status_code == 200:
                data = response.json()
                return True, data['document_id'], f"Uploaded successfully (ID: {data['document_id'][:8]}...)"
            else:
                return False, None, f"Upload failed: {response.status_code} - {response.text}"
        except Exception as e:
            return False, None, f"Upload error: {str(e)}"
    
    def test_model_qa(self, model_name: str, document_id: str) -> Dict[str, Any]:
        """Test a model with all questions"""
        # Get the full model name for API calls
        full_model_name = get_model_full_name(model_name)
        
        model_results = {
            "model": model_name,
            "document_id": document_id,
            "questions": [],
            "errors": [],
            "metrics": {
                "total_questions": len(self.test_questions),
                "successful_answers": 0,
                "accurate_answers": 0,
                "total_time": 0,
                "average_time": 0
            }
        }
        
        print(f"\n{'='*60}")
        print(f"Testing {model_name}")
        print(f"{'='*60}")
        
        for i, test_case in enumerate(self.test_questions, 1):
            question = test_case["question"]
            expected_keywords = test_case["expected_keywords"]
            
            print(f"\n[{i}/{len(self.test_questions)}] Q: {question}")
            
            try:
                start_time = time.time()
                
                # Make API request
                payload = {
                    "question": question,
                    "document_id": document_id,
                    "model_name": full_model_name,
                    "max_results": 5
                }
                
                response = requests.post(
                    f"{self.api_base}/ask",
                    json=payload,
                    timeout=60
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data['answer']
                    
                    # Check accuracy
                    answer_lower = answer.lower()
                    keywords_found = any(
                        str(keyword).lower() in answer_lower 
                        for keyword in expected_keywords
                    )
                    
                    print(f"✅ Answer: {answer[:100]}...")
                    print(f"⏱️  Time: {response_time:.2f}s")
                    if keywords_found:
                        print(f"✓ Accurate (found expected keywords)")
                    else:
                        print(f"⚠️  May be inaccurate (missing expected keywords: {expected_keywords})")
                    
                    model_results["questions"].append({
                        "question": question,
                        "answer": answer,
                        "success": True,
                        "accurate": keywords_found,
                        "response_time": response_time,
                        "expected_keywords": expected_keywords
                    })
                    
                    model_results["metrics"]["successful_answers"] += 1
                    if keywords_found:
                        model_results["metrics"]["accurate_answers"] += 1
                
                elif response.status_code == 422:
                    error_detail = response.json().get('detail', 'Unknown error')
                    print(f"❌ 422 Error: {error_detail}")
                    
                    model_results["errors"].append({
                        "question": question,
                        "error": f"422 Unprocessable Entity: {error_detail}",
                        "response_time": response_time
                    })
                    
                else:
                    error_msg = f"{response.status_code}: {response.text[:200]}"
                    print(f"❌ Error: {error_msg}")
                    
                    model_results["errors"].append({
                        "question": question,
                        "error": error_msg,
                        "response_time": response_time
                    })
                
                model_results["metrics"]["total_time"] += response_time
                
            except requests.exceptions.Timeout:
                print(f"❌ Timeout after 60s")
                model_results["errors"].append({
                    "question": question,
                    "error": "Request timeout (60s)",
                    "response_time": 60
                })
                
            except Exception as e:
                print(f"❌ Error: {str(e)}")
                model_results["errors"].append({
                    "question": question,
                    "error": str(e),
                    "response_time": 0
                })
        
        # Calculate metrics
        if model_results["metrics"]["successful_answers"] > 0:
            model_results["metrics"]["average_time"] = (
                model_results["metrics"]["total_time"] / 
                model_results["metrics"]["successful_answers"]
            )
        
        model_results["metrics"]["success_rate"] = (
            model_results["metrics"]["successful_answers"] / 
            model_results["metrics"]["total_questions"] * 100
        )
        
        model_results["metrics"]["accuracy_rate"] = (
            model_results["metrics"]["accurate_answers"] / 
            model_results["metrics"]["total_questions"] * 100
        )
        
        return model_results
    
    def run_tests(self, models: List[str] = None):
        """Run comprehensive tests on all models"""
        print("🚀 ProbeLocal Comprehensive Model Testing Suite\n")
        
        # Check services
        print("Checking services...")
        services = self.check_services()
        
        if not services["api"]:
            print("❌ API server not running. Start with: make run")
            return
        
        if not services["ollama"]:
            print("❌ Ollama not running. Start with: ollama serve")
            return
        
        # Get models
        available_models = self.get_available_models()
        if models:
            # Models were provided with full names, extract short names for display
            from tests.utils import MODEL_MAPPINGS
            test_models = []
            for model in models:
                # Find the short name for this model
                found = False
                for short, full in MODEL_MAPPINGS.items():
                    if model == full:
                        if short in available_models:
                            test_models.append(short)
                            found = True
                        break
                if not found and model in available_models:
                    # Not a known model mapping, use as is if available
                    test_models.append(model)
        else:
            test_models = available_models
        
        if not test_models:
            print("❌ No models available to test")
            return
        
        print(f"✅ Found {len(test_models)} models to test: {', '.join(test_models)}")
        
        # Upload PDF
        print(f"\n📄 Uploading PDF: {self.pdf_path}")
        success, document_id, message = self.upload_pdf()
        
        if not success:
            print(f"❌ {message}")
            return
        
        print(f"✅ {message}")
        self.test_results["document_id"] = document_id
        
        # Test each model
        for model in test_models:
            result = self.test_model_qa(model, document_id)
            self.test_results["models"][model] = result
        
        # Generate summary
        self.generate_summary()
        
        # Save results
        self.save_results()
        
        # Print summary
        self.print_summary()
    
    def generate_summary(self):
        """Generate test summary"""
        summary = {
            "total_models": len(self.test_results["models"]),
            "models_with_errors": 0,
            "models_with_422": 0,
            "best_accuracy_model": None,
            "fastest_model": None,
            "model_rankings": []
        }
        
        rankings = []
        
        for model_name, model_data in self.test_results["models"].items():
            metrics = model_data["metrics"]
            has_422 = any("422" in str(e.get("error", "")) for e in model_data["errors"])
            
            if model_data["errors"]:
                summary["models_with_errors"] += 1
            if has_422:
                summary["models_with_422"] += 1
            
            rankings.append({
                "model": model_name,
                "success_rate": metrics["success_rate"],
                "accuracy_rate": metrics["accuracy_rate"],
                "average_time": metrics["average_time"],
                "has_422": has_422,
                "error_count": len(model_data["errors"])
            })
        
        # Sort by accuracy, then by success rate
        rankings.sort(key=lambda x: (x["accuracy_rate"], x["success_rate"]), reverse=True)
        summary["model_rankings"] = rankings
        
        if rankings:
            summary["best_accuracy_model"] = rankings[0]["model"]
            
            # Find fastest model (excluding those with 0 success)
            fastest = min(
                (r for r in rankings if r["average_time"] > 0),
                key=lambda x: x["average_time"],
                default=None
            )
            if fastest:
                summary["fastest_model"] = fastest["model"]
        
        self.test_results["summary"] = summary
    
    def save_results(self):
        """Save test results to file"""
        output_path = f"tests/results/model_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_path}")
        
        # Also save a latest.json for easy access
        latest_path = "tests/results/latest.json"
        with open(latest_path, 'w') as f:
            json.dump(self.test_results, f, indent=2)
    
    def print_summary(self):
        """Print test summary"""
        summary = self.test_results["summary"]
        
        print("\n" + "="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        
        print(f"\nModels tested: {summary['total_models']}")
        print(f"Models with errors: {summary['models_with_errors']}")
        print(f"Models with 422 errors: {summary['models_with_422']}")
        
        print("\n🏆 Model Rankings (by accuracy):")
        print(f"{'Rank':<5} {'Model':<30} {'Success':<10} {'Accuracy':<10} {'Avg Time':<10} {'Status'}")
        print("-" * 75)
        
        for i, ranking in enumerate(summary["model_rankings"], 1):
            status = "⚠️ 422" if ranking["has_422"] else "✅ OK"
            if ranking["error_count"] == len(self.test_questions):
                status = "❌ FAIL"
            
            print(f"{i:<5} {ranking['model']:<30} "
                  f"{ranking['success_rate']:<10.1f}% "
                  f"{ranking['accuracy_rate']:<10.1f}% "
                  f"{ranking['average_time']:<10.2f}s "
                  f"{status}")
        
        if summary["best_accuracy_model"]:
            print(f"\n🥇 Best Accuracy: {summary['best_accuracy_model']}")
        if summary["fastest_model"]:
            print(f"⚡ Fastest Model: {summary['fastest_model']}")
        
        # Show models with 422 errors
        if summary["models_with_422"] > 0:
            print("\n⚠️  Models with 422 errors:")
            for ranking in summary["model_rankings"]:
                if ranking["has_422"]:
                    print(f"  - {ranking['model']}")
            print("\nRun 'python fix_deepseek.py' to apply fixes for these models")


def main():
    parser = argparse.ArgumentParser(description="Comprehensive model testing for ProbeLocal")
    parser.add_argument("--models", nargs="+", help="Specific models to test")
    parser.add_argument("--pdf", help="Path to PDF file to test with")
    parser.add_argument("--questions", type=int, default=None, help="Number of questions to test")
    
    args = parser.parse_args()
    
    # Use custom PDF if provided
    pdf_path = args.pdf
    if not pdf_path:
        # Check for test invoice in fixtures
        default_pdf = "tests/fixtures/test_invoice.pdf"
        if os.path.exists(default_pdf):
            pdf_path = default_pdf
        else:
            print("❌ No PDF file found. Please provide one with --pdf")
            print("   Or create one: python tests/unit/create_simple_test.py")
            sys.exit(1)
    
    tester = ComprehensiveTester(pdf_path=pdf_path)
    
    # Limit questions if requested
    if args.questions:
        tester.test_questions = tester.test_questions[:args.questions]
    
    # Parse model list - this converts short names to full names if needed
    models = parse_model_list(args.models) if args.models else None
    
    tester.run_tests(models=models)


if __name__ == "__main__":
    main()