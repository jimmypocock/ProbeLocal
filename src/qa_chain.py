from typing import List, Dict, Any
import time
import json
import os
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import Ollama as LangchainOllama

from src.config import Config
from src.local_llm import OptimizedLLM
from src.document_processor import DocumentProcessor

class QAChain:
    def __init__(self):
        self.config = Config()
        self.doc_processor = DocumentProcessor()
        self.llm_system = OptimizedLLM(self.config)
        self.llm = self.llm_system.get_llm()
        self.prompt_template = self._create_prompt_template()
        self.model_config = self._load_model_config()

    def _load_model_config(self) -> Dict:
        """Load model-specific configuration"""
        config_path = os.path.join(os.path.dirname(__file__), "model_config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Warning: Could not load model config: {e}")
        
        return {"model_parameters": {}, "unsupported_models": []}

    def _get_model_parameters(self, model_name: str) -> Dict:
        """Get model-specific parameters"""
        # Check if model is in unsupported list
        if model_name in self.model_config.get("unsupported_models", []):
            raise ValueError(f"Model {model_name} is not supported. Please use a different model.")
        
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
        return {
            "num_ctx": self.config.MAX_CONTEXT_LENGTH,
            "num_thread": self.config.NUM_THREADS,
            "repeat_penalty": 1.1,
            "stop": ["Human:", "Question:"]
        }

    def _create_prompt_template(self) -> PromptTemplate:
        """Optimized prompt for local models"""
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

        return PromptTemplate(
            template=template,
            input_variables=["context", "question"]
        )

    def answer_question(
        self,
        question: str,
        document_id: str,
        max_results: int = 5,
        stream: bool = False,
        model_name: str = None,
        temperature: float = None
    ) -> Dict[str, Any]:
        """Answer with optional streaming and model-specific configuration"""
        start_time = time.time()
        
        # Validate document exists first (this will raise ValueError if not found)
        vector_store = self.doc_processor.load_vector_store(document_id)
        
        # Use specified model or default
        if model_name and model_name != self.config.LOCAL_LLM_MODEL:
            try:
                # Get model-specific parameters
                model_params = self._get_model_parameters(model_name)
                
                print(f"Creating QA chain with {model_name} using parameters: {model_params}")
                
                # Create a new LLM instance with the requested model and specific parameters
                llm = LangchainOllama(
                    model=model_name,
                    temperature=temperature if temperature is not None else self.config.TEMPERATURE,
                    top_p=self.config.TOP_P,
                    **model_params  # Use model-specific parameters
                )
            except ValueError as e:
                # Model is unsupported
                return {
                    'answer': f"Error: {str(e)}",
                    'sources': [],
                    'document_id': document_id,
                    'processing_time': 0,
                    'llm_model': model_name,
                    'error': str(e)
                }
            except Exception as e:
                # Try with minimal parameters as fallback
                print(f"Failed with full parameters, trying minimal config: {e}")
                try:
                    llm = LangchainOllama(
                        model=model_name,
                        temperature=temperature if temperature is not None else self.config.TEMPERATURE,
                        top_p=self.config.TOP_P,
                        num_ctx=1024  # Minimal context
                    )
                except Exception as e2:
                    return {
                        'answer': f"Error initializing model {model_name}: {str(e2)}",
                        'sources': [],
                        'document_id': document_id,
                        'processing_time': 0,
                        'llm_model': model_name,
                        'error': str(e2)
                    }
        else:
            # Use default model but check if custom temperature is requested
            if temperature is not None and temperature != self.config.TEMPERATURE:
                # Create new LLM instance with custom temperature
                llm = LangchainOllama(
                    model=self.config.LOCAL_LLM_MODEL,
                    temperature=temperature,
                    top_p=self.config.TOP_P,
                    num_ctx=self.config.MAX_CONTEXT_LENGTH
                )
            else:
                llm = self.llm

        try:
            # Create retriever with similarity search
            retriever = vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": max_results}
            )

            # Configure callbacks for streaming
            callbacks = [StreamingStdOutCallbackHandler()] if stream else []

            # Create QA chain with the selected LLM
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,  # Use the dynamic LLM
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True,
                chain_type_kwargs={
                    "prompt": self.prompt_template,
                    "verbose": False
                },
                callbacks=callbacks
            )

            # Get answer
            result = qa_chain({"query": question})

            # Format sources with page numbers
            sources = []
            seen_pages = set()

            for doc in result['source_documents']:
                page = doc.metadata.get('page', 'N/A')
                if page not in seen_pages:
                    sources.append({
                        'content': doc.page_content[:200] + "...",
                        'page': page,
                        'chunk_index': doc.metadata.get('chunk_index', 'N/A')
                    })
                    seen_pages.add(page)

            processing_time = time.time() - start_time

            return {
                'answer': result['result'].strip(),
                'sources': sources[:3],  # Limit to top 3 sources
                'document_id': document_id,
                'processing_time': processing_time,
                'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL
            }
            
        except ValueError as e:
            # Re-raise ValueError so it can be caught as 404 in the API
            raise e
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            
            # Check for specific error types
            if "422" in error_msg:
                error_msg = f"Model {model_name} returned 422 error. This model may require different parameters. Run 'python test_models.py --models {model_name}' to test compatibility."
            
            return {
                'answer': f"Error processing question: {error_msg}",
                'sources': [],
                'document_id': document_id,
                'processing_time': processing_time,
                'llm_model': model_name if model_name else self.config.LOCAL_LLM_MODEL,
                'error': error_msg
            }