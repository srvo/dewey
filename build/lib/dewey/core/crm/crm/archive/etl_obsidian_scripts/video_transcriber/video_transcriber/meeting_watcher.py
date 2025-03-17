import os
from pathlib import Path
import re
import json
import shutil
from datetime import datetime
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('meeting_watcher.log'),
        logging.StreamHandler()
    ]
)

class MeetingProcessor:
    def __init__(self):
        # Base directories
        self.base_dir = Path("/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents")
        self.dev_dir = self.base_dir / "dev"
        
        # Input/Output directories
        self.zoom_dir = Path("/Users/srvo/Documents/Zoom")
        self.meetings_dir = self.dev_dir / "output/meetings"
        self.processing_dir = self.dev_dir / "input"
        self.people_dir = self.dev_dir / "output/people"
        self.transcripts_dir = self.dev_dir / "scripts/video_transcriber/transcriptions"
        
        # Template paths (in main Obsidian vault with ~ directory)
        self.template_path = Path("/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents/~/templates/zoom_meeting.md")
        self.person_template_path = Path("/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents/~/templates/Person.md")
        
        # Meeting info file
        self.meeting_info_path = self.dev_dir / "scripts/video_transcriber/video_transcriber/meeting_info.md"
        
        # Ensure output directories exist
        self.meetings_dir.mkdir(parents=True, exist_ok=True)
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        self.people_dir.mkdir(parents=True, exist_ok=True)
        
        self.deepinfra_api_key = "8XjDNKnJ7absujS4JNLn9aaIp6QtUtZE"
        self.deepinfra_api_url = "https://api.deepinfra.com/v1/openai/chat/completions"
        
    def parse_person_name(self, name_str: str) -> dict:
        """Parse a person's name and extract additional information"""
        # Remove any parenthetical information (like pronouns)
        pronouns = ""
        pronoun_match = re.search(r'\((.*?)\)', name_str)
        if pronoun_match:
            pronouns = pronoun_match.group(1)
            name_str = re.sub(r'\s*\(.*?\)', '', name_str)
            
        # Split name into parts
        name_parts = name_str.strip().split()
        if len(name_parts) >= 2:
            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])
        else:
            first_name = name_str.strip()
            last_name = ""
            
        return {
            'full_name': name_str.strip(),
            'first_name': first_name,
            'last_name': last_name,
            'pronouns': pronouns,
            'filename': re.sub(r'[^\w\s-]', '', name_str.strip()).replace(' ', '_'),
            'entity': '',  # Will be populated during review
            'status': ['lead']  # Default status for new contacts
        }
        
    def create_or_update_person_note(self, person_info: dict, meeting_info: dict = None) -> str:
        """Create or update a person note"""
        person_path = self.people_dir / f"{person_info['filename']}.md"
        now = datetime.now().isoformat()
        
        # Ensure people directory exists
        self.people_dir.mkdir(parents=True, exist_ok=True)
        
        if person_path.exists():
            # Read existing content
            content = person_path.read_text()
            
            # Parse YAML frontmatter
            try:
                # Find YAML section
                yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
                if yaml_match:
                    yaml_content = yaml_match.group(1)
                    # Update necessary fields
                    yaml_lines = yaml_content.split('\n')
                    updated_lines = []
                    modified_found = False
                    last_meeting_found = False
                    
                    # Keep track of existing fields
                    entity_found = False
                    status_found = False
                    
                    for line in yaml_lines:
                        if line.startswith('modified:'):
                            updated_lines.append(f'modified: {now}')
                            modified_found = True
                        elif line.startswith('last_meeting:'):
                            updated_lines.append(f'last_meeting: {meeting_info["date"]} {meeting_info["time"]}')
                            last_meeting_found = True
                        elif line.startswith('reviewed:'):
                            updated_lines.append('reviewed: false')
                        elif line.startswith('entity:'):
                            entity_found = True
                            updated_lines.append(line)  # Preserve existing entity
                        elif line.startswith('status:'):
                            status_found = True
                            updated_lines.append(line)  # Preserve existing status
                        else:
                            updated_lines.append(line)
                    
                    # Add missing fields
                    if not modified_found:
                        updated_lines.append(f'modified: {now}')
                    if not last_meeting_found:
                        updated_lines.append(f'last_meeting: {meeting_info["date"]} {meeting_info["time"]}')
                    if not entity_found:
                        updated_lines.append('entity: ')  # Empty entity field if not present
                    if not status_found:
                        updated_lines.append('status: [lead]')  # Default status if not present
                    
                    # Replace YAML section
                    new_yaml = '\n'.join(updated_lines)
                    new_content = f'---\n{new_yaml}\n---' + content[yaml_match.end():]
                    person_path.write_text(new_content)
                    logging.info(f"Updated person note at {person_path}")
            except Exception as e:
                logging.error(f"Error updating person note {person_path}: {str(e)}")
                
            return person_info['filename']
            
        # If file doesn't exist, create it
        if not self.person_template_path.exists():
            logging.error(f"Person template not found at {self.person_template_path}")
            return person_info['filename']
            
        template_content = self.person_template_path.read_text()
        
        # Replace template variables
        replacements = {
            'first_name:': f'first_name: {person_info["first_name"]}',
            'last_name:': f'last_name: {person_info["last_name"]}',
            'pronouns:': f'pronouns: {person_info["pronouns"]}',
            'aliases:': f'aliases: ["{person_info["full_name"]}"]',
            'entity:': f'entity: {person_info["entity"]}',
            'status:': f'status: {person_info["status"]}',
            'created:': f'created: {now}',
            'modified:': f'modified: {now}',
            'last_meeting:': f'last_meeting: {meeting_info["date"]} {meeting_info["time"]}',
            'reviewed:': 'reviewed: false',
            'review_note:': 'review_note: Auto-generated from Zoom meeting',
            '## {{Title}}': f'## {person_info["full_name"]}'
        }
        
        for old, new in replacements.items():
            template_content = template_content.replace(old, new)
            
        # Write person note
        person_path.write_text(template_content)
        logging.info(f"Created person note at {person_path}")
        
        return person_info['filename']
        
    def process_participants(self, meeting_info: dict) -> dict:
        """Process all participants and create person notes"""
        processed_participants = {'host': '', 'attendees': []}
        
        # Process host
        if meeting_info['participants']['host']:
            host_info = self.parse_person_name(meeting_info['participants']['host'])
            processed_participants['host'] = self.create_or_update_person_note(host_info, meeting_info)
            
        # Process attendees
        for attendee in meeting_info['participants']['attendees']:
            attendee_info = self.parse_person_name(attendee)
            processed_participants['attendees'].append(
                self.create_or_update_person_note(attendee_info, meeting_info)
            )
            
        return processed_participants
        
    def extract_meeting_info(self, audio_path: Path) -> dict:
        """Extract meeting information from the audio file's location"""
        meeting_dir = audio_path.parent
        
        # Extract date and meeting name
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', meeting_dir.name)
        date = date_match.group(1) if date_match else "Unknown"
        
        # Extract time from directory name
        time_match = re.search(r'\d{2}\.\d{2}\.\d{2}', meeting_dir.name)
        time = time_match.group(0).replace('.', ':') if time_match else "00:00:00"
        
        # Remove date/time prefix from meeting name
        meeting_name = re.sub(r'^\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2} ', '', meeting_dir.name)
        
        # Extract participant names and roles
        participants = {'host': '', 'attendees': []}
        if ' - ' in meeting_name:
            _, participant_part = meeting_name.split(' - ', 1)
            # First person listed is typically the host
            if ' and ' in participant_part:
                host, others = participant_part.split(' and ', 1)
                participants['host'] = host.strip()
                participants['attendees'] = [p.strip() for p in others.split(',')]
            else:
                participants['host'] = participant_part.strip()
        
        # Try to extract duration from audio file metadata if possible
        duration = "TBD"  # We can enhance this later with actual audio duration
        
        # Create initial meeting info
        meeting_info = {
            'date': date,
            'time': time,
            'meeting_name': meeting_name,
            'original_path': str(meeting_dir),
            'audio_id': re.search(r'audio(\d+)', audio_path.name).group(1),
            'timestamp': datetime.now().isoformat(),
            'participants': participants,
            'datetime': f"{date}T{time}",
            'duration': duration
        }
        
        # Process participants and create person notes
        processed_participants = self.process_participants(meeting_info)
        meeting_info['participants'] = processed_participants
        
        return meeting_info
    
    def create_meeting_note(self, meeting_info: dict, final_dir: Path, analysis: dict = None) -> None:
        """Create a meeting note from template"""
        if not self.template_path.exists():
            logging.error(f"Template not found at {self.template_path}")
            return
            
        # Read template
        template_content = self.template_path.read_text()
        
        # Calculate paths for files
        audio_path = self.processing_dir / f"audio{meeting_info['audio_id']}.m4a"
        transcript_path = final_dir / f"{meeting_info['date']}_{meeting_info['audio_id']}_transcript.md"
        
        # If analysis is provided, format the insights sections
        if analysis:
            key_points = "### Key Points\n" + "\n".join([f"- {theme}" for theme in analysis["key_themes"]])
            action_items = "### Action Items\n" + "\n".join([f"- [ ] {item}" for item in analysis["action_items"]])
            notes = "### Notes & Highlights\n#### Key Insights\n" + "\n".join([f"- {insight}" for insight in analysis["key_insights"]])
            questions = "#### Questions Raised\n" + "\n".join([f"- {q}" for q in analysis["interesting_questions"]])
            followups = "### Follow-up\n- **Next Steps**:\n" + "\n".join([f"  - {f}" for f in analysis["suggested_followups"]])
        else:
            key_points = "### Key Points\n- "
            action_items = "### Action Items\n- [ ] Review and annotate transcript\n- [ ] Follow up with participants"
            notes = "### Notes & Highlights\n```timestamp\n00:00 - Meeting start\n```"
            questions = "#### Questions Raised\n- "
            followups = "### Follow-up\n- **Next Steps**:  "

        # Replace template variables
        replacements = {
            'event-id:': f'event-id: {meeting_info["audio_id"]}',
            'type: meeting': 'type: meeting',
            'description:': f'description: Zoom recording of {meeting_info["meeting_name"]}',
            'menu:': f'menu: {meeting_info["datetime"]}',
            'aliases:': f'aliases: ["{meeting_info["meeting_name"]}"]',
            'meeting_date:': f'meeting_date: {meeting_info["date"]}',
            'duration:': f'duration: {meeting_info["duration"]}',
            'recording_path:': f'recording_path: {audio_path}',
            'transcript_path:': f'transcript_path: {transcript_path}',
            'created:': f'created: {datetime.now().isoformat()}',
            'modified:': f'modified: {datetime.now().isoformat()}',
            '## {{Title}}': f'## {meeting_info["meeting_name"]}',
            '### Meeting Details\n- **Date & Time**:': f'### Meeting Details\n- **Date & Time**: {meeting_info["date"]} {meeting_info["time"]}',
            '- **Duration**:': f'- **Duration**: {meeting_info["duration"]}',
            '- **Recording Location**:': f'- **Recording Location**: {audio_path}',
            '- **Transcript**:': f'- **Transcript**: {transcript_path}',
            '- **Host**:': f'- **Host**: [[{meeting_info["participants"]["host"]}]]',
            '  -': '\n'.join([f'  - [[{attendee}]]' for attendee in meeting_info["participants"]["attendees"]]) if meeting_info["participants"]["attendees"] else '  - ',
            '**Source Files**\n- Audio:': f'**Source Files**\n- Audio: {audio_path}',
            '- Transcript:': f'- Transcript: {transcript_path}',
            '### Key Points\n-': key_points,
            '### Action Items\n- [ ] Review': action_items,
            '### Notes & Highlights\n<!-- Timestamped': notes,
            '#### Questions Raised\n-': questions,
            '### Follow-up\n- **Next Steps**:': followups,
            '- [x] Audio Processed': self.get_processing_status(meeting_info),
            '#meeting #zoom': f'#meeting #zoom #{meeting_info["date"].replace("-", "")}'
        }
        
        for old, new in replacements.items():
            template_content = template_content.replace(old, new)
        
        # Write meeting note
        meeting_note_path = final_dir / f"{meeting_info['date']}_{meeting_info['audio_id']}_meeting.md"
        meeting_note_path.write_text(template_content)
        logging.info(f"Created/updated meeting note at {meeting_note_path}")

    def get_processing_status(self, meeting_info: dict) -> str:
        """Generate processing status checklist based on what's been completed"""
        status = []
        status.append("- [x] Audio Processed")  # Always true if we're processing
        status.append(f"- [{'x' if meeting_info.get('transcript_path') else ' '}] Transcript Generated")
        status.append(f"- [{'x' if meeting_info.get('analysis') else ' '}] Summary Created")
        status.append(f"- [{'x' if meeting_info.get('action_items') else ' '}] Action Items Extracted")
        status.append("- [ ] Follow-ups Scheduled")  # This would need manual verification
        return "\n".join(status)

    def create_meeting_structure(self, meeting_info: dict) -> Path:
        """Create the directory structure for the meeting"""
        date_dir = self.meetings_dir / meeting_info['date']
        meeting_dir = date_dir / meeting_info['meeting_name']
        meeting_dir.mkdir(parents=True, exist_ok=True)
        return meeting_dir
    
    def process_audio_file(self, audio_path: Path):
        """Process a new audio file"""
        try:
            # Extract meeting information
            meeting_info = self.extract_meeting_info(audio_path)
            logging.info(f"Processing {audio_path.name} from {meeting_info['meeting_name']}")
            
            # Create metadata file
            metadata_path = self.processing_dir / f"{audio_path.stem}_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(meeting_info, f, indent=2)
            
            # Move audio file to processing directory
            new_audio_path = self.processing_dir / audio_path.name
            shutil.move(str(audio_path), str(new_audio_path))
            
            # Create final directory structure
            final_dir = self.create_meeting_structure(meeting_info)
            
            # Create meeting note from template
            self.create_meeting_note(meeting_info, final_dir)
            
            logging.info(f"Moved {audio_path.name} to processing directory")
            logging.info(f"Created meeting directory at {final_dir}")
            
            return True
            
        except Exception as e:
            logging.error(f"Error processing {audio_path}: {str(e)}")
            return False

    def parse_meeting_info_file(self) -> dict:
        """Parse the meeting_info.md file into a structured format"""
        if not self.meeting_info_path.exists():
            logging.error(f"Meeting info file not found at {self.meeting_info_path}")
            return {}
            
        content = self.meeting_info_path.read_text()
        meetings = {}
        
        # Skip header lines and parse each meeting entry
        for line in content.split('\n')[3:]:  # Skip header and separator lines
            if '|' not in line:
                continue
                
            parts = [p.strip() for p in line.split('|')[1:-1]]  # Remove empty first/last cells
            if len(parts) == 4:  # audio_file, date, meeting_name, directory
                audio_id = re.search(r'audio(\d+)', parts[0]).group(1)
                meetings[audio_id] = {
                    'audio_file': parts[0],
                    'date': parts[1],
                    'meeting_name': parts[2],
                    'directory': parts[3]
                }
        
        return meetings

    def find_transcript(self, audio_id: str) -> Path:
        """Find the transcript file for a given audio ID"""
        transcript_pattern = f"audio{audio_id}_*.json"
        transcripts = list(self.transcripts_dir.glob(transcript_pattern))
        return transcripts[0] if transcripts else None

    def format_timestamp(self, seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def analyze_transcript(self, transcript_text: str) -> dict:
        """Analyze transcript using DeepInfra's API to extract insights"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepinfra_api_key}"
        }
        
        system_prompt = """You are an expert meeting analyst. Analyze the provided meeting transcript and return a JSON object with the following structure:
        {
            "key_themes": [list of main topics discussed],
            "interesting_questions": [important questions raised during the meeting],
            "action_items": [list of tasks or follow-ups mentioned],
            "key_insights": [important insights or decisions],
            "sentiment": "overall meeting tone/sentiment",
            "suggested_followups": [list of recommended next steps]
        }
        Be concise but insightful. Focus on extracting actionable information."""

        data = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript_text}
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(self.deepinfra_api_url, headers=headers, json=data)
            response.raise_for_status()
            analysis = response.json()["choices"][0]["message"]["content"]
            return json.loads(analysis)
        except Exception as e:
            logging.error(f"Error analyzing transcript: {str(e)}")
            return {
                "key_themes": ["Analysis failed"],
                "interesting_questions": [],
                "action_items": [],
                "key_insights": [],
                "sentiment": "unknown",
                "suggested_followups": ["Review transcript manually"]
            }

    def format_transcript(self, transcript_json: dict) -> str:
        """Convert JSON transcript to formatted markdown"""
        formatted_lines = ["# Transcript\n"]
        
        if not transcript_json.get("segments"):
            return "# Transcript\n\nNo transcript segments found."
            
        # Format transcript without extra newlines
        for segment in transcript_json["segments"]:
            start_time = self.format_timestamp(segment["start"])
            end_time = self.format_timestamp(segment["end"])
            text = segment["text"].strip()
            formatted_lines.append(f"[{start_time} - {end_time}] {text}")
        
        # Add analysis section
        transcript_text = " ".join([segment["text"] for segment in transcript_json["segments"]])
        analysis = self.analyze_transcript(transcript_text)
        
        formatted_lines.extend([
            "\n\n# Meeting Analysis\n",
            "## Key Themes",
            "- " + "\n- ".join(analysis["key_themes"]),
            "\n## Important Questions",
            "- " + "\n- ".join(analysis["interesting_questions"]),
            "\n## Action Items",
            "- " + "\n- ".join(analysis["action_items"]),
            "\n## Key Insights",
            "- " + "\n- ".join(analysis["key_insights"]),
            "\n## Overall Sentiment",
            analysis["sentiment"],
            "\n## Suggested Follow-ups",
            "- " + "\n- ".join(analysis["suggested_followups"])
        ])
            
        return "\n".join(formatted_lines)

    def process_existing_meetings(self):
        """Process existing meetings from meeting_info.md and transcripts"""
        meetings = self.parse_meeting_info_file()
        logging.info(f"Found {len(meetings)} meetings to process")
        
        for audio_id, meeting_data in meetings.items():
            try:
                # Find corresponding transcript
                transcript_path = self.find_transcript(audio_id)
                if not transcript_path:
                    logging.warning(f"No transcript found for audio{audio_id}")
                    continue
                
                # Read and parse JSON transcript
                with open(transcript_path, 'r') as f:
                    transcript_json = json.load(f)
                
                # Format transcript and analyze
                formatted_transcript = self.format_transcript(transcript_json)
                analysis = self.analyze_transcript(" ".join([segment["text"] for segment in transcript_json["segments"]]))
                
                # Extract time from directory name
                time_match = re.search(r'\d{2}\.\d{2}\.\d{2}', meeting_data['directory'])
                time = time_match.group(0).replace('.', ':') if time_match else "00:00:00"
                
                # Extract participant names
                meeting_name = meeting_data['meeting_name']
                participants = {'host': '', 'attendees': []}
                if ' - ' in meeting_name:
                    _, participant_part = meeting_name.split(' - ', 1)
                    if ' and ' in participant_part:
                        host, others = participant_part.split(' and ', 1)
                        participants['host'] = host.strip()
                        participants['attendees'] = [p.strip() for p in others.split(',')]
                    else:
                        participants['host'] = participant_part.strip()
                
                # Create meeting info structure
                meeting_info = {
                    'date': meeting_data['date'],
                    'time': time,
                    'meeting_name': meeting_name,
                    'original_path': meeting_data['directory'],
                    'audio_id': audio_id,
                    'timestamp': datetime.now().isoformat(),
                    'participants': participants,
                    'datetime': f"{meeting_data['date']}T{time}",
                    'duration': str(int(transcript_json.get('duration', 0))) + " seconds",
                    'transcript_path': str(transcript_path)
                }
                
                # Process participants and create person notes
                processed_participants = self.process_participants(meeting_info)
                meeting_info['participants'] = processed_participants
                
                # Create final directory structure
                final_dir = self.create_meeting_structure(meeting_info)
                
                # Create meeting note with analysis
                self.create_meeting_note(meeting_info, final_dir, analysis)
                
                # Write formatted transcript
                transcript_md_path = final_dir / f"{meeting_info['date']}_{meeting_info['audio_id']}_transcript.md"
                if not transcript_md_path.exists():
                    transcript_md_path.write_text(formatted_transcript)
                    logging.info(f"Created formatted transcript at {transcript_md_path}")
                
                logging.info(f"Processed meeting {meeting_name} from {meeting_data['date']}")
                
            except Exception as e:
                logging.error(f"Error processing meeting {audio_id}: {str(e)}")

class ZoomFolderHandler(FileSystemEventHandler):
    def __init__(self):
        self.processor = MeetingProcessor()
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        if file_path.suffix.lower() == '.m4a' and 'audio' in file_path.name:
            logging.info(f"New audio file detected: {file_path}")
            self.processor.process_audio_file(file_path)

def main():
    processor = MeetingProcessor()
    
    # First process existing meetings
    processor.process_existing_meetings()
    
    # Then start watching for new recordings
    logging.info("Started watching Zoom directory for new recordings...")
    
    class AudioHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory or not event.src_path.endswith('.m4a'):
                return
            processor.process_audio_file(Path(event.src_path))
    
    event_handler = AudioHandler()
    observer = Observer()
    observer.schedule(event_handler, str(processor.zoom_dir), recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main() 