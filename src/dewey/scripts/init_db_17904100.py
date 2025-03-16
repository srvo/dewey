#!/usr/bin/env python3
import os
import sys

sys.path.append("/opt/email-sync")
os.environ["METADATA_DB_PATH"] = "/opt/email-sync/data/metadata.db"
from scripts.init_metadata_db import setup_metadata_database

setup_metadata_database("/opt/email-sync/data/metadata.db")
