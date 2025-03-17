import os
from pathlib import Path
import subprocess
import re

def find_meeting_info():
    # Run the shell command to find all audio files
    cmd = 'ls -1d "/Users/srvo/Documents/Zoom"/**/*audio*.m4a 2>/dev/null'
    try:
        output = subprocess.check_output(cmd, shell=True, text=True)
    except subprocess.CalledProcessError:
        return []
    
    results = []
    for line in output.splitlines():
        if not line.strip():
            continue
            
        file_path = Path(line)
        meeting_dir = file_path.parent
        
        # Extract date from the meeting directory name
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', meeting_dir.name)
        date = date_match.group(1) if date_match else "Unknown"
        
        # Extract meeting name without date/time prefix
        meeting_name = meeting_dir.name
        meeting_name = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2} ', '', meeting_name)
        
        # Create a shorter path by removing the common prefix
        short_path = str(meeting_dir).replace("/Users/srvo/Documents/Zoom/", "")
        
        results.append({
            'audio_file': file_path.name,
            'meeting_name': meeting_name,
            'date': date,
            'full_path': short_path
        })
    
    return results

def generate_markdown_table(results):
    markdown = "| Audio File | Date | Meeting Name | Directory |\n"
    markdown += "|------------|------|--------------|------------|\n"
    
    # Sort results by date and then by audio file name
    for result in sorted(results, key=lambda x: (x['date'], x['audio_file'])):
        markdown += f"| {result['audio_file']} | {result['date']} | {result['meeting_name']} | {result['full_path']} |\n"
    
    return markdown

def main():
    # Find all meeting info
    results = find_meeting_info()
    
    # Generate markdown table
    markdown_table = generate_markdown_table(results)
    
    # Write to file
    output_file = Path("/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents/dev/scripts/video_transcriber/video_transcriber/meeting_info.md")
    output_file.write_text(markdown_table)
    print(f"Meeting information saved to {output_file}")

if __name__ == "__main__":
    main() 