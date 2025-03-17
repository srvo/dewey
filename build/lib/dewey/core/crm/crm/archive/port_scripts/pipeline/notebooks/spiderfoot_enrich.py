import os
import requests
import json
import sys
import time
from datetime import datetime

def start_scan(sf_host, api_key, email):
    """Start a SpiderFoot scan for an email and return the scan ID"""
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    
    # Configure the scan
    data = {
        "scanName": f"Email scan {email} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "scannerId": "AUTO",
        "useCase": "all",
        "target": email
    }
    
    print(f"[DEBUG] Starting scan for {email}")
    response = requests.post(f"{sf_host}/scan/new", headers=headers, json=data)
    
    if response.status_code == 200:
        scan_id = response.json().get('scanId')
        print(f"[DEBUG] Scan started with ID: {scan_id}")
        return scan_id
    else:
        print(f"[ERROR] Failed to start scan: {response.text}")
        return None

def get_scan_status(sf_host, api_key, scan_id):
    """Check the status of a scan"""
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"{sf_host}/scan/status/{scan_id}", headers=headers)
    
    if response.status_code == 200:
        return response.json().get('status')
    return None

def get_scan_results(sf_host, api_key, scan_id):
    """Get the results of a completed scan"""
    headers = {'Authorization': f'Bearer {api_key}'}
    response = requests.get(f"{sf_host}/scan/results/{scan_id}", headers=headers)
    
    if response.status_code == 200:
        return response.json()
    return None

def enrich_contact(contact, sf_results):
    """Enrich contact record with SpiderFoot data"""
    if not sf_results:
        print(f"[DEBUG] No SpiderFoot data available for {contact.get('email', 'unknown')}")
        return contact
        
    enriched = contact.copy()
    
    # Extract relevant information from results
    social_media = set()
    breached_sites = set()
    related_domains = set()
    
    for result in sf_results:
        type_data = result.get('type', '')
        data = result.get('data', '')
        
        if type_data == 'SOCIAL_MEDIA':
            social_media.add(data)
        elif type_data == 'EMAILADDR_COMPROMISED':
            breached_sites.add(data)
        elif type_data == 'DOMAIN_NAME':
            related_domains.add(data)
    
    print(f"[DEBUG] Enrichment data:")
    print(f"  - Social Media: {social_media}")
    print(f"  - Breached Sites: {breached_sites}")
    print(f"  - Related Domains: {related_domains}")
    
    enriched.update({
        'social_media': ', '.join(social_media),
        'breached_sites': ', '.join(breached_sites),
        'related_domains': ', '.join(related_domains)
    })
    
    return enriched

def main():
    """Main execution function"""
    # Configuration
    sf_host = os.getenv('SPIDERFOOT_HOST', 'http://localhost:5001')
    api_key = os.getenv('SPIDERFOOT_API_KEY')
    
    if not api_key:
        print("[ERROR] SPIDERFOOT_API_KEY environment variable not set")
        sys.exit(1)
    
    # For testing, you can hardcode an email here
    test_email = "test@example.com"  # Replace with a real email for testing
    
    # Start scan
    scan_id = start_scan(sf_host, api_key, test_email)
    if not scan_id:
        sys.exit(1)
    
    # Wait for scan to complete
    print("[INFO] Waiting for scan to complete...")
    while True:
        status = get_scan_status(sf_host, api_key, scan_id)
        if status == 'FINISHED':
            break
        elif status == 'FAILED':
            print("[ERROR] Scan failed")
            sys.exit(1)
        time.sleep(10)
    
    # Get results
    results = get_scan_results(sf_host, api_key, scan_id)
    if results:
        test_contact = {"email": test_email}
        enriched = enrich_contact(test_contact, results)
        print("\n[INFO] Enriched contact data:")
        print(json.dumps(enriched, indent=2))
    else:
        print("[ERROR] Failed to get scan results")

if __name__ == "__main__":
    main() 