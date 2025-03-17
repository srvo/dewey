#!/usr/bin/env python3

import os
import threading
import queue
import logging
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Data/scripts/logs/dialpad_export.log'),
        logging.StreamHandler()
    ]
)

# WebDAV configuration
WEBDAV_URL = "https://nx61057.your-storageshare.de/remote.php/webdav"
WEBDAV_USER = 'sloane@ethicic.com'
WEBDAV_PASSWORD = '5cnYp-SQYgT-j8FST-jsxrT-rs3jy'

# Let's test the connection first
def test_connection():
    try:
        session = requests.Session()
        session.auth = HTTPBasicAuth(WEBDAV_USER, WEBDAV_PASSWORD)
        response = session.request('PROPFIND', WEBDAV_URL, headers={'Depth': '0'})
        response.raise_for_status()
        logging.info("WebDAV connection successful!")
        return True
    except Exception as e:
        logging.error(f"WebDAV connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_connection()
    