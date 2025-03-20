# AI-Powered Email Prioritization System

This project uses the Gmail API and Google's Gemini AI to automatically prioritize your emails by applying labels based on content analysis and user feedback.

## Files

*   **`email_classifier.py`:** The main script that fetches emails, analyzes them with Gemini, and applies priority labels.
*   **`process_feedback.py`:** A script that collects user feedback *interactively*, structures it using the Gemini API, analyzes the feedback, and suggests (or optionally applies) changes to the prioritization rules.
*   **`email_preferences.json`:**  A JSON file containing rules and preferences for email prioritization.  You'll need to customize this file.
*   **`email_analysis.txt`:** A text file containing the prompt sent to the Gemini API for email analysis.
*   **`feedback.json`:**  A JSON file that stores user feedback. This file is created and updated automatically.  You no longer need to edit it directly.
*   **`credentials.json`:** Your Google Cloud credentials file, placed in the project root (`/Users/srvo/dewey/credentials.json`). **Do not commit this file to version control.**
*   **`gmail_token.json`:** A file that stores your OAuth tokens, automatically created in `/Users/srvo/dewey/config/gmail_token.json`. **Do not commit this file to version control.**
*   **`requirements.txt`:** Lists the required Python packages.

## Prerequisites

*   Python 3.8+
*   Google Cloud Project with Gmail API enabled
*   **`GEMINI_API_KEY`:** Environment variable for Google's Gemini API (optional)
*   **`DEEPINFRA_API_KEY`:** Environment variable for DeepInfra API (optional)

## Setup

1.  **Install Python:** Make sure you have Python 3.7 or later installed.

2.  **Create a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project.

3.  **Enable APIs:**
    *   In your project, enable the following APIs:
        *   Gmail API
        *   Generative Language API
    *   Search for each API in the "APIs & Services" section and enable it.

4.  **Create Credentials:**
    *   Go to "APIs & Services" -> "Credentials".
    *   Click "Create Credentials" -> "OAuth client ID".
    *   Choose "Desktop app" as the application type.
    *   Give it a name (e.g., "Email Classifier").
    *   Click "Create".
    *   Download the JSON file and save it as `credentials.json` in the project root.

5.  **Set up Gemini API Key:**
    *    Get an API key for the Gemini API. See [Google AI Studio documentation](https://ai.google.dev/tutorials/setup) for the most up-to-date instructions.
    *   Set the `GEMINI_API_KEY` environment variable:
        *   **Linux/macOS:**
            ```bash
            export GEMINI_API_KEY="your_api_key"
            ```
        *   **Windows (Command Prompt):**
            ```
            set GEMINI_API_KEY="your_api_key"
            ```
        *   **Windows (PowerShell):**
            ```powershell
            $env:GEMINI_API_KEY="your_api_key"
            ```
         *   **Important:** Replace `"your_api_key"` with your actual API key.

6.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

7.  **Customize `email_preferences.json`:**
    *   Create an `email_preferences.json` file based on the example provided.
    *   **Carefully customize the rules** to match your specific needs.

8.  **Create `email_analysis.txt`:**
    *   Create an `email_analysis.txt` file based on the example provided.
    *   This file contains the prompt for the Gemini API.

## Running the Scripts

1.  **Run `email_classifier.py` FIRST:**
    ```bash
    python email_classifier.py
    ```
    *   The first time you run it, you'll be guided through the Google OAuth authentication flow.
    *   The script will fetch unread emails, analyze them, and apply labels.
    *   It will create (or update) the `feedback.json` file with entries for each processed email, ready for feedback.

2.  **Run `process_feedback.py` SECOND:**
    ```bash
    python process_feedback.py
    ```
    *   This script will now **interactively prompt you for feedback** on each email processed by `email_classifier.py`.
    *   It uses the Gemini API to structure your natural language feedback into JSON.
    *   It analyzes the feedback and suggests changes to `email_preferences.json`.
    *   **Review the suggested changes carefully.**
    *   You can *optionally* uncomment the lines in `process_feedback.py` to automatically apply the changes, but **do this with caution**.

## Testing

1.  **Send Test Emails:** Send yourself a variety of test emails.

2.  **Run `email_classifier.py`:** Observe the output and check that labels are applied in Gmail.

3.  **Run `process_feedback.py`:** Provide feedback interactively when prompted.

4.  **Review Suggestions:** Check the suggested changes from `process_feedback.py`.

5.  **Iterate:** Repeat steps 1-4, refining your preferences and providing feedback, until the system performs as desired.

## Troubleshooting

*   **Authentication Errors:** Delete `gmail_token.json` from the config directory and try again. Ensure `credentials.json` in the project root is correct.
*   **Rate Limits:** The script respects Gmail API quotas. If you hit limits, wait and try again.
*   **Security:** Keep your `credentials.json` and API keys secure.

## Important Notes

*   **Rate Limits:** The Gmail API and Gemini API have rate limits.
*   **Cost:** Using the Gemini API may incur costs.
*   **Error Handling:** The scripts have basic error handling; consider adding more robust error handling for production use.
