"""Pytest configuration and shared fixtures for all tests"""
import pytest
import os
import time
import requests
import subprocess
from pathlib import Path
from typing import Generator

# Determine if we're in CI/CD environment
IS_CI = os.getenv("CI", "false").lower() == "true"

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
STREAMLIT_URL = os.getenv("STREAMLIT_URL", "http://localhost:2402")


@pytest.fixture(scope="session")
def api_url() -> str:
    """Get API base URL"""
    return API_BASE_URL


@pytest.fixture(scope="session")
def ensure_services():
    """Ensure required services are running
    
    In CI/CD: Assumes services are started externally
    In local dev: Checks if services are running, doesn't start them
    """
    if IS_CI:
        # In CI, services should be started by the pipeline
        print("Running in CI mode - expecting services to be started externally")
        yield
        return
    
    # Local development - just check if services are available
    services_ok = True
    
    # Check API
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print(f"✓ API is running at {API_BASE_URL}")
        else:
            print(f"✗ API returned status {response.status_code}")
            services_ok = False
    except requests.exceptions.RequestException as e:
        print(f"✗ API is not accessible at {API_BASE_URL}: {e}")
        services_ok = False
    
    # Check Ollama
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✓ Ollama is running")
        else:
            print(f"✗ Ollama returned status {response.status_code}")
            services_ok = False
    except requests.exceptions.RequestException:
        print("✗ Ollama is not accessible")
        services_ok = False
    
    if not services_ok:
        pytest.exit(
            "Required services are not running. Please run 'make run' first.",
            returncode=1
        )
    
    yield


@pytest.fixture(scope="function")
def test_file_factory(tmp_path) -> Generator:
    """Factory for creating test files"""
    created_files = []
    
    def _create_file(filename: str, content: str) -> Path:
        file_path = tmp_path / filename
        file_path.write_text(content)
        created_files.append(file_path)
        return file_path
    
    yield _create_file
    
    # Cleanup
    for file_path in created_files:
        if file_path.exists():
            file_path.unlink()


@pytest.fixture(scope="function")
def uploaded_document_id(api_url, test_file_factory):
    """Upload a test document and return its ID"""
    # Create test file
    test_file = test_file_factory(
        "test_doc.txt",
        "This is a test document for automated testing."
    )
    
    # Upload file
    with open(test_file, 'rb') as f:
        files = {"file": ("test_doc.txt", f, "text/plain")}
        data = {"model": "mistral"}
        response = requests.post(f"{api_url}/upload", files=files, data=data)
    
    assert response.status_code == 200
    doc_id = response.json()["document_id"]
    
    yield doc_id
    
    # Cleanup
    try:
        requests.delete(f"{api_url}/documents/{doc_id}")
    except:
        pass  # Best effort cleanup


@pytest.fixture(scope="session")
def performance_threshold():
    """Performance thresholds for different operations"""
    return {
        "api_response_time": 2.0,  # seconds
        "document_upload_time": 30.0,  # seconds
        "query_response_time": 10.0,  # seconds
        "ui_load_time": 5.0,  # seconds
    }


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "ui: marks tests as UI tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_ollama: marks tests that require Ollama to be running"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their location"""
    for item in items:
        # Auto-mark based on test location
        if "tests/unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "tests/ui" in str(item.fspath):
            item.add_marker(pytest.mark.ui)
        
        # Mark slow tests
        if "image" in item.name or "story" in item.name or "invoice" in item.name:
            item.add_marker(pytest.mark.slow)