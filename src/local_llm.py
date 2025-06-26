import os
import time
from typing import Dict, List, Optional
import ollama
from langchain_community.llms import Ollama as LangchainOllama
from langchain_huggingface import HuggingFaceEmbeddings
from src.config import Config
import torch

class OptimizedLLM:
    def __init__(self, config: Config):
        self.config = config
        self.setup_environment()
        self.llm = self._initialize_llm()
        self.embeddings = self._initialize_embeddings()

    def setup_environment(self):
        """Optimize for Apple Silicon"""
        # Use Metal Performance Shaders for acceleration
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

        # Set thread count for optimal performance
        torch.set_num_threads(self.config.NUM_THREADS)

        # Enable memory efficient attention
        os.environ["TRANSFORMERS_USE_ATTENTION_MASK"] = "1"

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
        model = optimal["model"]

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

        return LangchainOllama(
            model=model,
            temperature=self.config.TEMPERATURE,
            top_p=self.config.TOP_P,
            num_ctx=self.config.MAX_CONTEXT_LENGTH,
            num_thread=self.config.NUM_THREADS,
            repeat_penalty=1.1,
            stop=["Human:", "Question:"]
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