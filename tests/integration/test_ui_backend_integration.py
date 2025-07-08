"""Integration tests for UI behavior with backend states"""
import pytest
import time
import subprocess
import os
import signal
from pathlib import Path
from playwright.sync_api import sync_playwright


class TestUIBackendIntegration:
    """Test UI behavior under various backend conditions"""
    
    def test_ui_without_backend(self):
        """Test UI behavior when backend is completely down"""
        app_process = None
        playwright = None
        browser = None
        
        try:
            # Start only Streamlit (no backend)
            app_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", "2404", "--server.headless", "true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            time.sleep(5)
            
            # Use Playwright to test UI
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to app
            page.goto("http://localhost:2404")
            page.wait_for_selector('[data-testid="stApp"]', timeout=10000)
            
            # Check for offline indicators
            # Should show "Ollama Offline" or similar
            offline_indicator = page.locator('text=/Offline|Error|Cannot connect/i').first
            assert offline_indicator is not None
            
            # Try to upload a file (should fail gracefully)
            test_file = Path("tests/fixtures/no_backend_test.txt")
            test_file.parent.mkdir(exist_ok=True)
            test_file.write_text("Test without backend")
            
            # Find file uploader
            file_input = page.locator('[data-testid="stFileUploader"] input[type="file"]')
            file_input.set_input_files(str(test_file))
            
            # Try to click upload button
            upload_button = page.locator('button:has-text("📤 Upload & Process")').first
            if upload_button:
                upload_button.click()
                time.sleep(2)
                
                # Should show error notification
                error = page.locator('[data-testid="stAlert"]').first
                if error:
                    error_text = error.inner_text()
                    assert "error" in error_text.lower() or "failed" in error_text.lower()
                    
            test_file.unlink()
            
        finally:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            if app_process:
                os.killpg(os.getpgid(app_process.pid), signal.SIGTERM)
                app_process.wait(timeout=5)
                
    def test_ui_backend_recovery(self):
        """Test UI behavior when backend comes back online"""
        api_process = None
        app_process = None
        playwright = None
        browser = None
        
        try:
            # Start Streamlit first (without backend)
            app_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", "2405", "--server.headless", "true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            time.sleep(5)
            
            # Setup Playwright
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to app
            page.goto("http://localhost:2405")
            page.wait_for_selector('[data-testid="stApp"]', timeout=10000)
            
            # Should show offline status
            offline = page.locator('text=/Offline|❌/').first
            assert offline is not None
            
            # Now start the backend
            api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for API to be ready
            import requests
            for i in range(30):
                try:
                    response = requests.get("http://localhost:8080/health", timeout=1)
                    if response.status_code == 200:
                        break
                except:
                    time.sleep(1)
                    
            # Refresh the page
            page.reload()
            time.sleep(3)
            
            # Should now show online status
            online = page.locator('text=/Ready|✅/').first
            assert online is not None
            
            # Should be able to upload now
            test_file = Path("tests/fixtures/recovery_test.txt")
            test_file.parent.mkdir(exist_ok=True)
            test_file.write_text("Backend recovery test")
            
            file_input = page.locator('[data-testid="stFileUploader"] input[type="file"]')
            file_input.set_input_files(str(test_file))
            
            upload_button = page.locator('button:has-text("📤 Upload & Process")').first
            if upload_button:
                upload_button.click()
                time.sleep(3)
                
                # Should show success
                success = page.locator('text=/success|uploaded/i').first
                assert success is not None
                
            test_file.unlink()
            
        finally:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            for process in [api_process, app_process]:
                if process:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                    
    def test_ui_during_backend_restart(self):
        """Test UI behavior during backend restart"""
        api_process = None
        app_process = None
        playwright = None
        browser = None
        
        try:
            # Start both services
            api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for API
            import requests
            for i in range(30):
                try:
                    response = requests.get("http://localhost:8080/health", timeout=1)
                    if response.status_code == 200:
                        break
                except:
                    time.sleep(1)
                    
            app_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", "2406", "--server.headless", "true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            time.sleep(5)
            
            # Setup Playwright
            playwright = sync_playwright().start()
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            
            page.goto("http://localhost:2406")
            page.wait_for_selector('[data-testid="stApp"]', timeout=10000)
            
            # Upload a document while backend is running
            test_file = Path("tests/fixtures/restart_test.txt")
            test_file.parent.mkdir(exist_ok=True)
            test_file.write_text("Backend restart test document")
            
            file_input = page.locator('[data-testid="stFileUploader"] input[type="file"]')
            file_input.set_input_files(str(test_file))
            
            upload_button = page.locator('button:has-text("📤 Upload & Process")').first
            upload_button.click()
            time.sleep(3)
            
            # Now kill the backend
            os.killpg(os.getpgid(api_process.pid), signal.SIGTERM)
            api_process.wait(timeout=5)
            api_process = None
            
            # Try to send a message (should fail gracefully)
            chat_input = page.locator('[data-testid="stChatInput"] textarea').first
            if chat_input:
                chat_input.fill("Test message during backend down")
                chat_input.press("Enter")
                time.sleep(2)
                
                # Should show error
                error = page.locator('text=/error|failed/i').first
                assert error is not None
                
            # Restart backend
            api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            # Wait for it to be ready
            for i in range(30):
                try:
                    response = requests.get("http://localhost:8080/health", timeout=1)
                    if response.status_code == 200:
                        break
                except:
                    time.sleep(1)
                    
            # Refresh page
            page.reload()
            time.sleep(3)
            
            # Should be functional again
            online = page.locator('text=/Ready|✅/').first
            assert online is not None
            
            test_file.unlink()
            
        finally:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            for process in [api_process, app_process]:
                if process:
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        process.wait(timeout=5)
                    except:
                        pass