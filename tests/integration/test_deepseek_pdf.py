#!/usr/bin/env python3
"""
Test deepseek models specifically in PDF processing context
This simulates the actual usage scenario where 422 errors might occur
"""

import sys
import os
import json
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.config import Config
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

def test_deepseek_with_pdf_context():
    """Test deepseek with a prompt similar to PDF Q&A"""
    
    # The actual prompt template used in qa_chain.py
    template = """You are analyzing a document. When asked about numbers, amounts, or totals, 
look for EXACT values in the context. Do not calculate or estimate - only report what is explicitly written.

For invoices: Look for labels like "Total:", "Grand Total:", "Amount Due:", "Subtotal:", "Balance:".
For dates: Look for date formats and return them exactly as written.
For names/addresses: Return them exactly as they appear.

Context:
{context}

Question: {question}

Important: If you cannot find the exact information, say "I cannot find that specific information in the provided context."

Answer:"""

    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    # Simulate a PDF context
    pdf_context = """
    Invoice #12345
    Date: June 27, 2025
    
    Customer: John Doe
    Address: 123 Main St, Anytown, USA
    
    Items:
    - Widget A: $10.00
    - Widget B: $15.00
    - Widget C: $25.00
    
    Subtotal: $50.00
    Tax: $4.00
    Total: $54.00
    
    Thank you for your business!
    """
    
    models_to_test = [
        "deepseek-llm:7b-chat",
        "deepseek-coder:6.7b-instruct",
        "deepseek"  # Test base name too
    ]
    
    results = {}
    
    for model_name in models_to_test:
        print(f"\n{'='*60}")
        print(f"Testing {model_name} with PDF-like context")
        print(f"{'='*60}")
        
        # Test different parameter combinations
        param_sets = [
            {
                "name": "minimal",
                "params": {"num_ctx": 2048}
            },
            {
                "name": "with_threads",
                "params": {"num_ctx": 2048, "num_thread": 8}
            },
            {
                "name": "full_params",
                "params": {
                    "num_ctx": 2048,
                    "num_thread": 8,
                    "repeat_penalty": 1.1,
                    "stop": ["Human:", "Question:"]
                }
            }
        ]
        
        model_results = []
        
        for param_set in param_sets:
            try:
                print(f"\nTesting with {param_set['name']} parameters...")
                
                # Create LLM with parameters
                llm = Ollama(
                    model=model_name,
                    temperature=0.7,
                    top_p=0.9,
                    **param_set['params']
                )
                
                # Create chain
                chain = LLMChain(llm=llm, prompt=prompt)
                
                # Test with PDF-like question
                response = chain.invoke({
                    "context": pdf_context,
                    "question": "What is the total amount on this invoice?"
                })
                
                print(f"✅ Success with {param_set['name']}")
                print(f"Response: {response['text'][:100]}...")
                
                model_results.append({
                    "params": param_set['name'],
                    "success": True,
                    "error": None,
                    "response": response['text'][:200]
                })
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ Failed with {param_set['name']}: {error_msg}")
                
                # Check if it's a 422 error
                if "422" in error_msg:
                    print("⚠️  422 Unprocessable Entity Error Detected!")
                
                model_results.append({
                    "params": param_set['name'],
                    "success": False,
                    "error": error_msg,
                    "response": None
                })
        
        results[model_name] = model_results
    
    # Save results
    results_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "results")
    os.makedirs(results_dir, exist_ok=True)
    results_file = os.path.join(results_dir, "deepseek_pdf_test_results.json")
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("Summary of PDF Context Testing")
    print(f"{'='*60}")
    
    for model, model_results in results.items():
        successes = sum(1 for r in model_results if r['success'])
        total = len(model_results)
        print(f"\n{model}: {successes}/{total} tests passed")
        
        # Show which parameters failed
        for result in model_results:
            if not result['success'] and "422" in str(result['error']):
                print(f"  ⚠️  422 error with {result['params']} parameters")
    
    print(f"\nResults saved to {results_file}")

def check_installed_models():
    """Check which deepseek models are installed"""
    try:
        import ollama as ollama_module
        models = ollama_module.list()
        deepseek_models = [m['name'] for m in models['models'] if 'deepseek' in m['name'].lower()]
        
        if deepseek_models:
            print(f"Found deepseek models: {', '.join(deepseek_models)}")
            return True
        else:
            print("No deepseek models found. Available models:")
            for m in models['models']:
                print(f"  - {m['name']}")
            return False
    except Exception as e:
        print(f"Error checking models: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Deepseek Models with PDF Context\n")
    
    if not check_installed_models():
        print("\n⚠️  No deepseek models installed. Install with:")
        print("  ollama pull deepseek-llm:7b-chat")
        print("  ollama pull deepseek-coder:6.7b-instruct")
        sys.exit(1)
    
    test_deepseek_with_pdf_context()