#!/usr/bin/env python3
"""Run UI tests for Greg AI Playground"""
import sys
import subprocess
from pathlib import Path


def main():
    """Run all UI tests"""
    print("🧪 Running Streamlit UI Tests")
    print("=" * 60)
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent.parent.parent
    
    # Install Playwright browsers if needed
    print("📦 Ensuring Playwright browsers are installed...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    
    # Run the tests
    print("\n🚀 Starting UI tests...")
    test_files = [
        "tests/ui/test_document_management.py",
        "tests/ui/test_chat_interface.py", 
        "tests/ui/test_error_handling.py",
        "tests/ui/test_web_search_ui.py"
    ]
    
    for test_file in test_files:
        print(f"\n📋 Running {test_file}...")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            cwd=project_root
        )
        
        if result.returncode != 0:
            print(f"❌ Tests failed in {test_file}")
            return 1
            
    print("\n✅ All UI tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())