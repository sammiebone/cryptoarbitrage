import time
from playwright.sync_api import sync_playwright, expect

def verify_dashboard():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # 1. Go to the dashboard URL
            print("Navigating to the dashboard...")
            page.goto("http://localhost:5000", timeout=15000)

            # 2. Check for initial state
            print("Checking for initial state...")
            # Expect the status to be 'stopped' or 'unknown' initially
            expect(page.locator("text=/Status: (stopped|unknown|disconnected)/i")).to_be_visible(timeout=10000)
            print("Initial status verified.")

            # 3. Click the "Start Bot" button
            print("Clicking 'Start Bot'...")
            page.get_by_role("button", name="Start Bot").click()

            # 4. Wait for the status to change to "running"
            print("Waiting for status to become 'running'...")
            expect(page.locator("text=Status: running")).to_be_visible(timeout=15000)
            print("Status changed to 'running'.")

            # 5. Wait for a log message to appear
            print("Waiting for log messages...")
            # We expect the log viewer to contain at least one log entry
            log_viewer = page.locator("pre")
            expect(log_viewer).to_contain_text("Bot loop started", timeout=15000)
            print("Log messages found.")

            # 6. Take a screenshot
            print("Taking screenshot...")
            screenshot_path = "jules-scratch/verification/verification.png"
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")

        except Exception as e:
            print(f"An error occurred during verification: {e}")
            # Take a screenshot on error for debugging
            page.screenshot(path="jules-scratch/verification/error.png")
            raise

        finally:
            browser.close()

if __name__ == "__main__":
    verify_dashboard()
