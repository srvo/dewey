import os
import requests
import logging
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

# Load environment variables from .env
logger.debug("Loading environment variables")
load_dotenv('/Users/srvo/srvo_utils/.env')

API_KEY = os.getenv("DEEPINFRA_API_KEY")
if not API_KEY:
    logger.error("DEEPINFRA_API_KEY environment variable not found")
    raise ValueError("DEEPINFRA_API_KEY environment variable not found. Please check your .env file.")
else:
    logger.debug("Successfully loaded DEEPINFRA_API_KEY")

@dataclass
class TranscriptionResponse:
    text: str
    task: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[float] = None
    words: Optional[list] = None
    segments: Optional[list] = None

def transcribe_audio(
    file_path: str,
    model: str = "distil-whisper/distil-large-v3",
    language: Optional[str] = None,
    prompt: Optional[str] = None,
    response_format: str = "verbose_json",
    temperature: Optional[float] = None,
    timestamp_granularities: Optional[list] = None
) -> TranscriptionResponse:
    """
    Send the audio file to Deepinfra's transcription API.
    
    Args:
        file_path: Path to the audio file
        model: Model identifier, defaults to "distil-whisper/distil-large-v3"
        language: Optional ISO-639-1 language code
        prompt: Optional text to guide transcription
        response_format: One of "json", "text", "srt", "verbose_json", "vtt"
        temperature: Optional sampling temperature (0 to 1)
        timestamp_granularities: List of "word" and/or "segment" for timestamps
    
    Returns:
        TranscriptionResponse object containing the transcription data
    """
    logger.debug(f"Starting transcription for file: {file_path}")
    url = "https://api.deepinfra.com/v1/openai/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Prepare the multipart form data
    data = {
        "model": model,
        "response_format": response_format
    }
    
    if language:
        data["language"] = language
    if prompt:
        data["prompt"] = prompt
    if temperature is not None:
        data["temperature"] = str(temperature)
    
    # Handle timestamp granularities
    if timestamp_granularities:
        for granularity in timestamp_granularities:
            data[f"timestamp_granularities[]"] = granularity
    
    logger.debug(f"Request data prepared: {data}")
    
    try:
        # Open and send the file
        with open(file_path, "rb") as audio_file:
            files = {
                "file": (os.path.basename(file_path), audio_file, "audio/mp4")
            }
            
            logger.info(f"Sending request to Deepinfra API for {os.path.basename(file_path)}")
            response = requests.post(
                url,
                headers=headers,
                data=data,
                files=files,
                timeout=300  # 5 minute timeout
            )
            
            logger.debug(f"Received response with status {response.status_code}")
            response.raise_for_status()
            
            # Parse the response
            response_data = response.json()
            logger.debug(f"Response data: {response_data}")
            
            # Convert to TranscriptionResponse object
            return TranscriptionResponse(
                text=response_data["text"],
                task=response_data.get("task"),
                language=response_data.get("language"),
                duration=response_data.get("duration"),
                words=response_data.get("words"),
                segments=response_data.get("segments")
            )
            
    except requests.Timeout:
        logger.error(f"Request timed out after 300 seconds for {file_path}")
        raise
    except requests.RequestException as e:
        logger.error(f"API request failed: {str(e)}", exc_info=True)
        raise
    except KeyError as e:
        logger.error(f"Invalid API response format: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise
