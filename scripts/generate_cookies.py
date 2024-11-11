#!/usr/bin/env python3

import os
import sys
import json
import argparse
from typing import Dict, Any

import browser_cookie3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from http.cookiejar import MozillaCookieJar

class AppleMusicCookieGenerator:
    def __init__(self, browser: str = 'chrome', output_path: str = None):
        """
        Initialize cookie generator
        
        Args:
            browser (str): Browser to extract cookies from
            output_path (str): Path to save cookies file
        """
        self.browser = browser.lower()
        self.output_path = output_path or os.path.join(os.path.expanduser('~'), '.gamdl', 'cookies.txt')
        self.driver = None

    def _setup_selenium_driver(self):
        """
        Setup Chrome WebDriver
        """
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        
        # Optional: Run in headless mode
        # chrome_options.add_argument("--headless")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    def extract_browser_cookies(self) -> Dict[str, Any]:
        """
        Extract cookies from specified browser
        
        Returns:
            Dict[str, Any]: Extracted cookies
        """
        try:
            if self.browser == 'chrome':
                cookies = browser_cookie3.chrome(domain_name='apple.com')
            elif self.browser == 'firefox':
                cookies = browser_cookie3.firefox(domain_name='apple.com')
            elif self.browser == 'safari':
                cookies = browser_cookie3.safari(domain_name='apple.com')
            else:
                raise ValueError(f"Unsupported browser: {self.browser}")
            
            return {cookie.name: cookie.value for cookie in cookies}
        except Exception as e:
            print(f"Error extracting browser cookies: {e}")
            return {}

    def interactive_login(self) -> Dict[str, Any]:
        """
        Perform interactive login to Apple Music
        
        Returns:
            Dict[str, Any]: Extracted cookies after login
        """
        self._setup_selenium_driver()
        
        try:
            # Navigate to Apple Music
            self.driver.get('https://music.apple.com/login')
            
            # Wait for user to login
            print("Please login to Apple Music in the browser window...")
            
            # Wait for a specific element that indicates successful login
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="profile-menu"]'))
            )
            
            # Extract cookies
            browser_cookies = {
                cookie['name']: cookie['value'] 
                for cookie in self.driver.get_cookies() 
                if 'apple.com' in cookie.get('domain', '')
            }
            
            return browser_cookies
        
        except Exception as e:
            print(f"Login error: {e}")
            return {}
        finally:
            if self.driver:
                self.driver.quit()

    def save_cookies(self, cookies: Dict[str, Any]):
        """
        Save cookies to Netscape/Mozilla format
        
        Args:
            cookies (Dict[str, Any]): Cookies to save
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
        # Create Mozilla Cookie Jar
        cookie_jar = MozillaCookieJar(self.output_path)
        
        # Add cookies to jar
        for name, value in cookies.items():
            cookie_jar.set_cookie(
                browser_cookie3.create_cookie(
                    name=name, 
                    value=value, 
                    domain='.apple.com'
                )
            )
        
        # Save cookies
        cookie_jar.save(ignore_discard=True, ignore_expires=True)
        print(f"Cookies saved to {self.output_path}")

    def validate_cookies(self, cookies: Dict[str, Any]) -> bool:
        """
        Basic validation of extracted cookies
        
        Args:
            cookies (Dict[str, Any]): Cookies to validate
        
        Returns:
            bool: Whether cookies are valid
        """
        required_cookies = [
            'itua',  # Storefront
            'media-user-token',
            'acn01'  # Apple account token
        ]
        
        return all(cookie in cookies for cookie in required_cookies)

def main():
    # Argument Parser
    parser = argparse.ArgumentParser(description='Apple Music Cookie Generator')
    parser.add_argument(
        '--browser', 
        choices=['chrome', 'firefox', 'safari'], 
        default='chrome', 
        help='Browser to extract cookies from'
    )
    parser.add_argument(
        '--output', 
        help='Path to save cookies file'
    )
    parser.add_argument(
        '--method', 
        choices=['browser', 'interactive'], 
        default='interactive', 
        help='Method to extract cookies'
    )
    
    args = parser.parse_args()
    
    # Initialize Cookie Generator
    cookie_generator = AppleMusicCookieGenerator(
        browser=args.browser, 
        output_path=args.output
    )
    
    try:
        # Extract Cookies
        if args.method == 'browser':
            cookies = cookie_generator.extract_browser_cookies()
        else:
            cookies = cookie_generator.interactive_login()
        
        # Validate Cookies
        if not cookie_generator.validate_cookies(cookies):
            print("Invalid or incomplete cookies. Please try again.")
            sys.exit(1)
        
        # Save Cookies
        cookie_generator.save_cookies(cookies)
        
        # Optional: Print extracted cookie names for verification
        print("Extracted Cookies:")
        print(", ".join(cookies.keys()))
    
    except Exception as e:
        print(f"Cookie generation failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
