import glob
import os

import markdown
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/documents"]


def get_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If no valid credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def create_doc_from_markdown() -> None:
    # Get credentials and create service
    creds = get_credentials()
    service = build("docs", "v1", credentials=creds)

    # Create new Google Doc
    title = "Dokku Deployment Notes"
    doc = service.documents().create(body={"title": title}).execute()
    doc_id = doc.get("documentId")

    # Get all markdown files in current directory
    markdown_files = glob.glob("*.md")

    for md_file in markdown_files:
        # Read markdown content
        with open(md_file) as file:
            content = file.read()

        # Convert markdown to HTML
        markdown.markdown(content)

        # Prepare the update request
        requests = [
            {
                "insertText": {
                    "location": {
                        "index": 1,
                    },
                    "text": f"\n\nFrom {md_file}:\n\n{content}\n\n",
                },
            },
        ]

        # Update the document
        service.documents().batchUpdate(
            documentId=doc_id,
            body={"requests": requests},
        ).execute()


if __name__ == "__main__":
    create_doc_from_markdown()
