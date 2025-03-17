import requests
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json
from urllib.parse import urlparse, urljoin
import time
import xml.etree.ElementTree as ET
import re
import html

def sanitize_filename(filename):
    """Convert a string to a valid filename."""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove any non-ASCII characters
    filename = ''.join(char for char in filename if ord(char) < 128)
    # Limit length
    return filename[:200]

def download_episode(url, title, output_dir):
    """Download an episode from its URL."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Create sanitized filename from title
        safe_title = sanitize_filename(title)
        filename = os.path.join(output_dir, f"{safe_title}.mp3")
            
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return filename
    except Exception as e:
        print(f"Error downloading {url}: {str(e)}")
        return None

def is_podcast_episode(item, ns):
    """Determine if an item is a podcast episode."""
    # Check for audio enclosure
    enclosure = item.find('enclosure', ns)
    if enclosure is not None and enclosure.get('type', '').startswith('audio/'):
        return True
    return False

def clean_xml(content):
    """Clean XML content to handle potential parsing issues."""
    # Convert bytes to string if necessary
    if isinstance(content, bytes):
        content = content.decode('utf-8', errors='ignore')
    
    # Unescape HTML entities
    content = html.unescape(content)
    
    # Remove any invalid XML characters
    content = re.sub(u'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    return content

def analyze_podcast():
    # Create directories
    os.makedirs('episodes', exist_ok=True)
    os.makedirs('analysis', exist_ok=True)
    
    # Get the RSS feed
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get('https://api.substack.com/feed/podcast/11174/s/141478.rss', headers=headers)
        response.raise_for_status()
        
        # Clean and parse the XML
        clean_content = clean_xml(response.content)
        root = ET.fromstring(clean_content)
        
        # Find the namespace
        ns = {'': root.tag.split('}')[0].strip('{')} if '}' in root.tag else ''
        
        episodes = []
        
        # Find all items (episodes)
        for item in root.findall('.//item', ns):
            try:
                # Skip if not a podcast episode
                if not is_podcast_episode(item, ns):
                    continue
                    
                episode = {
                    'title': item.find('title', ns).text if item.find('title', ns) is not None else '',
                    'link': item.find('link', ns).text if item.find('link', ns) is not None else '',
                    'published': item.find('pubDate', ns).text if item.find('pubDate', ns) is not None else '',
                    'description': item.find('description', ns).text if item.find('description', ns) is not None else ''
                }
                
                # Find enclosure (audio file)
                enclosure = item.find('enclosure', ns)
                if enclosure is not None:
                    episode['audio_url'] = enclosure.get('url')
                    episode['audio_type'] = enclosure.get('type')
                    episode['audio_length'] = enclosure.get('length')
                
                episodes.append(episode)
            except Exception as e:
                print(f"Error processing episode: {str(e)}")
                continue
        
        # Save metadata as JSON
        with open('analysis/episodes_metadata.json', 'w') as f:
            json.dump(episodes, f, indent=2)
        
        # Download episodes
        print("\nDownloading episodes...")
        for episode in episodes:
            if 'audio_url' in episode and episode['audio_url']:
                print(f"Downloading: {episode['title']}")
                filename = download_episode(episode['audio_url'], episode['title'], 'episodes')
                if filename:
                    print(f"Downloaded to: {filename}")
            else:
                print(f"No audio URL found for: {episode['title']}")
        
        # Generate analysis summary
        summary = {
            'total_episodes': len(episodes),
            'episodes': [{
                'title': ep['title'],
                'published': ep['published'],
                'link': ep['link'],
                'has_audio': 'audio_url' in ep and ep['audio_url'] is not None,
                'audio_type': ep.get('audio_type', 'unknown'),
                'audio_length': ep.get('audio_length', 'unknown')
            } for ep in episodes]
        }
        
        with open('analysis/summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        print("\nAnalysis complete!")
        print(f"Total episodes found: {len(episodes)}")
        print("Metadata saved to: analysis/episodes_metadata.json")
        print("Summary saved to: analysis/summary.json")
        
        # Print a preview of episodes
        print("\nEpisode Preview:")
        for ep in episodes[:5]:  # Show first 5 episodes
            print(f"\nTitle: {ep['title']}")
            print(f"Published: {ep['published']}")
            print(f"Type: {ep.get('audio_type', 'unknown')}")
            print(f"Has audio: {'Yes' if 'audio_url' in ep and ep['audio_url'] else 'No'}")
    
    except Exception as e:
        print(f"Error: {str(e)}")
        # Save the raw response for debugging
        with open('analysis/debug_response.txt', 'wb') as f:
            f.write(response.content)
        print("Saved raw response to analysis/debug_response.txt for debugging")

if __name__ == "__main__":
    analyze_podcast()
