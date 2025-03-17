#!/usr/bin/env python3

import os
import threading
import queue
import logging
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from pathlib import Path
import whisper
import subprocess
from tqdm import tqdm
from functools import lru_cache
import magic
import shutil
import urllib.parse

# Configuration
WEBDAV_URL = "https://nx61057.your-storageshare.de/remote.php/webdav"
WEBDAV_USER = 'sloane@ethicic.com'
WEBDAV_PASSWORD = '5cnYp-SQYgT-j8FST-jsxrT-rs3jy'
LOCAL_SYNC_DIR = '/opt/nextcloud-sync'
TRANSCRIPT_DIR = '/opt/meeting-transcripts'
TEMP_DIR = '/opt/temp-audio'
WHISPER_MODEL = "large"

# Create directories
os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs('/Data/scripts/logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Data/scripts/logs/nextcloud_sync.log'),
        logging.StreamHandler()
    ]
)

@lru_cache(maxsize=1)
def get_whisper_model():
    logging.info(f"Loading Whisper model: {WHISPER_MODEL}")
    return whisper.load_model(WHISPER_MODEL)

class NextcloudClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(WEBDAV_USER, WEBDAV_PASSWORD)
        self.session.verify = True
        
    def download_file(self, remote_path, local_path):
        """Download file from Nextcloud with proper WebDAV handling"""
        try:
            # Encode the path properly for WebDAV
            encoded_path = urllib.parse.quote(remote_path)
            url = f"{WEBDAV_URL}/{encoded_path}"
            
            # First check if file exists
            response = self.session.head(url)
            if response.status_code == 404:
                logging.error(f"File not found on server: {remote_path}")
                return False
                
            # Download file
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Save file
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            # Verify downloaded file
            if not os.path.exists(local_path):
                return False
                
            return True
            
        except Exception as e:
            logging.error(f"Download failed for {remote_path}: {str(e)}")
            return False

class MeetingProcessor(threading.Thread):
    def __init__(self, queue, pbar):
        threading.Thread.__init__(self)
        self.queue = queue
        self.pbar = pbar
        self.daemon = True
        self.nextcloud = NextcloudClient()
        logging.info(f"Started worker thread {threading.current_thread().name}")
        
    def process_file(self, file_info):
        file_path = file_info['local_path']
        
        # Check if file is valid audio
        mime = magic.Magic(mime=True)
        file_type = mime.from_file(file_path)
        
        if not file_type.startswith('audio/'):
            logging.info(f"Invalid file type ({file_type}), attempting re-download: {file_path}")
            if not self.nextcloud.download_file(file_info['path'], file_path):
                return None
                
            # Verify after download
            file_type = mime.from_file(file_path)
            if not file_type.startswith('audio/'):
                logging.error(f"File still invalid after download: {file_path}")
                return None
        
        # Process valid audio file
        try:
            temp_dir = os.path.join(TEMP_DIR, datetime.now().strftime('%Y%m%d_%H%M%S'))
            os.makedirs(temp_dir, exist_ok=True)
            wav_path = os.path.join(temp_dir, 'audio.wav')
            
            # Convert to WAV using sox
            cmd = [
                'sox',
                file_path,
                '-r', '16000',
                '-c', '1',
                '-b', '16',
                wav_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"Conversion failed for {file_path}: {result.stderr}")
                return None
                
            # Transcribe
            model = get_whisper_model()
            result = model.transcribe(wav_path)
            
            # Save transcript
            transcript_path = os.path.join(
                TRANSCRIPT_DIR,
                os.path.relpath(file_path, LOCAL_SYNC_DIR).replace('.mp3', '.txt')
            )
            os.makedirs(os.path.dirname(transcript_path), exist_ok=True)
            
            with open(transcript_path, 'w') as f:
                f.write(result['text'])
                
            return transcript_path
            
        except Exception as e:
            logging.error(f"Processing error for {file_path}: {str(e)}")
            return None
            
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def run(self):
        while True:
            try:
                file_info = self.queue.get()
                if file_info is None:
                    logging.info(f"Worker {threading.current_thread().name} shutting down")
                    break

                logging.info(f"Processing file: {file_info['local_path']}")
                transcript_path = self.process_file(file_info)
                
                if transcript_path:
                    logging.info(f"Successfully processed: {file_info['local_path']}")
                else:
                    logging.error(f"Failed to process: {file_info['local_path']}")
                
                self.pbar.update(1)
                self.queue.task_done()

            except Exception as e:
                logging.error(f"Thread error: {str(e)}")
                self.queue.task_done()

def find_local_meetings():
    """Find all MP3 files in the sync directory"""
    files = []
    try:
        for path in Path(LOCAL_SYNC_DIR).rglob('*.mp3'):
            logging.debug(f"Found file: {path}")
            relative_path = str(path).replace(LOCAL_SYNC_DIR, '').lstrip('/')
            files.append({
                'path': relative_path,
                'local_path': str(path),
                'size': path.stat().st_size
            })
        logging.info(f"Found {len(files)} files")
        for f in files[:5]:  # Log first 5 files for debugging
            logging.info(f"Sample file: {f}")
        return files
    except Exception as e:
        logging.error(f"Error finding files: {str(e)}")
        return []

def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/Data/scripts/logs/nextcloud_sync.log'),
            logging.StreamHandler()
        ]
    )

    # Create directories
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    # Find files to process
    files = find_local_meetings()
    logging.info(f"Found {len(files)} meeting recordings to process")
    
    if not files:
        logging.error("No files found to process!")
        return

    # Create progress bar
    pbar = tqdm(total=len(files), desc="Processing meetings")
    
    # Create queue and workers
    process_queue = queue.Queue()
    num_worker_threads = 2
    workers = []
    
    logging.info(f"Starting {num_worker_threads} worker threads")
    
    for i in range(num_worker_threads):
        worker = MeetingProcessor(process_queue, pbar)
        worker.start()
        workers.append(worker)
        logging.info(f"Started worker {i+1}")

    try:
        # Add work to the queue
        for file_info in files:
            logging.debug(f"Queueing file: {file_info['local_path']}")
            process_queue.put(file_info)
        
        # Wait for completion
        process_queue.join()
        logging.info("All files processed")
        
        # Stop workers
        for i in range(num_worker_threads):
            process_queue.put(None)
        for worker in workers:
            worker.join()
            
    except Exception as e:
        logging.error(f"Main thread error: {str(e)}")
    finally:
        pbar.close()
    
    logging.info("Meeting processing completed")

if __name__ == "__main__":
    main()
