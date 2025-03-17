from .deepinfra_api import transcribe_audio, TranscriptionResponse
from typing import Optional, Dict, Any
import logging
import os
import sys
import json
from datetime import datetime
from tqdm import tqdm

def setup_logging():
    """Set up logging with both file and console output at DEBUG level."""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    # Create formatters and handlers
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler at DEBUG level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # File handler at DEBUG level
    file_handler = logging.FileHandler('transcriber.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Add both handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

logger = logging.getLogger(__name__)

class VideoTranscriber:
    def __init__(self, model_name: str = "distil-large-v3"):
        logger.debug(f"Initializing VideoTranscriber with model_name={model_name}")
        self.model_name = model_name
        
    def transcribe(self, audio_path: str) -> Optional[TranscriptionResponse]:
        """
        Transcribe an audio file using Distil-Whisper.
        
        Args:
            audio_path (str): Path to the audio file
            
        Returns:
            Optional[TranscriptionResponse]: Transcription data or None if transcription fails
        """
        logger.debug(f"Starting transcription of file: {audio_path}")
        try:
            logger.debug("Calling transcribe_audio with verbose_json format and word timestamps")
            result = transcribe_audio(
                file_path=audio_path,
                model=f"distil-whisper/{self.model_name}",
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
            logger.debug(f"Received transcription result: {result}")
            return result
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}", exc_info=True)
            return None

    def save_transcription(self, transcription: TranscriptionResponse, audio_path: str, output_dir: str = "transcriptions"):
        """Save transcription data to JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"{base_name}_{timestamp}.json")
        
        with open(output_file, 'w') as f:
            json.dump(vars(transcription), f, indent=2)
        
        logger.info(f"Saved transcription to {output_file}")
        return output_file

def format_transcription(transcription: TranscriptionResponse) -> str:
    """Format transcription data for display."""
    output = []
    output.append(f"Text: {transcription.text}")
    
    if transcription.language:
        output.append(f"Language: {transcription.language}")
    if transcription.duration:
        output.append(f"Duration: {transcription.duration:.2f} seconds")
    
    if transcription.segments:
        output.append("\nSegments:")
        for segment in transcription.segments:
            output.append(f"[{segment['start']:.2f}s - {segment['end']:.2f}s] {segment['text']}")
    
    return "\n".join(output)

def main():
    setup_logging()
    logger.debug("Starting video transcriber main function")
    
    if len(sys.argv) < 2:
        logger.error("No input path provided")
        print("Usage: video_transcriber <path_to_audio_file_or_directory>")
        return

    input_path = sys.argv[1]
    logger.debug(f"Processing input path: {input_path}")
    
    transcriber = VideoTranscriber()
    logger.debug("VideoTranscriber instance created")

    # Create output directory for transcriptions
    output_dir = "transcriptions"
    os.makedirs(output_dir, exist_ok=True)

    # If a directory is passed, process each audio file
    if os.path.isdir(input_path):
        logger.debug(f"Input path is a directory: {input_path}")
        audio_extensions = ('.mp3', '.m4a', '.wav', '.flac', '.ogg', '.mp4', '.mpeg', '.mpga', '.webm')
        logger.debug(f"Searching for files with extensions: {audio_extensions}")
        
        files = [os.path.join(input_path, f)
                 for f in os.listdir(input_path)
                 if f.lower().endswith(audio_extensions)]
        
        logger.info(f"Found {len(files)} audio files to process")
        
        if not files:
            logger.warning("No audio files found in the directory.")
            print("No audio files found in the directory.")
            return

        successful = 0
        failed = 0
        
        for file_path in tqdm(files, desc="Processing audio files", unit="file"):
            try:
                logger.info(f"Processing file: {os.path.basename(file_path)}")
                transcription = transcriber.transcribe(file_path)
                
                if transcription:
                    successful += 1
                    # Save transcription to file
                    output_file = transcriber.save_transcription(transcription, file_path, output_dir)
                    
                    # Display formatted output
                    print(f"\nTranscription for {os.path.basename(file_path)}:")
                    print(format_transcription(transcription))
                    print(f"Full transcription saved to: {output_file}")
                    print("-" * 80)
                else:
                    failed += 1
                    print(f"\nFailed to transcribe {os.path.basename(file_path)}")
                    
            except KeyboardInterrupt:
                logger.warning("Process interrupted by user")
                print("\nProcess interrupted by user")
                break
            except Exception as e:
                failed += 1
                logger.error(f"Error processing {file_path}: {str(e)}", exc_info=True)
                print(f"\nError processing {os.path.basename(file_path)}: {str(e)}")
                continue

        print(f"\nProcessing complete: {successful} successful, {failed} failed")
        print(f"Transcriptions saved in: {os.path.abspath(output_dir)}")
        logger.info(f"Processing complete: {successful} successful, {failed} failed")
                
    else:
        logger.debug(f"Input path is a file: {input_path}")
        transcription = transcriber.transcribe(input_path)
        
        if transcription:
            # Save transcription to file
            output_file = transcriber.save_transcription(transcription, input_path, output_dir)
            
            # Display formatted output
            print("\nTranscription:")
            print(format_transcription(transcription))
            print(f"\nFull transcription saved to: {output_file}")
        else:
            print("Failed to transcribe file")

if __name__ == "__main__":
    main()