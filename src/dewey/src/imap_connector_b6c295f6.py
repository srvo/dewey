import imaplib
import os
import sys

# Get credentials from environment or command line
server = os.getenv("IMAP_SERVER", "imap.gmail.com")
username = os.getenv("EMAIL_USER", "sloane@ethicic.com")
password = os.getenv("EMAIL_PASSWORD", "cmis kdor uwvo uykj")

# Command line args override environment variables
if len(sys.argv) > 1:
    password = sys.argv[1]


try:
    # Try with default settings
    mail = imaplib.IMAP4_SSL(server)
    mail.login(username, password)
    mail.logout()
except Exception:
    sys.exit(1)
