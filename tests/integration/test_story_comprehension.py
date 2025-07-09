#!/usr/bin/env python3
import asyncio
import sys
import os
import time
from pathlib import Path
from datetime import datetime
import json
from typing import List, Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ollama
import requests
from tests.utils import get_model_full_name, get_available_models, parse_model_list

# Story comprehension questions that test context understanding, inference, and meaning
STORY_QUESTIONS = [
    {
        "question": "What is the true purpose of the lighthouse beyond guiding ships, and what evidence in the story supports this?",
        "key_concepts": ["barrier", "boundary", "keeping something back", "holding something back", "threshold between worlds"],
        "inference_required": True
    },
    {
        "question": "Why are the seventeen mirrors arranged in the lamp room, and what makes their pattern unusual?",
        "key_concepts": ["impossible patterns", "bent light", "not for amplifying", "catch light impossibly", "strange arrangement"],
        "inference_required": True
    },
    {
        "question": "What is the significance of the seals' absence, and how does it relate to the lighthouse's hidden purpose?",
        "key_concepts": ["guardians", "strengthen boundary", "warning", "seventy years", "boundary weakens"],
        "inference_required": True
    },
    {
        "question": "Analyze Elena's character transformation throughout the story. How does her scientific background conflict with and ultimately reconcile with her ancestral duty?",
        "key_concepts": ["rational", "scientific", "marine biology", "crossroads", "ancestral duty", "choice", "knowledge transcends textbooks"],
        "inference_required": True
    },
    {
        "question": "What does the oath 'Let the light never falter, lest the darkness remember' truly mean in the context of the story?",
        "key_concepts": ["darkness remember", "something ancient", "crossing over", "held back", "barrier"],
        "inference_required": True
    },
    {
        "question": "Explain the symbolism of Thomas painting strange symbols on the tower's base each spring. What might this ritual represent?",
        "key_concepts": ["ritual", "protection", "renewal", "maintenance", "boundary", "tradition"],
        "inference_required": True
    },
    {
        "question": "What is the nature of the 'something ancient' mentioned in the story, and what clues does the text provide about its characteristics?",
        "key_concepts": ["ancient", "beneath waves", "turned away", "voices in the beam", "older than human", "harmonics"],
        "inference_required": True
    },
    {
        "question": "How does the story explore the theme of inherited responsibility and the burden of secret knowledge?",
        "key_concepts": ["three generations", "burden", "inherited", "family duty", "secret knowledge", "choice"],
        "inference_required": True
    },
    {
        "question": "What is the significance of the new moon in the story, and why does Thomas never leave during this time?",
        "key_concepts": ["new moon", "darkness", "boundary thin", "vulnerable time", "never leaves"],
        "inference_required": True
    },
    {
        "question": "Analyze the metaphor of the lighthouse as both 'guardian and prison.' How does this duality manifest throughout the story?",
        "key_concepts": ["guardian", "prison", "protects town", "binds keeper", "duty", "burden", "trapped"],
        "inference_required": True
    },
    {
        "question": "What role does the setting of Windmere play in the story? How does the coastal location contribute to the narrative's themes?",
        "key_concepts": ["coastal", "threshold", "boundary", "between worlds", "liminal space", "edge"],
        "inference_required": True
    },
    {
        "question": "Describe the 'price that must be paid' mentioned near the end. What sacrifices do the lighthouse keepers make?",
        "key_concepts": ["price", "sacrifice", "burden", "isolation", "forty-three years", "never leave", "bound by oath"],
        "inference_required": True
    }
]

