#!/usr/bin/env python3
"""
List all models available for testing
"""
import ollama
import sys
from tabulate import tabulate


def get_model_size(size_bytes):
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def list_models():
    """List all available models"""
    try:
        # Get model list
        models = ollama.list()['models']
        
        if not models:
            print("❌ No models installed")
            print("\nInstall models with:")
            print("  ollama pull mistral")
            print("  ollama pull llama3")
            print("  ollama pull phi")
            return
        
        # Extract unique base models
        unique_models = {}
        for model in models:
            base_name = model['name'].split(':')[0]
            if base_name not in unique_models:
                unique_models[base_name] = {
                    'name': base_name,
                    'size': model.get('size', 0),
                    'modified': model.get('modified', 'Unknown'),
                    'full_name': model['name']
                }
        
        # Sort by name
        sorted_models = sorted(unique_models.values(), key=lambda x: x['name'])
        
        print(f"🤖 Found {len(sorted_models)} unique models available for testing:\n")
        
        # Prepare table data
        table_data = []
        for model in sorted_models:
            table_data.append([
                model['name'],
                get_model_size(model['size']),
                model['modified'].split('T')[0] if 'T' in str(model['modified']) else model['modified']
            ])
        
        # Print table
        headers = ['Model', 'Size', 'Last Modified']
        print(tabulate(table_data, headers=headers, tablefmt='simple'))
        
        print(f"\n📊 Total models: {len(sorted_models)}")
        total_size = sum(m['size'] for m in unique_models.values())
        print(f"💾 Total size: {get_model_size(total_size)}")
        
        print("\n🧪 To test all models:")
        print("  make test-models")
        print("\n🧪 To test specific models:")
        print(f"  make test-models MODELS=\"{','.join([m['name'] for m in sorted_models[:3]])}\"")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure Ollama is running:")
        print("  ollama serve")
        sys.exit(1)


if __name__ == "__main__":
    list_models()