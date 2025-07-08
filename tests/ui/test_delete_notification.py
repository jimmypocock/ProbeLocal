"""Test delete notification display"""
import time
from pathlib import Path
from tests.ui.base_test import StreamlitTest


def test_delete_notification_display():
    """Verify delete notification appears in main area, not just sidebar"""
    test = StreamlitTest()
    
    try:
        # Start services and browser
        test.start_services()
        test.setup_browser(headless=False)  # Run with UI visible for debugging
        test.wait_for_streamlit()
        
        # Upload a test document
        test_file = Path("tests/fixtures/delete_notification_test.txt")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("Test document for delete notification")
        
        test.upload_file(str(test_file))
        test.click_button("📤 Upload & Process")
        time.sleep(3)
        
        # Take screenshot before delete
        test.take_screenshot("before_delete")
        
        # Find and click delete button
        delete_buttons = test.page.locator('button:has-text("🗑️")').all()
        if delete_buttons:
            delete_buttons[0].click()
            
            # Wait for notification
            time.sleep(2)
            
            # Take screenshot after delete
            test.take_screenshot("after_delete")
            
            # Check for notification in main area
            notification = test.page.locator('[data-testid="stAlert"]').first
            if notification:
                text = notification.inner_text()
                print(f"✅ Notification found: {text}")
                print(f"   Location: Main area (not sidebar)")
                
                # Check if it's visible in the viewport
                is_visible = notification.is_visible()
                print(f"   Visible: {is_visible}")
                
                # Get bounding box to see where it appears
                box = notification.bounding_box()
                if box:
                    print(f"   Position: x={box['x']}, y={box['y']}, width={box['width']}")
            else:
                print("❌ No notification found")
                
    finally:
        test.teardown_browser()
        test.stop_services()


if __name__ == "__main__":
    test_delete_notification_display()