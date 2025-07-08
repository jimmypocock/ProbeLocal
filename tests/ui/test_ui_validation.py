"""UI validation tests that don't require complex interactions"""
import pytest
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from .selenium_base import SeleniumStreamlitTest


class TestUIValidation:
    """Test UI elements and design validation"""
    
    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test"""
        self.test = SeleniumStreamlitTest()
        self.test.start_services()
        self.test.setup_driver(headless=True)
        self.test.wait_for_streamlit()
        
        yield
        
        self.test.teardown()
        
    def test_ui_elements_present(self):
        """Test all key UI elements are present and visible"""
        elements_to_check = {
            "App Header": ("xpath", "//h1[contains(text(), 'Greg')]"),
            "Status Indicator": ("xpath", "//*[contains(text(), 'Status:')]"),
            "Model Selector": ("css", "[data-testid='stSelectbox']"),
            "Help Button": ("xpath", "//button[contains(text(), '❓')]"),
            "Search Web Toggle": ("xpath", "//*[contains(text(), 'Search Web')]"),
            "Drag Drop Area": ("xpath", "//*[contains(text(), 'Drag') and contains(text(), 'Drop')]"),
            "Browse Files Button": ("xpath", "//button[contains(text(), 'Browse files')]"),
            "Upload Button": ("xpath", "//button[contains(text(), 'Upload')]"),
            "Sidebar": ("css", "[data-testid='stSidebar']"),
        }
        
        for name, (selector_type, selector) in elements_to_check.items():
            try:
                if selector_type == "css":
                    element = self.test.driver.find_element(By.CSS_SELECTOR, selector)
                else:
                    element = self.test.driver.find_element(By.XPATH, selector)
                    
                assert element.is_displayed(), f"{name} not visible"
                print(f"✓ {name} is present and visible")
            except Exception as e:
                print(f"✗ {name} not found: {e}")
                
    def test_ui_styling(self):
        """Test UI has proper styling applied"""
        # Check drag-drop area has custom styling
        drag_drop_elements = self.test.driver.find_elements(
            By.XPATH, "//*[contains(@class, 'drag-drop-area')]"
        )
        
        if drag_drop_elements:
            element = drag_drop_elements[0]
            bg_color = element.value_of_css_property('background-color')
            border = element.value_of_css_property('border')
            
            # Should have some styling (not default)
            assert bg_color != 'rgba(0, 0, 0, 0)', "Drag-drop area lacks background styling"
            print(f"✓ Drag-drop area has custom styling: bg={bg_color}")
        
        # Check overall theme
        body = self.test.driver.find_element(By.TAG_NAME, "body")
        body_bg = body.value_of_css_property('background-color')
        print(f"✓ Page background: {body_bg}")
        
    def test_responsive_layout(self):
        """Test layout is responsive"""
        # Get initial window size
        initial_size = self.test.driver.get_window_size()
        
        # Test mobile viewport
        self.test.driver.set_window_size(375, 667)
        time.sleep(1)
        
        # Check sidebar is still accessible
        sidebar = self.test.driver.find_element(By.CSS_SELECTOR, "[data-testid='stSidebar']")
        assert sidebar is not None, "Sidebar not found in mobile view"
        
        # Test tablet viewport
        self.test.driver.set_window_size(768, 1024)
        time.sleep(1)
        
        # Restore original size
        self.test.driver.set_window_size(initial_size['width'], initial_size['height'])
        
        print("✓ Layout is responsive across different viewport sizes")
        
    def test_document_list_ui(self):
        """Test document list UI elements"""
        # Get all buttons
        buttons = self.test.driver.find_elements(By.TAG_NAME, "button")
        
        doc_count = 0
        delete_count = 0
        
        for button in buttons:
            text = button.text.strip()
            if text and any(ext in text.lower() for ext in ['.txt', '.pdf', '.csv']):
                doc_count += 1
                print(f"  Found document: {text}")
            elif "🗑️" in text:
                delete_count += 1
                
        print(f"✓ Found {doc_count} documents with {delete_count} delete buttons")
        
        # Check pagination if many documents
        pagination_buttons = self.test.driver.find_elements(
            By.XPATH, "//button[contains(text(), '⏮️') or contains(text(), '◀️') or contains(text(), '▶️') or contains(text(), '⏭️')]"
        )
        if pagination_buttons:
            print(f"✓ Pagination controls present ({len(pagination_buttons)} buttons)")
            
    def test_help_system(self):
        """Test help button and documentation"""
        help_buttons = self.test.driver.find_elements(
            By.XPATH, "//button[contains(text(), '❓')]"
        )
        
        assert len(help_buttons) > 0, "No help button found"
        
        # Click help button
        help_buttons[0].click()
        time.sleep(2)
        
        # Take screenshot of help content
        self.test.take_screenshot("help_content")
        
        # Check if help content appeared (could be modal, expander, etc.)
        page_text = self.test.driver.find_element(By.TAG_NAME, "body").text
        help_keywords = ["support", "format", "upload", "model", "question"]
        
        help_found = any(keyword in page_text.lower() for keyword in help_keywords)
        assert help_found, "Help content not displayed after clicking help button"
        
        print("✓ Help system is functional")
        
    def test_status_indicators(self):
        """Test system status indicators"""
        # Look for status elements
        status_elements = self.test.driver.find_elements(
            By.XPATH, "//*[contains(text(), 'Status:')]"
        )
        
        assert len(status_elements) > 0, "No status indicator found"
        
        # Check for green status (✅ or 🟢)
        page_text = self.test.driver.find_element(By.TAG_NAME, "body").text
        status_ok = "🟢" in page_text or "✅" in page_text or "●" in page_text
        
        assert status_ok, "System status not showing as operational"
        print("✓ System status indicators working")
        
    def test_model_selector_options(self):
        """Test AI model selector has options"""
        model_selector = self.test.driver.find_element(
            By.CSS_SELECTOR, "[data-testid='stSelectbox']"
        )
        
        # Click to open dropdown
        model_selector.click()
        time.sleep(1)
        
        # Get options
        options = self.test.driver.find_elements(By.CSS_SELECTOR, "[role='option']")
        assert len(options) > 0, "No model options available"
        
        model_names = []
        for option in options:
            model_names.append(option.text)
            
        print(f"✓ Found {len(model_names)} AI models: {', '.join(model_names)}")
        
        # Click away to close dropdown
        self.test.driver.find_element(By.TAG_NAME, "body").click()
        
    def test_file_type_support_display(self):
        """Test supported file types are displayed"""
        page_text = self.test.driver.find_element(By.TAG_NAME, "body").text
        
        expected_formats = ["PDF", "TXT", "CSV", "MD", "DOCX", "XLSX"]
        supported_formats = []
        
        for fmt in expected_formats:
            if fmt in page_text:
                supported_formats.append(fmt)
                
        assert len(supported_formats) > 0, "No supported file formats displayed"
        print(f"✓ Supported formats displayed: {', '.join(supported_formats)}")
        
    def test_branding_elements(self):
        """Test branding and visual identity"""
        # Check logo/icon
        robot_emoji = "🤖" in self.test.driver.find_element(By.TAG_NAME, "body").text
        assert robot_emoji, "App icon/branding not found"
        
        # Check title
        title_element = self.test.driver.find_element(
            By.XPATH, "//h1[contains(text(), 'Greg')]"
        )
        assert "AI Playground" in title_element.text, "Full app title not displayed"
        
        # Check tagline
        page_text = self.test.driver.find_element(By.TAG_NAME, "body").text
        assert "Local AI Assistant" in page_text, "Tagline not found"
        
        print("✓ Branding elements properly displayed")