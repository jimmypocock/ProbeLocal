import time
import psutil
import ollama
from src.config import Config
from src.document_processor import DocumentProcessor
from src.qa_chain import QAChain

def test_performance():
    print("🧪 Testing M3 MacBook Air Performance")

    # System info
    memory = psutil.virtual_memory()
    print(f"Total Memory: {memory.total / (1024**3):.1f} GB")
    print(f"Available Memory: {memory.available / (1024**3):.1f} GB")

    # Test model loading times
    models = ["phi", "mistral", "neural-chat"]

    for model in models:
        print(f"\nTesting {model}...")
        start = time.time()

        try:
            # Pull if not exists
            ollama.pull(model)

            # Test generation
            response = ollama.generate(
                model=model,
                prompt="What is machine learning?",
                options={"num_predict": 50}
            )

            elapsed = time.time() - start
            tokens = len(response['response'].split())
            tps = tokens / elapsed

            print(f"  Time: {elapsed:.2f}s")
            print(f"  Tokens/sec: {tps:.1f}")
            print(f"  Memory used: {psutil.Process().memory_info().rss / (1024**3):.1f} GB")

        except Exception as e:
            print(f"  Error: {e}")

    print("\n✅ Performance test complete!")

if __name__ == "__main__":
      test_performance()