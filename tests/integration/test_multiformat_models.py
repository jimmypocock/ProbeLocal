#!/usr/bin/env python3
"""
Multi-Format Model Testing Suite for Greg
Tests all models with Excel, Markdown, Word, and Image files
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

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.config import Config
import ollama
from tests.utils import get_model_full_name, get_available_models as get_available_models_util, parse_model_list

class MultiFormatModelTester:
    """Test all file formats across different models"""
    
    def __init__(self):
        self.config = Config()
        self.api_base = "http://localhost:8080"
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        
        # Define test files for each format
        self.test_files = {
            "excel": {
                "invoice": {
                    "file": "test_invoice.xlsx",
                    "questions": [
                        {"question": "What is the company name?", "expected_keywords": ["Digital", "Dynamics"]},
                        {"question": "What is the total amount?", "expected_keywords": ["313232", "313,232"]},
                        {"question": "Who is the invoice billed to?", "expected_keywords": ["Quantum", "Analytics"]},
                        {"question": "What is the invoice number?", "expected_keywords": ["INV-2025-006"]},
                        {"question": "What services were provided?", "expected_keywords": ["Machine Learning", "API", "Cloud"]},
                    ]
                },
                "story": {
                    "file": "test_story.xlsx", 
                    "questions": [
                        {"question": "What is the story title?", "expected_keywords": ["LAST", "EXPEDITION"]},
                        {"question": "Who is Dr. Chen?", "expected_keywords": ["Xenobiologist", "Chen"]},
                        {"question": "What did they discover?", "expected_keywords": ["crystals", "ice core"]},
                        {"question": "What happened to the team?", "expected_keywords": ["formations", "bridge"]},
                        {"question": "Where did this take place?", "expected_keywords": ["Antarctica", "Station Echo"]},
                    ]
                }
            },
            "markdown": {
                "invoice": {
                    "file": "test_invoice.md",
                    "questions": [
                        {"question": "What company sent this invoice?", "expected_keywords": ["CloudScale", "Technologies"]},
                        {"question": "What is the total due?", "expected_keywords": ["220500", "220,500"]},
                        {"question": "What services were provided?", "expected_keywords": ["Cloud", "Migration", "Training"]},
                        {"question": "When is payment due?", "expected_keywords": ["March", "2025"]},
                        {"question": "What is the invoice number?", "expected_keywords": ["INV-2025-004"]},
                    ]
                },
                "story": {
                    "file": "test_story.md",
                    "questions": [
                        {"question": "What is the story about?", "expected_keywords": ["lighthouse", "keeper"]},
                        {"question": "Who is the main character?", "expected_keywords": ["keeper", "lighthouse"]},
                        {"question": "What happens in the story?", "expected_keywords": ["storm", "sea"]},
                        {"question": "Where does it take place?", "expected_keywords": ["lighthouse", "coast"]},
                        {"question": "What is the mood?", "expected_keywords": ["solitude", "storm"]},
                    ]
                }
            },
            "word": {
                "invoice": {
                    "file": "test_invoice.docx",
                    "questions": [
                        {"question": "What is the company name?", "expected_keywords": ["TechVision", "Solutions"]},
                        {"question": "What is the total amount?", "expected_keywords": ["197448", "197,448"]},
                        {"question": "What services were provided?", "expected_keywords": ["IoT", "Sensor", "Integration"]},
                        {"question": "Who is the client?", "expected_keywords": ["Smart", "Manufacturing"]},
                        {"question": "What is the project timeline?", "expected_keywords": ["March", "2025"]},
                    ]
                },
                "story": {
                    "file": "test_story.docx",
                    "questions": [
                        {"question": "What is the story title?", "expected_keywords": ["Digital", "Echoes"]},
                        {"question": "Who is the main character?", "expected_keywords": ["Dr", "Sarah"]},
                        {"question": "What technology is involved?", "expected_keywords": ["quantum", "computer"]},
                        {"question": "What happens to the character?", "expected_keywords": ["consciousness", "trapped"]},
                        {"question": "What is the setting?", "expected_keywords": ["laboratory", "future"]},
                    ]
                }
            },
            "images": {
                "invoice": {
                    "file": "test_invoice.png",
                    "questions": [
                        {"question": "What company is on the invoice?", "expected_keywords": ["Repair", "Inc"]},
                        {"question": "What is the total amount?", "expected_keywords": ["154", "06"]},
                        {"question": "Who is the customer?", "expected_keywords": ["John", "Smith"]},
                        {"question": "What items were purchased?", "expected_keywords": ["brake", "cables", "pedal"]},
                        {"question": "What is the invoice number?", "expected_keywords": ["US-001", "us-001"]},
                    ]
                },
                "story": {
                    "file": "test_story.png", 
                    "questions": [
                        {"question": "What is the story title?", "expected_keywords": ["WHAT", "REMAINS"]},
                        {"question": "Who is the main character?", "expected_keywords": ["woman"]},
                        {"question": "What animals are mentioned?", "expected_keywords": ["raccoon", "squirrel", "crow"]},
                        {"question": "What does the woman do?", "expected_keywords": ["gathered", "buried", "graves"]},
                        {"question": "What publication is this from?", "expected_keywords": ["Sucharnochee", "Review"]},
                    ]
                },
                "content": {
                    "file": "test_content.png",
                    "questions": [
                        {"question": "What type of file is this?", "expected_keywords": ["image", "visual", "content"]},
                        {"question": "Does this contain text?", "expected_keywords": ["no", "visual", "computer vision"]},
                        {"question": "What analysis would be needed?", "expected_keywords": ["vision", "visual", "computer"]},
                        {"question": "What extraction method was used?", "expected_keywords": ["OCR", "extraction"]},
                        {"question": "What format is this image?", "expected_keywords": ["PNG", "image"]},
                    ]
                }
            }
        }

    def handle_rate_limit(self, response, operation_name="operation", max_retries=3):
        """Handle rate limit errors with exponential backoff"""
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limit hit for {operation_name}, waiting {retry_after} seconds...")
            time.sleep(retry_after + 1)  # Add 1 second buffer
            return True
        return False

    async def upload_document(self, file_path: str, model: str) -> str:
        """Upload a document and return its ID"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Determine content type based on file extension
                ext = file_path.split('.')[-1].lower()
                content_types = {
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'md': 'text/markdown',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'png': 'image/png',
                    'jpg': 'image/jpeg'
                }
                
                content_type = content_types.get(ext, 'application/octet-stream')
                
                with open(file_path, 'rb') as f:
                    files = {'file': (os.path.basename(file_path), f, content_type)}
                    response = requests.post(
                        f"{self.api_base}/upload",
                        files=files,
                        data={'model': model},
                        timeout=120  # Longer timeout for image processing
                    )
                    
                if response.status_code == 200:
                    return response.json()['document_id']
                elif self.handle_rate_limit(response, f"upload {os.path.basename(file_path)} (attempt {attempt+1})", max_retries):
                    continue  # Retry after rate limit wait
                else:
                    print(f"Upload failed: {response.status_code} - {response.text}")
                    return None
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            print(f"Upload error: {e}")
            return None

    async def ask_question(self, document_id: str, question: str, model: str) -> Tuple[bool, str, float]:
        """Ask a question and return success, answer, and response time"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                payload = {
                    "question": question,
                    "document_id": document_id,
                    "model_name": model,
                    "max_results": 5
                }
                
                response = requests.post(
                    f"{self.api_base}/ask",
                    json=payload,
                    timeout=90
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status_code == 200:
                    data = response.json()
                    return True, data['answer'], response_time
                elif self.handle_rate_limit(response, f"question (attempt {attempt+1})", max_retries):
                    continue  # Retry after rate limit wait
                else:
                    return False, f"Error {response.status_code}: {response.text}", response_time
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return False, str(e), 0
        return False, "Max retries exceeded", 0

    async def test_file_format(self, file_format: str, content_type: str, model: str) -> Dict:
        """Test a specific file format with a model"""
        test_config = self.test_files[file_format][content_type]
        file_path = self.fixtures_dir / test_config["file"]
        
        print(f"\n📄 Testing {file_format.upper()} ({content_type}): {test_config['file']}")
        
        # Upload document
        document_id = await self.upload_document(str(file_path), model)
        if not document_id:
            return {
                "format": file_format,
                "content_type": content_type,
                "file": test_config["file"],
                "success": False,
                "error": "Upload failed",
                "questions": []
            }
        
        print(f"✅ Upload successful: {document_id}")
        
        # Test questions
        results = []
        successful_questions = 0
        accurate_answers = 0
        total_time = 0
        
        for i, test_case in enumerate(test_config["questions"], 1):
            question = test_case["question"]
            expected_keywords = test_case["expected_keywords"]
            
            print(f"  [{i}/{len(test_config['questions'])}] {question}")
            
            success, answer, response_time = await self.ask_question(document_id, question, model)
            total_time += response_time
            
            if success:
                successful_questions += 1
                
                # Check accuracy
                answer_lower = answer.lower()
                keywords_found = any(
                    str(keyword).lower() in answer_lower 
                    for keyword in expected_keywords
                )
                
                if keywords_found:
                    accurate_answers += 1
                    print(f"    ✅ Accurate ({response_time:.2f}s): {answer[:60]}...")
                else:
                    print(f"    ⚠️  Inaccurate ({response_time:.2f}s): {answer[:60]}...")
                    print(f"       Expected: {expected_keywords}")
                
                results.append({
                    "question": question,
                    "answer": answer,
                    "success": True,
                    "accurate": keywords_found,
                    "response_time": response_time,
                    "expected_keywords": expected_keywords
                })
            else:
                print(f"    ❌ Failed ({response_time:.2f}s): {answer}")
                results.append({
                    "question": question,
                    "error": answer,
                    "success": False,
                    "accurate": False,
                    "response_time": response_time,
                    "expected_keywords": expected_keywords
                })
        
        return {
            "format": file_format,
            "content_type": content_type,
            "file": test_config["file"],
            "success": True,
            "questions": results,
            "metrics": {
                "total_questions": len(test_config["questions"]),
                "successful_answers": successful_questions,
                "accurate_answers": accurate_answers,
                "success_rate": successful_questions / len(test_config["questions"]) * 100,
                "accuracy_rate": accurate_answers / len(test_config["questions"]) * 100,
                "avg_response_time": total_time / len(test_config["questions"]) if test_config["questions"] else 0,
                "total_time": total_time
            }
        }

    async def test_model(self, model_name: str) -> Dict:
        """Test a model across all file formats"""
        # Convert short name to full name for API calls
        full_model_name = get_model_full_name(model_name)
        
        print(f"\n🤖 Testing Model: {model_name} ({full_model_name})")
        print(f"{'='*80}")
        
        model_results = {
            "model": model_name,
            "timestamp": datetime.now().isoformat(),
            "formats": [],
            "overall_metrics": {
                "total_files": 0,
                "successful_files": 0,
                "total_questions": 0,
                "successful_answers": 0,
                "accurate_answers": 0,
                "total_time": 0
            }
        }
        
        # Test each format
        for file_format in self.test_files:
            for content_type in self.test_files[file_format]:
                try:
                    result = await self.test_file_format(file_format, content_type, full_model_name)
                    model_results["formats"].append(result)
                    
                    # Update overall metrics
                    model_results["overall_metrics"]["total_files"] += 1
                    if result["success"]:
                        model_results["overall_metrics"]["successful_files"] += 1
                        metrics = result["metrics"]
                        model_results["overall_metrics"]["total_questions"] += metrics["total_questions"]
                        model_results["overall_metrics"]["successful_answers"] += metrics["successful_answers"]
                        model_results["overall_metrics"]["accurate_answers"] += metrics["accurate_answers"]
                        model_results["overall_metrics"]["total_time"] += metrics["total_time"]
                        
                except Exception as e:
                    print(f"❌ Error testing {file_format} {content_type}: {e}")
                    model_results["formats"].append({
                        "format": file_format,
                        "content_type": content_type,
                        "success": False,
                        "error": str(e)
                    })
        
        # Calculate overall rates
        overall = model_results["overall_metrics"]
        if overall["total_questions"] > 0:
            overall["success_rate"] = overall["successful_answers"] / overall["total_questions"] * 100
            overall["accuracy_rate"] = overall["accurate_answers"] / overall["total_questions"] * 100
            overall["avg_response_time"] = overall["total_time"] / overall["total_questions"]
        else:
            overall["success_rate"] = 0
            overall["accuracy_rate"] = 0 
            overall["avg_response_time"] = 0
        
        return model_results

async def main():
    parser = argparse.ArgumentParser(description="Test Ollama models with multiple file formats")
    parser.add_argument("--models", type=str, help="Comma-separated list of models to test")
    parser.add_argument("--formats", type=str, help="Comma-separated list of formats to test (excel,markdown,word,images)")
    parser.add_argument("--output", type=str, default="tests/results/multiformat_test_results.json", help="Output file for results")
    args = parser.parse_args()
    
    tester = MultiFormatModelTester()
    
    # Get available models
    try:
        available_models = get_available_models_util()
        if args.models:
            test_models = [m.strip() for m in args.models.split(",")]
        else:
            test_models = available_models
    except Exception as e:
        print(f"Error getting models: {e}")
        return
    
    print(f"🧪 Multi-Format Model Testing Suite")
    print(f"Testing {len(test_models)} models across 4 file formats")
    print(f"Models: {', '.join(test_models)}")
    print(f"Formats: Excel, Markdown, Word, Images")
    print(f"{'='*80}")
    
    all_results = []
    
    for model in test_models:
        try:
            result = await tester.test_model(model)
            all_results.append(result)
            
            # Print summary
            metrics = result["overall_metrics"]
            print(f"\n📊 {model} Summary:")
            print(f"   Files: {metrics['successful_files']}/{metrics['total_files']} successful")
            print(f"   Questions: {metrics['successful_answers']}/{metrics['total_questions']} answered")
            print(f"   Accuracy: {metrics['accuracy_rate']:.1f}%")
            print(f"   Avg Response: {metrics['avg_response_time']:.2f}s")
            
        except Exception as e:
            print(f"❌ Error testing {model}: {e}")
    
    # Save results
    results = {
        "test_run": {
            "timestamp": datetime.now().isoformat(),
            "total_models": len(test_models),
            "formats_tested": list(tester.test_files.keys())
        },
        "results": all_results
    }
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved to: {output_path}")
    print(f"🎉 Multi-format testing complete!")

if __name__ == "__main__":
    asyncio.run(main())