class StoryComprehensionTester:
    """Tester for story comprehension and context understanding"""
    
    def __init__(self):
        self.api_base = "http://localhost:8080"
        self.story_pdf = "tests/fixtures/test_story.pdf"
    
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
                    'model_name': model,
                    'max_results': 5
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
        return get_available_models()
        
    async def test_story_comprehension(self, model: str) -> Dict[str, Any]:
        """Test a model's ability to understand story context and meaning"""
        # Get the full model name for API calls
        full_model_name = get_model_full_name(model)
        
        print(f"\n{'='*60}")
        print(f"Testing {model} - Story Comprehension")
        print(f"{'='*60}")
        
        # First, upload the story PDF
        try:
            doc_id = await self.upload_document(self.story_pdf, full_model_name)
            if not doc_id:
                return {
                    "model": model,
                    "status": "failed",
                    "error": "Failed to upload story document"
                }
        except Exception as e:
            return {
                "model": model,
                "status": "failed", 
                "error": f"Upload error: {str(e)}"
            }
        
        # Test each question
        results = {
            "model": model,
            "status": "success",
            "questions": [],
            "summary": {
                "total_questions": len(STORY_QUESTIONS),
                "inference_questions": sum(1 for q in STORY_QUESTIONS if q.get("inference_required", False)),
                "response_times": [],
                "comprehension_scores": []
            }
        }
        
        for i, question_data in enumerate(STORY_QUESTIONS):
            question = question_data["question"]
            print(f"\nQuestion {i+1}/{len(STORY_QUESTIONS)}: {question[:50]}...")
            
            try:
                response = await self.ask_question(doc_id, question, full_model_name)
                
                # Evaluate comprehension based on key concepts
                comprehension_score = self._evaluate_comprehension(
                    response["answer"], 
                    question_data["key_concepts"]
                )
                
                question_result = {
                    "question": question,
                    "answer": response["answer"],
                    "response_time": response["response_time"],
                    "comprehension_score": comprehension_score,
                    "inference_required": question_data.get("inference_required", False),
                    "key_concepts_found": [concept for concept in question_data["key_concepts"] 
                                          if concept.lower() in response["answer"].lower()]
                }
                
                results["questions"].append(question_result)
                results["summary"]["response_times"].append(response["response_time"])
                results["summary"]["comprehension_scores"].append(comprehension_score)
                
                print(f"✓ Comprehension score: {comprehension_score:.2f}")
                print(f"  Response time: {response['response_time']:.2f}s")
                
            except Exception as e:
                print(f"✗ Error: {str(e)}")
                question_result = {
                    "question": question,
                    "error": str(e),
                    "comprehension_score": 0
                }
                results["questions"].append(question_result)
                results["summary"]["comprehension_scores"].append(0)
        
        # Calculate summary statistics
        if results["summary"]["comprehension_scores"]:
            results["summary"]["average_comprehension"] = sum(results["summary"]["comprehension_scores"]) / len(results["summary"]["comprehension_scores"])
        else:
            results["summary"]["average_comprehension"] = 0
            
        if results["summary"]["response_times"]:
            results["summary"]["average_response_time"] = sum(results["summary"]["response_times"]) / len(results["summary"]["response_times"])
        else:
            results["summary"]["average_response_time"] = 0
        
        # Clean up
        try:
            await self.delete_document(doc_id)
        except:
            pass
            
        return results
    
    def _evaluate_comprehension(self, answer: str, key_concepts: List[str]) -> float:
        """Evaluate how well the answer demonstrates comprehension"""
        if not answer:
            return 0.0
        
        # Check for error messages
        answer_lower = answer.lower()
        if "error" in answer_lower or "404" in answer_lower or "failed" in answer_lower:
            return 0.0
            
        concepts_found = 0
        
        for concept in key_concepts:
            if concept.lower() in answer_lower:
                concepts_found += 1
                
        # Base score on concept coverage
        concept_score = concepts_found / len(key_concepts) if key_concepts else 0
        
        # Bonus for answer length (indicates detailed understanding)
        length_bonus = min(len(answer) / 1000, 0.2)  # Up to 0.2 bonus for detailed answers
        
        # Penalty for very short answers
        if len(answer) < 50:
            length_bonus = -0.2
            
        return min(1.0, max(0.0, concept_score + length_bonus))
    
    async def run_all_story_tests(self, models: List[str] = None) -> Dict[str, Any]:
        """Run story comprehension tests on all specified models"""
        if models is None:
            # Get available models - returns short names
            available_models = await self.get_available_models()
            models = available_models
        else:
            # Models were provided with full names, extract short names for display
            from tests.utils import MODEL_MAPPINGS
            short_names = []
            for model in models:
                # Find the short name for this model
                found_short = False
                for short, full in MODEL_MAPPINGS.items():
                    if model == full:
                        short_names.append(short)
                        found_short = True
                        break
                if not found_short:
                    # Not a known model, use as is
                    short_names.append(model)
            models = short_names
            
        all_results = {
            "test_type": "story_comprehension",
            "story_file": self.story_pdf,
            "test_date": datetime.now().isoformat(),
            "models_tested": models,
            "questions_count": len(STORY_QUESTIONS),
            "results": {}
        }
        
        for model in models:
            try:
                result = await self.test_story_comprehension(model)
                all_results["results"][model] = result
            except Exception as e:
                all_results["results"][model] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Save results
        results_dir = Path("tests/results")
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"story_comprehension_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(all_results, f, indent=2)
            
        print(f"\n{'='*60}")
        print("Story Comprehension Test Summary")
        print(f"{'='*60}")
        
        # Print summary
        for model, result in all_results["results"].items():
            if result.get("status") == "success":
                avg_comp = result["summary"]["average_comprehension"]
                avg_time = result["summary"]["average_response_time"]
                print(f"\n{model}:")
                print(f"  Average comprehension score: {avg_comp:.2f}/1.00")
                print(f"  Average response time: {avg_time:.2f}s")
            else:
                print(f"\n{model}: Failed - {result.get('error', 'Unknown error')}")
                
        print(f"\nResults saved to: {results_file}")
        return all_results


async def main():
    """Run story comprehension tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test model story comprehension')
    parser.add_argument('--models', nargs='+', help='Specific models to test')
    parser.add_argument('--story-pdf', default='tests/fixtures/test_story.pdf', help='Path to story PDF')
    
    args = parser.parse_args()
    
    # Check if story PDF exists
    if not Path(args.story_pdf).exists():
        print(f"Error: Story PDF not found at {args.story_pdf}")
        print("\nPlease convert the story text file to PDF first:")
        print("  - Text file is at: tests/test_story.txt")
        print("  - Save PDF as: tests/fixtures/test_story.pdf")
        sys.exit(1)
    
    tester = StoryComprehensionTester()
    tester.story_pdf = args.story_pdf
    
    # Parse model list - this converts short names to full names if needed
    models = parse_model_list(args.models) if args.models else None
    
    await tester.run_all_story_tests(models)


if __name__ == "__main__":
    asyncio.run(main())