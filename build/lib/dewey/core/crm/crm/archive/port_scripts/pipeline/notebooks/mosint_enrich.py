import os
import subprocess
import json
import sys

def run_mosint(email, mosint_path):
    """Run mosint for a single email and return results"""
    try:
        # Create a temporary file for JSON output
        temp_output = f"/tmp/mosint_{email.replace('@', '_at_')}.json"
        
        print(f"[DEBUG] Running mosint command for {email}")
        # Run mosint with output file
        cmd = [mosint_path, email, '-o', temp_output, '-s']
        print(f"[DEBUG] Executing command: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # Timeout after 30 seconds
        )
        
        print(f"[DEBUG] Command stdout: {result.stdout}")
        print(f"[DEBUG] Command stderr: {result.stderr}")
        
        if result.returncode == 0:
            # Read the JSON file
            try:
                with open(temp_output, 'r') as f:
                    data = json.load(f)
                print(f"[DEBUG] Parsed JSON data: {json.dumps(data, indent=2)}")
                return data
            except FileNotFoundError:
                print(f"[ERROR] Output file not found: {temp_output}")
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse JSON from file: {str(e)}")
            finally:
                # Clean up the temporary file
                try:
                    os.remove(temp_output)
                except OSError:
                    pass
        else:
            print(f"[ERROR] Mosint command failed with return code {result.returncode}")
    except Exception as e:
        print(f"[ERROR] Error processing {email}: {str(e)}")
    return None

def enrich_contact(contact, mosint_data):
    """Enrich contact record with mosint data"""
    if not mosint_data:
        print(f"[DEBUG] No mosint data available for {contact.get('email', 'unknown')}")
        return contact
        
    enriched = contact.copy()
    
    # Add new fields for mosint data
    verification_status = mosint_data.get('verification', {}).get('status', '')
    social_media = mosint_data.get('social_media', [])
    breached_sites = mosint_data.get('breached_sites', [])
    related_domains = mosint_data.get('related_domains', [])
    password_leaks = mosint_data.get('password_leaks', '')
    pastebin_records = mosint_data.get('pastebin', [])
    
    print(f"[DEBUG] Enrichment data:")
    print(f"  - Verification: {verification_status}")
    print(f"  - Social Media: {social_media}")
    print(f"  - Breached Sites: {breached_sites}")
    print(f"  - Related Domains: {related_domains}")
    print(f"  - Password Leaks: {password_leaks}")
    print(f"  - Pastebin Records: {len(pastebin_records)}")
    
    enriched.update({
        'email_verified': verification_status,
        'social_media': ', '.join(social_media),
        'breached_sites': ', '.join(breached_sites),
        'related_domains': ', '.join(related_domains),
        'password_leaks': password_leaks,
        'pastebin_records': len(pastebin_records)
    })
    
    return enriched

def main():
    """Main execution function"""
    # Find mosint path
    mosint_path = subprocess.run(['which', 'mosint'], capture_output=True, text=True).stdout.strip()
    if not mosint_path:
        print("[ERROR] mosint not found in PATH. Please install it first.")
        sys.exit(1)
    
    print(f"[INFO] Found mosint at: {mosint_path}")
    
    # For testing, you can hardcode an email here
    test_email = "test@example.com"  # Replace with a real email for testing
    
    # Run test enrichment
    print(f"[INFO] Testing enrichment with {test_email}")
    mosint_data = run_mosint(test_email, mosint_path)
    
    if mosint_data:
        test_contact = {"email": test_email}
        enriched = enrich_contact(test_contact, mosint_data)
        print("\n[INFO] Enriched contact data:")
        print(json.dumps(enriched, indent=2))
    else:
        print("[ERROR] Failed to get mosint data")

if __name__ == "__main__":
    main()