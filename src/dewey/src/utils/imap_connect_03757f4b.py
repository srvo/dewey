import imaplib
import os
import ssl
import sys

# Enable more verbose debugging
imaplib.Debug = 4

# Get credentials from environment or command line
server = os.getenv("IMAP_SERVER", "imap.gmail.com")
username = os.getenv("EMAIL_USER", "sloane@ethicic.com")
password = os.getenv("EMAIL_PASSWORD", "pamtnykjwacpsnu")

# Command line args override environment variables
if len(sys.argv) > 1:
    password = sys.argv[1]


try:
    # Create a context with relaxed SSL verification
    context = ssl.create_default_context()
    # Try with default settings
    mail = imaplib.IMAP4_SSL(server, ssl_context=context)
    # Try to get server capabilities
    typ, data = mail.capability()
    # Try login
    mail.login(username, password)
    mail.logout()
except Exception as e:
    if isinstance(e, imaplib.IMAP4.error):
        pass
    sys.exit(1)
