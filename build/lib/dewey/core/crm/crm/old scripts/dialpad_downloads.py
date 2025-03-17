import pandas as pd
import requests
import os
from urllib.parse import urlparse
from datetime import datetime
import time

def clean_filename(filename):
    """Remove invalid characters from filename"""
    return "".join([c for c in filename if c.isalpha() or c.isdigit() or c in ' -_.']).rstrip()

def download_file(url, output_path):
    """Download a file with progress indication"""
    if not url or url.isspace():
        return False
        
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024
        downloaded = 0
        
        with open(output_path, 'wb') as f:
            for data in response.iter_content(block_size):
                downloaded += len(data)
                f.write(data)
                
                # Print progress
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    print(f"\rDownloading: {percent:.1f}%", end='')
                    
        print(f"\nSaved: {output_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return False

def main():
    # Create base output directory
    base_dir = "dialpad_downloads"
    os.makedirs(base_dir, exist_ok=True)
    
    # Read CSV
    df = pd.read_csv('scripts/csvs/Dialpad Call History - dpm_sloane@ethicic.com_call_history.csv')
    
    # Process each row
    for index, row in df.iterrows():
        try:
            # Get date and create formatted directory name
            date_str = row['start_time (in US/Mountain)'].split(' ')[0]  # Get just the date part
            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
            date_formatted = date_obj.strftime('%Y-%m-%d')
            
            # Create directory for this call
            call_dir = os.path.join(base_dir, f"{date_formatted}_{clean_filename(row['title'])}")
            os.makedirs(call_dir, exist_ok=True)
            
            # Download MP3
            if pd.notna(row['recordings (audio)']):
                mp3_path = os.path.join(call_dir, "audio.mp3")
                print(f"\nDownloading MP3 for {date_formatted}...")
                download_file(row['recordings (audio)'], mp3_path)
            
            # Download MP4 if available
            if pd.notna(row['recordings (video)']):
                mp4_path = os.path.join(call_dir, "video.mp4")
                print(f"Downloading MP4 for {date_formatted}...")
                download_file(row['recordings (video)'], mp4_path)
            
            # Download Chat if available
            if pd.notna(row['chat']):
                chat_path = os.path.join(call_dir, "chat.txt")
                print(f"Downloading Chat for {date_formatted}...")
                download_file(row['chat'], chat_path)
            
            # Sleep briefly to avoid overwhelming the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing row {index}: {str(e)}")
            continue

if __name__ == "__main__":
    main()
