#!/usr/bin/env python3
"""Quick script to test different models on the same document"""

import os
import sys

models_to_test = [
    "mistral",
    "llama3:8b", 
    "deepseek-coder:6.7b-instruct",
    "zephyr"
]

test_questions = [
    "What is the total amount?",
    "What is the invoice number?",
    "List all line items with their amounts",
    "What is the due date?"
]

print("Model Comparison Test")
print("=" * 50)
print("\nMake sure you have uploaded a document first!")
print("\nModels to test:")
for model in models_to_test:
    print(f"  - {model}")

print("\nTest questions:")
for q in test_questions:
    print(f"  - {q}")

print("\nTo test each model:")
print("1. Edit .env and change LOCAL_LLM_MODEL to each model")
print("2. Restart the app with 'make run'")
print("3. Ask the same questions and compare accuracy")