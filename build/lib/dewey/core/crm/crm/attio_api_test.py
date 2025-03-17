"""Test script for Attio API integration following official documentation examples."""
import os
import requests
import logging
from dotenv import load_dotenv

def main():
    # Initialize environment and logging
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Check for required API key
    api_key = os.getenv("ATTIO_API_KEY")
    if not api_key:
        logger.error("ATTIO_API_KEY environment variable not set")
        logger.info("Troubleshooting:")
        logger.info("1. Create a .env file in project root")
        logger.info("2. Add: ATTIO_API_KEY=your_live_key_here")
        return
    
    # Configure API request as per documentation
    headers = {"Authorization": f"Bearer {api_key}"}
    url = "https://api.attio.com/v2/lists"
    
    try:
        logger.info("Making API call to /v2/lists endpoint...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Process results
        lists = response.json().get('data', [])
        logger.info(f"Successfully retrieved {len(lists)} lists")
        
        # Display sample output with safe field access
        for lst in lists[:3]:  # Show first 3 lists to avoid overflow
            logger.debug("Raw list structure: %s", lst)  # Help debug schema changes
            logger.debug("Full ID structure: %s", lst.get('id', {}))
            logger.info(
                "List: %s (Workspace ID: %s, List ID: %s)",
                lst.get('attributes', {}).get('name', 'Unnamed List'),
                lst.get('id', {}).get('workspace_id', 'Unknown'),
                lst.get('id', {}).get('list_id', 'Unknown')
            )
            
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        logger.info("Troubleshooting steps:")
        logger.info("1. Verify API key has 'lists:read' permission")
        logger.info("2. Check network connectivity")
        logger.info("3. Validate API status at https://status.attio.com")

if __name__ == "__main__":
    main()
