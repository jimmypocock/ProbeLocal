#!/usr/bin/env python3
"""
Model Compatibility Testing Framework for Greg

This script tests different models with various content types to ensure compatibility
and identify model-specific parameter requirements.
"""

import os
import sys
import json
import time
import requests
from typing import Dict, List, Optional, Tuple
import subprocess
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from langchain_community.llms import Ollama
import ollama as ollama_module

class ModelTester:
    def __init__(self):
        self.config = Config()
        self.test_results = []
        self.models_to_test = []
        
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            models = ollama_module.list()
            return [model['name'] for model in models['models']]
        except Exception as e:
            print(f"Error getting models: {e}")
            return []
    
    def test_model_basic(self, model_name: str) -> Tuple[bool, str]:
        """Test basic model functionality"""
        try:
            # Test with minimal parameters first, but with proper timeout
            llm = Ollama(model=model_name, timeout=120)  # 2 minute timeout for first call
            response = llm.invoke("Hello, can you respond?")
            return True, "Basic test passed"
        except Exception as e:
            return False, f"Basic test failed: {str(e)}"
    
    def test_model_with_parameters(self, model_name: str) -> Dict[str, any]:
        """Test model with different parameter combinations"""
        results = {
            "model": model_name,
            "tests": []
        }
        
        # Parameter combinations to test
        param_sets = [
            {"name": "minimal", "params": {}},
            {"name": "with_context", "params": {"num_ctx": 2048}},
            {"name": "with_threads", "params": {"num_ctx": 2048, "num_thread": 8}},
            {"name": "with_penalty", "params": {"num_ctx": 2048, "repeat_penalty": 1.1}},
            {"name": "with_stop_tokens", "params": {"num_ctx": 2048, "stop": ["Human:", "Question:"]}},
            {"name": "full_params", "params": {
                "num_ctx": 2048,
                "num_thread": 8,
                "repeat_penalty": 1.1,
                "stop": ["Human:", "Question:"]
            }},
            {"name": "small_context", "params": {"num_ctx": 1024}},
            {"name": "large_context", "params": {"num_ctx": 4096}},
        ]
        
        for param_set in param_sets:
            try:
                # Add timeout to parameters
                params_with_timeout = {**param_set["params"], "timeout": 60}
                llm = Ollama(model=model_name, **params_with_timeout)
                response = llm.invoke("What is 2+2?")
                results["tests"].append({
                    "test": param_set["name"],
                    "params": param_set["params"],
                    "success": True,
                    "error": None,
                    "response_length": len(str(response))
                })
            except Exception as e:
                error_msg = str(e)
                # Check if it's a 422 error
                if "422" in error_msg:
                    error_msg = f"422 Unprocessable Entity - Parameters incompatible: {error_msg}"
                
                results["tests"].append({
                    "test": param_set["name"],
                    "params": param_set["params"],
                    "success": False,
                    "error": error_msg,
                    "response_length": 0
                })
        
        return results
    
    def test_model_with_content_types(self, model_name: str) -> Dict[str, any]:
        """Test model with different content types"""
        # Find working parameters first
        working_params = {}
        for test in self.test_results[-1]["tests"]:
            if test["success"]:
                working_params = test["params"]
                break
        
        content_tests = {
            "model": model_name,
            "content_type_tests": []
        }
        
        test_contents = [
            {"type": "simple_question", "content": "What is the capital of France?"},
            {"type": "math", "content": "Calculate 15 * 23 + 47"},
            {"type": "code", "content": "Explain this Python code: def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"},
            {"type": "long_context", "content": "Summarize this: " + ("Lorem ipsum dolor sit amet. " * 100)},
            {"type": "json", "content": "Parse this JSON and explain what it represents: {\"users\": [{\"id\": 1, \"name\": \"John\"}]}"},
            {"type": "technical", "content": "Explain the difference between TCP and UDP protocols."},
        ]
        
        for test_content in test_contents:
            try:
                # Add timeout to working parameters
                params_with_timeout = {**working_params, "timeout": 60}
                llm = Ollama(model=model_name, **params_with_timeout)
                start_time = time.time()
                response = llm.invoke(test_content["content"])
                end_time = time.time()
                
                content_tests["content_type_tests"].append({
                    "type": test_content["type"],
                    "success": True,
                    "response_time": round(end_time - start_time, 2),
                    "response_length": len(str(response)),
                    "error": None
                })
            except Exception as e:
                content_tests["content_type_tests"].append({
                    "type": test_content["type"],
                    "success": False,
                    "response_time": 0,
                    "response_length": 0,
                    "error": str(e)
                })
        
        return content_tests
    
    def generate_model_config(self) -> Dict[str, any]:
        """Generate model-specific configuration based on test results"""
        model_configs = {}
        
        for result in self.test_results:
            model_name = result["model"]
            working_params = None
            
            # Find the best working parameter set
            for test in result["tests"]:
                if test["success"]:
                    if test["test"] == "full_params":
                        working_params = test["params"]
                        break
                    elif not working_params:
                        working_params = test["params"]
            
            if working_params:
                model_configs[model_name] = {
                    "supported": True,
                    "parameters": working_params,
                    "notes": []
                }
                
                # Add notes about failures
                for test in result["tests"]:
                    if not test["success"] and "422" in str(test["error"]):
                        model_configs[model_name]["notes"].append(
                            f"Incompatible with {test['test']}: {test['params']}"
                        )
            else:
                model_configs[model_name] = {
                    "supported": False,
                    "parameters": {},
                    "notes": ["No working parameter combination found"]
                }
        
        return model_configs
    
    def run_tests(self, models: Optional[List[str]] = None):
        """Run tests on specified models or all available models"""
        if not models:
            models = self.get_available_models()
        
        if not models:
            print("No models found. Please ensure Ollama is running with models installed.")
            return
        
        print(f"Found {len(models)} models to test: {', '.join(models)}")
        print("-" * 80)
        
        for model in models:
            print(f"\n🧪 Testing model: {model}")
            
            # Warm up the model first
            print(f"  🔥 Warming up model...")
            try:
                warmup_llm = Ollama(model=model, timeout=120)
                warmup_start = time.time()
                warmup_llm.invoke("Hi")
                warmup_time = time.time() - warmup_start
                print(f"  ✅ Warmup completed in {warmup_time:.2f}s")
            except Exception as e:
                print(f"  ❌ Warmup failed: {str(e)}")
                continue

            # Basic test
            success, message = self.test_model_basic(model)
            print(f"  ✓ Basic test: {'✅ Passed' if success else '❌ Failed'} - {message}")
            
            if success:
                # Parameter tests
                print(f"  🔧 Testing parameter combinations...")
                param_results = self.test_model_with_parameters(model)
                self.test_results.append(param_results)
                
                # Show summary
                successful_tests = sum(1 for test in param_results["tests"] if test["success"])
                total_tests = len(param_results["tests"])
                print(f"  📊 Parameter tests: {successful_tests}/{total_tests} passed")
                
                # Show failures
                for test in param_results["tests"]:
                    if not test["success"]:
                        print(f"    ❌ {test['test']}: {test['error'][:100]}...")
                
                # Content type tests
                if successful_tests > 0:
                    print(f"  📝 Testing content types...")
                    content_results = self.test_model_with_content_types(model)
                    
                    successful_content = sum(1 for test in content_results["content_type_tests"] if test["success"])
                    total_content = len(content_results["content_type_tests"])
                    print(f"  📊 Content tests: {successful_content}/{total_content} passed")
        
        # Generate and save configuration
        print("\n" + "=" * 80)
        print("📋 Generating model configuration...")
        model_config = self.generate_model_config()
        
        # Save results to test output directory
        output_dir = "tests/results"
        os.makedirs(output_dir, exist_ok=True)
        results_path = os.path.join(output_dir, "model_test_results.json")
        
        with open(results_path, "w") as f:
            json.dump({
                "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "test_results": self.test_results,
                "model_configurations": model_config
            }, f, indent=2)
        
        print(f"✅ Test results saved to {results_path}")
        
        # Save recommended configuration
        self.save_model_config(model_config)
    
    def save_model_config(self, model_config: Dict[str, any]):
        """Save model-specific configuration file"""
        config_content = {
            "model_parameters": {},
            "unsupported_models": []
        }
        
        for model, config in model_config.items():
            if config["supported"]:
                config_content["model_parameters"][model] = config["parameters"]
            else:
                config_content["unsupported_models"].append(model)
        
        # Save to test results directory instead of modifying source files
        output_dir = "tests/results"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "tested_model_config.json")

        with open(output_path, "w") as f:
            json.dump(config_content, f, indent=2)
        
        print(f"✅ Model configuration saved to {output_path}")
        print("⚠️  Note: This test output does not modify src/model_config.json")
        
        # Print summary
        print("\n📊 Summary:")
        print(f"  - Supported models: {len(config_content['model_parameters'])}")
        print(f"  - Unsupported models: {len(config_content['unsupported_models'])}")
        
        if config_content["unsupported_models"]:
            print(f"  - Unsupported: {', '.join(config_content['unsupported_models'])}")

def main():
    """Main function to run model tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Ollama models for Greg compatibility")
    parser.add_argument("--models", nargs="+", help="Specific models to test (default: all)")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    
    args = parser.parse_args()
    
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code != 200:
            print("❌ Ollama is not running. Please start it with: ollama serve")
            sys.exit(1)
    except:
        print("❌ Cannot connect to Ollama. Please start it with: ollama serve")
        sys.exit(1)
    
    tester = ModelTester()
    tester.run_tests(models=args.models)

if __name__ == "__main__":
    main()