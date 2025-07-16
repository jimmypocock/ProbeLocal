"""
Context management utilities for better LLM performance
"""
from typing import List, Dict, Any, Tuple
from langchain_core.documents import Document

# Optional tiktoken import
try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class ContextManager:
    """Manages context size and provides warnings/optimizations"""
    
    def __init__(self, model_name: str = "mistral"):
        self.model_name = model_name
        # Updated 2024-2025 Ollama model limits (conservative estimates for stability)
        self.model_limits = {
            "mistral": 32768,      # Mistral Small 3.1 supports 128K, using 32K for stability
            "llama3": 32768,       # Llama 3.x supports 128K, using 32K for stability  
            "llama3.1": 65536,     # More aggressive for newer models
            "llama3.2": 65536,
            "llama3.3": 65536,
            "deepseek": 32768,     # DeepSeek-R1 supports 128K, using 32K for stability
            "phi": 8192,          # Phi-4 supports more than 2K
            "gradient": 131072     # Llama3-gradient supports 1M+, using 128K
        }
        
        # Try to get tiktoken encoder, fallback to simple estimation
        if HAS_TIKTOKEN:
            try:
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except:
                self.encoder = None
        else:
            self.encoder = None
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        if self.encoder:
            return len(self.encoder.encode(text))
        else:
            # Rough estimation: ~4 characters per token
            return len(text) // 4
    
    def get_model_limit(self, model_name: str = None) -> int:
        """Get token limit for model"""
        model = model_name or self.model_name
        base_model = model.split(":")[0].lower()
        return self.model_limits.get(base_model, 2048)
    
    def analyze_context_load(
        self, 
        documents: List[Document], 
        question: str, 
        prompt_template: str,
        model_name: str = None
    ) -> Dict[str, Any]:
        """Analyze if context will fit in model limits"""
        
        # Estimate tokens for each component
        question_tokens = self.estimate_tokens(question)
        
        # Estimate context tokens
        context_text = "\n\n".join([doc.page_content for doc in documents])
        context_tokens = self.estimate_tokens(context_text)
        
        # Estimate prompt overhead (template + formatting)
        prompt_overhead = self.estimate_tokens(prompt_template) + 100  # Buffer
        
        total_tokens = question_tokens + context_tokens + prompt_overhead
        
        # Reserve space for response (25% of model limit)
        model_limit = self.get_model_limit(model_name)
        usable_limit = int(model_limit * 0.75)
        
        return {
            "total_tokens": total_tokens,
            "context_tokens": context_tokens,
            "question_tokens": question_tokens,
            "prompt_overhead": prompt_overhead,
            "model_limit": model_limit,
            "usable_limit": usable_limit,
            "will_fit": total_tokens <= usable_limit,
            "utilization_percent": (total_tokens / usable_limit) * 100,
            "documents_count": len(documents),
            "recommended_max_docs": self._recommend_max_docs(usable_limit, prompt_overhead, question_tokens)
        }
    
    def _recommend_max_docs(self, usable_limit: int, prompt_overhead: int, question_tokens: int) -> int:
        """Recommend maximum number of document chunks"""
        available_for_context = usable_limit - prompt_overhead - question_tokens
        # Assume average 200 tokens per chunk
        avg_tokens_per_chunk = 200
        return max(1, available_for_context // avg_tokens_per_chunk)
    
    def optimize_document_selection(
        self, 
        documents: List[Document], 
        question: str,
        prompt_template: str,
        model_name: str = None,
        max_chunks: int = None
    ) -> Tuple[List[Document], Dict[str, Any]]:
        """Select optimal number of documents to fit context"""
        
        if not documents:
            return documents, {"error": "No documents provided"}
        
        # If max_chunks not specified, calculate optimal
        if max_chunks is None:
            analysis = self.analyze_context_load(documents[:1], question, prompt_template, model_name)
            max_chunks = analysis["recommended_max_docs"]
        
        # Try different numbers of documents
        for num_docs in range(min(len(documents), max_chunks), 0, -1):
            selected_docs = documents[:num_docs]
            analysis = self.analyze_context_load(selected_docs, question, prompt_template, model_name)
            
            if analysis["will_fit"]:
                return selected_docs, analysis
        
        # If nothing fits, return single document
        return documents[:1], self.analyze_context_load(documents[:1], question, prompt_template, model_name)
    
    def get_user_warning(self, analysis: Dict[str, Any]) -> str:
        """Generate user-friendly warning message"""
        if analysis["will_fit"]:
            return None
        
        utilization = analysis["utilization_percent"]
        recommended = analysis["recommended_max_docs"]
        current = analysis["documents_count"]
        
        return f"""
⚠️ **Context Too Large** ({utilization:.0f}% of model capacity)

**Current:** {current} document chunks ({analysis['total_tokens']} tokens)
**Model Limit:** {analysis['model_limit']} tokens
**Recommended:** Use {recommended} or fewer document chunks

**Suggestions:**
- Try a more specific question
- Use advanced settings to reduce "Context Sources"
- Switch to a model with larger context (like llama3)
"""