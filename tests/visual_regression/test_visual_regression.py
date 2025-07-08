#!/usr/bin/env python3
"""Visual regression testing for Streamlit UI"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️  Playwright not installed. Install with: pip install playwright && playwright install chromium")


class VisualRegressionTester:
    """Visual regression testing for Streamlit app"""
    
    def __init__(self):
        self.app_url = "http://localhost:2402"
        self.screenshots_dir = Path("tests/visual_regression/screenshots")
        self.baseline_dir = self.screenshots_dir / "baseline"
        self.current_dir = self.screenshots_dir / "current"
        self.diff_dir = self.screenshots_dir / "diff"
        
        # Create directories
        for dir_path in [self.baseline_dir, self.current_dir, self.diff_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        self.viewport_sizes = [
            {"width": 1920, "height": 1080, "name": "desktop"},
            {"width": 1366, "height": 768, "name": "laptop"},
            {"width": 768, "height": 1024, "name": "tablet"},
            {"width": 375, "height": 812, "name": "mobile"}
        ]
    
    async def setup_browser(self) -> tuple:
        """Setup browser and page"""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        return playwright, browser, page
    
    async def wait_for_app_ready(self, page: Page) -> None:
        """Wait for Streamlit app to be ready"""
        await page.goto(self.app_url)
        
        # Wait for Streamlit to load
        await page.wait_for_selector('div[data-testid="stApp"]', timeout=30000)
        
        # Wait for header to be visible
        await page.wait_for_selector('h1:has-text("Greg - AI Playground")', timeout=10000)
        
        # Wait a bit more for dynamic content
        await asyncio.sleep(2)
    
    async def capture_screenshot(self, page: Page, name: str, viewport: Dict[str, Any], is_baseline: bool = False) -> str:
        """Capture a screenshot"""
        # Set viewport
        await page.set_viewport_size({"width": viewport["width"], "height": viewport["height"]})
        await asyncio.sleep(1)  # Wait for resize
        
        # Determine path
        dir_path = self.baseline_dir if is_baseline else self.current_dir
        filename = f"{name}_{viewport['name']}.png"
        filepath = dir_path / filename
        
        # Capture screenshot
        await page.screenshot(path=str(filepath), full_page=True)
        
        return str(filepath)
    
    async def capture_ui_states(self, page: Page, is_baseline: bool = False) -> List[Dict[str, str]]:
        """Capture screenshots of different UI states"""
        screenshots = []
        
        for viewport in self.viewport_sizes:
            print(f"📸 Capturing {viewport['name']} viewport...")
            
            # 1. Initial state
            await self.wait_for_app_ready(page)
            path = await self.capture_screenshot(page, "01_initial_state", viewport, is_baseline)
            screenshots.append({"name": "Initial State", "viewport": viewport['name'], "path": path})
            
            # 2. With notification
            await page.evaluate("""
                const notification = document.createElement('div');
                notification.className = 'stSuccess';
                notification.textContent = '✅ Test notification';
                document.querySelector('[data-testid="stApp"]').appendChild(notification);
            """)
            await asyncio.sleep(0.5)
            path = await self.capture_screenshot(page, "02_with_notification", viewport, is_baseline)
            screenshots.append({"name": "With Notification", "viewport": viewport['name'], "path": path})
            
            # 3. Sidebar expanded
            try:
                # Try to expand sidebar
                sidebar_button = await page.query_selector('button[aria-label="Open sidebar"]')
                if sidebar_button:
                    await sidebar_button.click()
                    await asyncio.sleep(1)
                    path = await self.capture_screenshot(page, "03_sidebar_expanded", viewport, is_baseline)
                    screenshots.append({"name": "Sidebar Expanded", "viewport": viewport['name'], "path": path})
            except:
                print(f"⚠️  Could not expand sidebar for {viewport['name']}")
            
            # 4. Chat interface (if document loaded)
            chat_input = await page.query_selector('textarea[placeholder*="Ask about"]')
            if chat_input:
                await chat_input.fill("Test question")
                await asyncio.sleep(0.5)
                path = await self.capture_screenshot(page, "04_chat_input", viewport, is_baseline)
                screenshots.append({"name": "Chat Input", "viewport": viewport['name'], "path": path})
            
            # 5. Error state simulation
            await page.evaluate("""
                const error = document.createElement('div');
                error.className = 'stAlert';
                error.innerHTML = '<div style="color: red;">❌ Simulated error message</div>';
                document.querySelector('[data-testid="stApp"]').appendChild(error);
            """)
            await asyncio.sleep(0.5)
            path = await self.capture_screenshot(page, "05_error_state", viewport, is_baseline)
            screenshots.append({"name": "Error State", "viewport": viewport['name'], "path": path})
            
            # Clean up
            await page.reload()
        
        return screenshots
    
    async def compare_screenshots(self) -> Dict[str, Any]:
        """Compare current screenshots with baseline"""
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "missing_baseline": 0,
            "differences": []
        }
        
        # Get all current screenshots
        current_files = list(self.current_dir.glob("*.png"))
        
        for current_file in current_files:
            results["total"] += 1
            baseline_file = self.baseline_dir / current_file.name
            
            if not baseline_file.exists():
                results["missing_baseline"] += 1
                results["differences"].append({
                    "file": current_file.name,
                    "status": "missing_baseline"
                })
                continue
            
            # Simple file size comparison (more sophisticated comparison would use image diff libraries)
            current_size = current_file.stat().st_size
            baseline_size = baseline_file.stat().st_size
            
            # Allow 5% difference in file size
            size_diff_percent = abs(current_size - baseline_size) / baseline_size * 100
            
            if size_diff_percent > 5:
                results["failed"] += 1
                results["differences"].append({
                    "file": current_file.name,
                    "status": "different",
                    "size_diff_percent": size_diff_percent
                })
            else:
                results["passed"] += 1
        
        return results
    
    async def run_tests(self, create_baseline: bool = False) -> None:
        """Run visual regression tests"""
        if not PLAYWRIGHT_AVAILABLE:
            print("❌ Playwright not available, skipping visual regression tests")
            return
        
        print(f"🎨 Running Visual Regression Tests {'(Creating Baseline)' if create_baseline else ''}")
        print(f"📍 App URL: {self.app_url}")
        
        playwright, browser, page = await self.setup_browser()
        
        try:
            # Check if app is running
            try:
                await page.goto(self.app_url, timeout=5000)
            except:
                print("❌ Streamlit app not running at http://localhost:2402")
                print("   Start it with: streamlit run app.py")
                return
            
            # Capture screenshots
            screenshots = await self.capture_ui_states(page, is_baseline=create_baseline)
            
            print(f"\n✅ Captured {len(screenshots)} screenshots")
            
            if not create_baseline:
                # Compare with baseline
                print("\n🔍 Comparing screenshots...")
                results = await self.compare_screenshots()
                
                print(f"\n📊 Results:")
                print(f"   Total: {results['total']}")
                print(f"   Passed: {results['passed']} ✅")
                print(f"   Failed: {results['failed']} ❌")
                print(f"   Missing Baseline: {results['missing_baseline']} ⚠️")
                
                if results['differences']:
                    print("\n🔍 Differences found:")
                    for diff in results['differences']:
                        print(f"   - {diff['file']}: {diff['status']}")
                        if 'size_diff_percent' in diff:
                            print(f"     Size difference: {diff['size_diff_percent']:.1f}%")
                
                # Save results
                results_file = self.screenshots_dir / "results.json"
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                
                if results['failed'] > 0:
                    print("\n❌ Visual regression tests failed!")
                else:
                    print("\n✅ All visual regression tests passed!")
            else:
                print("\n✅ Baseline screenshots created successfully!")
                print(f"   Saved to: {self.baseline_dir}")
        
        finally:
            await browser.close()
            await playwright.stop()


async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual Regression Testing")
    parser.add_argument("--create-baseline", action="store_true", 
                       help="Create baseline screenshots")
    args = parser.parse_args()
    
    tester = VisualRegressionTester()
    await tester.run_tests(create_baseline=args.create_baseline)


if __name__ == "__main__":
    asyncio.run(main())