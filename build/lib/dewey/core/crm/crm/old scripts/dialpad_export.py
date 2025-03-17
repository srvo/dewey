import os
from pathlib import Path
import requests
import pandas as pd
from tqdm import tqdm
import subprocess

def setup_session():
    """Create authenticated session for Dialpad"""
    session = requests.Session()
    cookies_str = "dp_mkt_lead_source=Website; optimizelyEndUserId=oeu1731736857211r0.393609677714428; _biz_uid=db3c9d6ebe414f05c1af0a81f168c7ff; _gcl_au=1.1.1740596618.1731736857; AMP_MKTG_0fd3be711d=JTdCJTdE; _ga=GA1.2.895686130.1731736857;"
    
    # Add more comprehensive headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Origin': 'https://meetings.dialpad.com',
        'Referer': 'https://meetings.dialpad.com/',
        'Cookie': cookies_str,
        'Accept': '*/*',
        'Connection': 'keep-alive',
        'Authorization': 'Bearer YOUR_TOKEN_HERE'  # We might need this
    })
    return session

def download_with_progress(url, output_path, session):
    """Download file with progress bar"""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        urls = url.split(';')
        success = False
        
        for i, single_url in enumerate(urls):
            single_url = single_url.strip()
            if not single_url:
                continue
                
            try:
                # First make a HEAD request to check content size
                head_response = session.head(single_url)
                expected_size = int(head_response.headers.get('content-length', 0))
                
                if expected_size < 100000:  # Less than 100KB is suspicious
                    print(f"Warning: File seems too small ({expected_size} bytes)")
                    continue
                
                response = session.get(single_url, stream=True)
                response.raise_for_status()
                
                # Print response headers for debugging
                print(f"\nResponse headers for {single_url}:")
                for key, value in response.headers.items():
                    print(f"{key}: {value}")
                
                current_output = output_path if i == 0 else output_path.with_stem(f"{output_path.stem}_{i+1}")
                
                with open(current_output, 'wb') as f:
                    with tqdm(total=expected_size, unit='B', unit_scale=True, desc=current_output.name) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                
                # Verify file size after download
                if os.path.getsize(current_output) < 100000:
                    print(f"Warning: Downloaded file is too small: {os.path.getsize(current_output)} bytes")
                    os.remove(current_output)
                    continue
                    
                success = True
            except requests.exceptions.RequestException as e:
                print(f"Error downloading {single_url}: {e}")
                print(f"Response status code: {getattr(e.response, 'status_code', 'N/A')}")
                print(f"Response text: {getattr(e.response, 'text', 'N/A')}")
                continue
        return success
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def main():
    # Create directories if they don't exist
    temp_dir = Path("/root/dialpad_processing/temp_downloads")
    output_dir = Path("/root/dialpad_processing/processed_audio")
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read CSV file
    df = pd.read_csv('Data/scripts/csvs/processed/Dialpad Call History - dpm_sloane@ethicic.com_call_history.csv')
    
    # Setup session
    session = setup_session()
    
    # Track progress
    successful = []
    failed = []
    
    print(f"\nFound {len(df)} Dialpad recordings\n")
    
    # Process each recording
    for index, row in df.iterrows():
        date = row['start_time (in US/Mountain)'].split()[0].replace('/', '-')
        title = row['title']
        print(f"\nProcessing {index+1}/{len(df)}: {date} - {title}")
        
        try:
            # Process audio recordings
            if pd.notna(row['recordings (audio)']):
                audio_urls = row['recordings (audio)']
                audio_path = temp_dir / f"{date}_{title.replace('/', '_')}.mp3"
                if download_with_progress(audio_urls, audio_path, session):
                    successful.append(f"{date} - {title} (audio)")
                else:
                    failed.append(f"{date} - {title} (audio)")
            
            # Process video recordings
            if pd.notna(row['recordings (video)']):
                video_urls = row['recordings (video)']
                video_path = temp_dir / f"{date}_{title.replace('/', '_')}.mp4"
                if download_with_progress(video_urls, video_path, session):
                    successful.append(f"{date} - {title} (video)")
                else:
                    failed.append(f"{date} - {title} (video)")
                    
        except Exception as e:
            print(f"Error processing {title}: {e}")
            failed.append(f"{date} - {title} (error: {str(e)})")
            continue
    
    # Print summary
    print("\nProcessing Complete!")
    print(f"Successfully processed: {len(successful)} files")
    print(f"Failed to process: {len(failed)} files")
    
    if failed:
        print("\nFailed files:")
        for f in failed:
            print(f"- {f}")

if __name__ == "__main__":
    main()