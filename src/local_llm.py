import os
import json
import time
from typing import Dict, List, Optional
import ollama
from langchain_community.llms import Ollama as LangchainOllama
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import Config
import torch

class OptimizedLLM:
    def __init__(self, config: Config, model_name: Optional[str] = None):
        self.config = config
        self.model_name = model_name or config.LOCAL_LLM_MODEL
        self.model_config = self._load_model_config()
        self.setup_environment()
        self.llm = self._initialize_llm()
        self.embeddings = self._initialize_embeddings()

    def _load_model_config(self) -> Dict:
        """Load model-specific configuration"""
        config_path = os.path.join(os.path.dirname(__file__), "model_config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load model config: {e}")
        
        # Default configuration if file doesn't exist
        return {
            "model_parameters": {
                "default": {
                    "num_ctx": self.config.MAX_CONTEXT_LENGTH,
                    "num_thread": self.config.NUM_THREADS,
                    "repeat_penalty": 1.1,
                    "stop": ["Human:", "Question:"]
                }
            },
            "unsupported_models": []
        }

    def setup_environment(self):
        """Optimize for Apple Silicon"""
        # Use Metal Performance Shaders for acceleration
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

        # Set thread count for optimal performance
        torch.set_num_threads(self.config.NUM_THREADS)

        # Enable memory efficient attention
        os.environ["TRANSFORMERS_USE_ATTENTION_MASK"] = "1"

    def _get_model_parameters(self, model_name: str) -> Dict:
        """Get model-specific parameters"""
        # Check if model is in unsupported list
        if model_name in self.model_config.get("unsupported_models", []):
            print(f"Warning: Model {model_name} is marked as unsupported. Using minimal parameters.")
            return {}
        
        # Get model-specific parameters
        model_params = self.model_config.get("model_parameters", {})
        
        # First check for exact model match
        if model_name in model_params:
            return model_params[model_name].copy()
        
        # Check for base model match (e.g., "deepseek" for "deepseek:latest")
        base_model = model_name.split(':')[0]
        if base_model in model_params:
            return model_params[base_model].copy()
        
        # Check for partial matches
        for param_model, params in model_params.items():
            if param_model in model_name or model_name in param_model:
                print(f"Using parameters from {param_model} for {model_name}")
                return params.copy()
        
        # Use default parameters if no match found
        print(f"No specific config for {model_name}, using default parameters")
        return model_params.get("default", {
            "num_ctx": self.config.MAX_CONTEXT_LENGTH,
            "num_thread": self.config.NUM_THREADS,
            "repeat_penalty": 1.1,
            "stop": ["Human:", "Question:"]
        }).copy()

    def _initialize_llm(self):
        """Initialize Ollama with optimal settings for M3"""
        # Check if Ollama is running
        try:
            ollama.list()
        except:
            raise Exception(
                "Ollama is not running. Please run 'ollama serve' in a terminal."
            )

        # Get optimal model based on available memory
        optimal = self.config.get_optimal_settings()
        model = self.model_name or optimal["model"]

        # Check if model is available
        try:
            available_models = [m['name'] for m in ollama.list()['models']]
            if not any(model in m for m in available_models):
                # Don't automatically pull models - use default instead
                print(f"Model {model} not found. Falling back to mistral...")
                model = "mistral"
                
                # Check if mistral is available
                if not any("mistral" in m for m in available_models):
                    raise Exception(
                        f"No models found. Please run: ollama pull mistral"
                    )
        except Exception as e:
            print(f"Error checking models: {e}")
            model = self.config.LOCAL_LLM_MODEL

        # Get model-specific parameters
        model_params = self._get_model_parameters(model)
        
        # Log the parameters being used
        print(f"Initializing {model} with parameters: {model_params}")
        
        # Create LLM instance with model-specific parameters
        try:
            return LangchainOllama(
                model=model,
                temperature=self.config.TEMPERATURE,
                top_p=self.config.TOP_P,
                **model_params  # Unpack model-specific parameters
            )
        except Exception as e:
            # If initialization fails, try with minimal parameters
            print(f"Failed to initialize {model} with full parameters: {e}")
            print("Retrying with minimal parameters...")
            
            return LangchainOllama(
                model=model,
                temperature=self.config.TEMPERATURE,
                top_p=self.config.TOP_P,
                num_ctx=1024  # Minimal context
            )

    def _initialize_embeddings(self):
        """Initialize local embeddings optimized for M3"""
        # Use sentence-transformers with Apple Silicon optimization
        return HuggingFaceEmbeddings(
            model_name=self.config.EMBEDDING_MODEL,
            model_kwargs={
                'device': 'mps' if torch.backends.mps.is_available() else 'cpu'
            },
            encode_kwargs={
                'normalize_embeddings': True,
                'batch_size': self.config.BATCH_SIZE
            }
        )

    def get_llm(self):
        return self.llm

    def get_embeddings(self):
        return self.embeddings

    def test_model(self) -> bool:
        """Test if the model works with current configuration"""
        try:
            response = self.llm.invoke("Hello, please respond with 'OK'")
            return True
        except Exception as e:
            print(f"Model test failed: {e}")
            return False