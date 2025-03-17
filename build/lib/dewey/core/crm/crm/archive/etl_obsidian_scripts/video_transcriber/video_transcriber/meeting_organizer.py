import os
import json
import shutil
import datetime
from pathlib import Path
import subprocess
import re
from typing import Dict, List, Optional
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meeting_organizer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MeetingOrganizer:
    def __init__(self):
        self.transcriptions_dir = Path("/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents/dev/scripts/video_transcriber/transcriptions")
        self.zoom_dir = Path("/Users/srvo/Documents/Zoom")
        self.output_dir = Path("/Volumes/back_marx/lake/meetings")
        self.compressed_dir = self.output_dir / "compressed"
        
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        self.compressed_dir.mkdir(parents=True, exist_ok=True)
        
    def find_original_audio_file(self, audio_id: str) -> Optional[Dict]:
        """Find the original audio file and its meeting info in the Zoom directory."""
        logger.debug(f"Looking for audio file with ID: {audio_id}")
        
        # Search through all date folders in Zoom directory
        for date_dir in self.zoom_dir.glob("*"):
            if not date_dir.is_dir():
                continue
                
            # Search through meeting folders
            for meeting_dir in date_dir.iterdir():
                if not meeting_dir.is_dir():
                    continue
                    
                # Look for matching audio file
                audio_file = next(meeting_dir.glob(f"audio{audio_id}.m4a"), None)
                if audio_file:
                    logger.info(f"Found original audio file: {audio_file}")
                    
                    # Get associated files
                    chat_file = meeting_dir / "chat.txt"
                    video_file = next(meeting_dir.glob("*.mp4"), None)
                    
                    # Extract meeting name from folder
                    meeting_name = meeting_dir.name
                    # Remove date and time info if present
                    meeting_name = re.sub(r'\d{4}-\d{2}-\d{2}.*$', '', meeting_name).strip()
                    
                    return {
                        "date": date_dir.name,
                        "meeting_name": meeting_name,
                        "directory": str(meeting_dir),
                        "chat_file": str(chat_file) if chat_file.exists() else None,
                        "video_file": str(video_file) if video_file else None,
                        "audio_file": str(audio_file)
                    }
                    
        logger.warning(f"Could not find original audio file with ID: {audio_id}")
        return None
        
    def compress_media(self, input_file: Path, output_dir: Path) -> Optional[Path]:
        """Compress video or audio file using ffmpeg."""
        if not input_file.exists():
            logger.error(f"Input file does not exist: {input_file}")
            return None
            
        output_file = output_dir / f"compressed_{input_file.name}"
        
        try:
            if input_file.suffix.lower() == '.mp4':
                # Compress video
                cmd = [
                    'ffmpeg', '-i', str(input_file),
                    '-c:v', 'libx264', '-crf', '28',
                    '-c:a', 'aac', '-b:a', '128k',
                    str(output_file)
                ]
            else:
                # Compress audio
                cmd = [
                    'ffmpeg', '-i', str(input_file),
                    '-c:a', 'aac', '-b:a', '128k',
                    str(output_file)
                ]
                
            subprocess.run(cmd, check=True, capture_output=True)
            return output_file
        except subprocess.CalledProcessError as e:
            logger.error(f"Error compressing file {input_file}: {e}")
            return None
            
    def process_transcription(self, trans_file: Path) -> Dict:
        """Process a transcription file and extract relevant information."""
        with open(trans_file, 'r') as f:
            trans_data = json.load(f)
            
        # Extract timestamp from filename
        timestamp_match = re.search(r'_(\d{8}_\d{6})\.json$', trans_file.name)
        if timestamp_match:
            timestamp = datetime.datetime.strptime(timestamp_match.group(1), "%Y%m%d_%H%M%S")
        else:
            timestamp = datetime.datetime.fromtimestamp(trans_file.stat().st_mtime)
            
        return {
            "timestamp": timestamp.isoformat(),
            "transcription": trans_data
        }
        
    def organize_meeting(self, trans_file: Path):
        """Organize a single meeting's data."""
        logger.info(f"Processing transcription file: {trans_file.name}")
        
        # Extract audio ID from transcription filename
        audio_id_match = re.search(r'audio(\d+)_', trans_file.name)
        if not audio_id_match:
            logger.error(f"Could not extract audio ID from filename: {trans_file.name}")
            return
            
        audio_id = audio_id_match.group(1)
        
        # Find original audio file and meeting info
        meeting_info = self.find_original_audio_file(audio_id)
        if not meeting_info:
            logger.warning(f"No meeting info found for audio ID: {audio_id}")
            return
            
        # Get transcription data
        trans_data = self.process_transcription(trans_file)
        timestamp = datetime.datetime.fromisoformat(trans_data["timestamp"])
        
        # Create output structure
        meeting_date = meeting_info["date"]
        meeting_time = timestamp.strftime("%H-%M-%S")
        meeting_name = meeting_info["meeting_name"]
        
        output_path = self.output_dir / meeting_date / f"{meeting_time}_{meeting_name}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Compress and move media files
        compressed_files = {}
        if meeting_info["video_file"]:
            compressed_video = self.compress_media(Path(meeting_info["video_file"]), self.compressed_dir)
            if compressed_video:
                compressed_files["video"] = str(compressed_video)
                
        if meeting_info["audio_file"]:
            compressed_audio = self.compress_media(Path(meeting_info["audio_file"]), self.compressed_dir)
            if compressed_audio:
                compressed_files["audio"] = str(compressed_audio)
                
        # Create comprehensive JSON
        meeting_data = {
            "meeting_name": meeting_name,
            "date": meeting_date,
            "time": meeting_time,
            "transcription": trans_data["transcription"],
            "compressed_media": compressed_files,
            "original_paths": {
                "video": meeting_info["video_file"],
                "audio": meeting_info["audio_file"],
                "chat": meeting_info["chat_file"]
            }
        }
        
        # Save comprehensive JSON
        output_json = output_path / "meeting_data.json"
        with open(output_json, 'w') as f:
            json.dump(meeting_data, f, indent=2)
            
        # Copy chat file if it exists
        if meeting_info["chat_file"]:
            chat_file = Path(meeting_info["chat_file"])
            if chat_file.exists():
                shutil.copy2(chat_file, output_path / "chat.txt")
                
        logger.info(f"Successfully organized meeting: {meeting_name} ({meeting_date} {meeting_time})")
        
    def process_all_transcriptions(self):
        """Process all transcription files."""
        self.setup_directories()
        
        for trans_file in self.transcriptions_dir.glob("*.json"):
            try:
                self.organize_meeting(trans_file)
            except Exception as e:
                logger.error(f"Error processing {trans_file}: {e}", exc_info=True)
                
def main():
    organizer = MeetingOrganizer()
    organizer.process_all_transcriptions()
    
if __name__ == "__main__":
    main() 