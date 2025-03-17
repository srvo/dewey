from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

import os
from playwright.sync_api import sync_playwright
import pandas as pd
from pathlib import Path
from datetime import datetime
import keyring

class AltruistCollector:
    def __init__(self, debug=False):
        self.debug = debug
        
        # Altruist specific configuration
        self.altruist_url = "https://app.altruist.com/login"
        
        # Get browserless configuration with defaults
        self.browserless_url = os.getenv('SERVICE_FQDN_BROWSERLESS', 
            'http://browserless-vsosskcowsko80wwc4kgs0g4.5.78.111.69.sslip.io')
        self.token = os.getenv('SERVICE_PASSWORD_BROWSERLESS', 
            'Q1ULNqMPRZrrV2vcC9p4BtxMzZnWo7Ez')
            
        if not self.browserless_url or not self.token:
            raise ValueError("Browserless URL and token must be set in environment variables")
            
        self.ws_url = self.browserless_url.replace('http', 'ws')
        
        if self.debug:
            print(f"Browserless URL: {self.browserless_url}")
            print(f"WebSocket URL: {self.ws_url}")
            print(f"Altruist URL: {self.altruist_url}")
        
        # Get credentials from keychain
        self.credentials = {
            'email': keyring.get_password('altruist', 'email'),
            'password': keyring.get_password('altruist', 'password')
        }
        
        if self.debug:
            print(f"Found email: {self.credentials['email'] is not None}")
            print(f"Found password: {self.credentials['password'] is not None}")
        
        if not all(self.credentials.values()):
            raise ValueError("Altruist credentials not found in keychain")
        
        # Setup output directory
        self.output_dir = Path("/Users/srvo/lc/collection/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def login_to_altruist(self, page, credentials, max_retries=3):
        """Handle Altruist login sequence including MFA with retries"""
        for attempt in range(max_retries):
            try:
                if self.debug:
                    print(f"\nLogin attempt {attempt + 1} of {max_retries}")
                    print("Navigating to Altruist login page...")
                
                page.goto(self.altruist_url)
                
                # Initial login
                if self.debug:
                    print("Filling login credentials...")
                page.wait_for_selector('input[type="email"]')
                page.fill('input[type="email"]', credentials['email'])
                page.fill('input[type="password"]', credentials['password'])
                page.click('button[type="submit"]')
                
                # Handle MFA
                if self.debug:
                    print("Waiting for MFA page...")
                page.wait_for_selector('input[type="text"]', timeout=30000)
                
                mfa_code = self.get_mfa_code()
                
                if self.debug:
                    print(f"Entering MFA code: {mfa_code}")
                page.fill('input[type="text"]', mfa_code)
                page.click('button[type="submit"]')
                
                # Wait for either success or error
                try:
                    if self.debug:
                        print("Checking for successful login...")
                    # Try to detect error message first (faster timeout)
                    error_visible = page.wait_for_selector('.error-message', timeout=5000)
                    if error_visible:
                        error_text = page.text_content('.error-message')
                        print(f"MFA Error: {error_text}")
                        if attempt < max_retries - 1:
                            print("Retrying with new code...")
                            continue
                        return False
                except:
                    # No error found, wait for dashboard
                    if self.debug:
                        print("Waiting for dashboard...")
                    page.wait_for_selector('.dashboard', timeout=30000)
                    
                    if self.debug:
                        print("Successfully logged into Altruist")
                        page.screenshot(path=self.output_dir / "login_success.png")
                    return True
                
            except Exception as e:
                print(f"Login attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    print("Retrying...")
                    continue
                if self.debug:
                    try:
                        page.screenshot(path=self.output_dir / f"login_error_{attempt + 1}.png")
                    except:
                        print("Could not save error screenshot")
                return False
        
        return False
    
    def get_mfa_code(self):
        """Get MFA code from user input with basic validation"""
        while True:
            if self.debug:
                print("\nWaiting for MFA code from Google Authenticator...")
            code = input("Enter 6-digit MFA code (or 'q' to quit): ").strip()
            
            if code.lower() == 'q':
                raise Exception("User cancelled MFA input")
            
            if len(code) == 6 and code.isdigit():
                return code
            
            print("Invalid code format. Please enter 6 digits.")
    
    def collect_transactions(self, credentials):
        """Collect transaction data for all accounts"""
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(
                f"{self.ws_url}?token={self.token}"
            )
            
            try:
                page = browser.new_page()
                
                # Enable request logging in debug mode
                if self.debug:
                    page.on("request", lambda req: print(f">> {req.method} {req.url}"))
                    page.on("response", lambda res: print(f"<< {res.status} {res.url}"))
                
                # Login first
                if not self.login_to_altruist(page, credentials):
                    raise Exception("Failed to login to Altruist")
                
                # TODO: Add navigation to transactions page
                # TODO: Add data extraction logic
                # TODO: Add CSV export
                
            except Exception as e:
                print(f"Error collecting data: {str(e)}")
                if self.debug:
                    page.screenshot(path=self.output_dir / "error.png")
                raise
                
            finally:
                browser.close()

if __name__ == "__main__":
    # Install keyring if not present
    try:
        import keyring
    except ImportError:
        import subprocess
        subprocess.run(["uv", "pip", "install", "keyring"])
        import keyring
    
    collector = AltruistCollector(debug=True)
    collector.collect_transactions(collector.credentials)