import requests
import urllib3
from typing import Dict
from datetime import datetime
import json

class SearchDiagnostics:
    def __init__(self):
        # Use container names since we're all on search_network
        self.whoogle_base = "http://whoogle-okko0cck440ww0gogc04skw8:5000"
        self.searx_base = "http://searxng-q4ssoskw8swsc8g8o84gogkc:8080"
        self.verify_ssl = False
        
        # Create session with longer timeout
        self.session = requests.Session()
        self.session.timeout = 10
        
        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    def check_services(self):
        """Test both search services"""
        results = {
            'whoogle': {'status': 'unknown', 'error': None},
            'searx': {'status': 'unknown', 'error': None}
        }
        
        # Test Whoogle
        try:
            whoogle_response = self.session.get(
                f"{self.whoogle_base}/search",
                params={'q': 'test'},
                verify=self.verify_ssl
            )
            results['whoogle'] = {
                'status': 'ok' if whoogle_response.status_code == 200 else 'error',
                'code': whoogle_response.status_code,
                'error': None
            }
        except Exception as e:
            results['whoogle']['status'] = 'error'
            results['whoogle']['error'] = str(e)
            
        # Test SearXNG
        try:
            searx_response = self.session.get(
                f"{self.searx_base}/search",
                params={
                    'q': 'test',
                    'format': 'json',
                    'categories': 'news'
                },
                verify=self.verify_ssl
            )
            results['searx'] = {
                'status': 'ok' if searx_response.status_code == 200 else 'error',
                'code': searx_response.status_code,
                'error': None
            }
        except Exception as e:
            results['searx']['status'] = 'error'
            results['searx']['error'] = str(e)
            
        return results

def main():
    """Run diagnostics"""
    print("\n=== Search Services Diagnostics ===\n")
    
    diagnostics = SearchDiagnostics()
    results = diagnostics.check_services()
    
    # Print results
    for service, data in results.items():
        print(f"{service.upper()} Status: {data['status']}")
        if data.get('code'):
            print(f"Response Code: {data['code']}")
        if data.get('error'):
            print(f"Error: {data['error']}")
        print()
    
    return results

if __name__ == "__main__":
    main()