"""Core functionality for transcript analysis and conversion."""
##TODO  update the logic to count the number of times word vomit like "like", "know" "no yeah" "just kind" "really" "um" and other filler words.
##TODO integrate a deep scrape of https://freemoneypodcast.com and the information currently available there also our youttube and generate an obsidian  markdown formatted table of all episodes
##  https://www.youtube.com/@FreeMoneyPod
##todo create a function to identify questions asked in the "dear ashby" segment of the the podcast as well as our answers. also please identify all gardening tips offered


import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime
import json
import re
import numpy as np
from collections import defaultdict
import requests
from bs4 import BeautifulSoup
import youtube_dl

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.metrics.pairwise import cosine_similarity
import spacy

from .config import Config  # Add import for Config class

@dataclass
class FillerWordAnalysis:
    """Analysis of filler words in transcript."""
    total_words: int
    filler_counts: Dict[str, int]
    filler_percentage: float
    common_patterns: List[str]

@dataclass
class PodcastEpisode:
    """Metadata for a podcast episode."""
    title: str
    date: datetime
    url: str
    description: str
    youtube_url: Optional[str] = None
    transcript_path: Optional[str] = None

@dataclass
class DearAshbySegment:
    """Analysis of a Dear Ashby segment."""
    question: str
    answer: str
    episode_title: str
    timestamp: Optional[str] = None

@dataclass
class GardeningTip:
    """Gardening tip from the podcast."""
    tip: str
    episode_title: str
    context: str
    timestamp: Optional[str] = None

@dataclass
class TranscriptMetadata:
    """Metadata for a transcript."""
    file_path: str
    title: str
    date: Optional[datetime]
    duration: Optional[float]
    speaker_count: int
    word_count: int
    topics: List[str]
    key_phrases: List[str]
    summary: Optional[str]
    cluster_id: Optional[int] = None
    source_type: str = "unknown"  # youtube, podcast, txt, etc.
    source_url: Optional[str] = None
    filler_analysis: Optional[FillerWordAnalysis] = None
    dear_ashby_segments: List[DearAshbySegment] = field(default_factory=list)
    gardening_tips: List[GardeningTip] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        if self.date:
            d['date'] = self.date.isoformat()
        return d
    
    def to_markdown_row(self) -> str:
        """Convert to markdown table row."""
        return f"| {self.title} | {self.date.strftime('%Y-%m-%d') if self.date else 'Unknown'} | {self.duration or 0:.1f} | {self.word_count} | {', '.join(self.topics[:3])} |"

class TopicAnalyzer:
    """Analyze topics and key phrases in text."""
    
    def __init__(self, num_topics: int = 10):
        """Initialize the analyzer."""
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.lda = LatentDirichletAllocation(
            n_components=num_topics,
            random_state=42,
            batch_size=128,
            learning_method='online'
        )
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            import os
            os.system("python -m spacy download en_core_web_sm")
            self.nlp = spacy.load("en_core_web_sm")
    
    def extract_key_phrases(self, text: str) -> List[str]:
        """Extract meaningful phrases using spaCy."""
        doc = self.nlp(text)
        phrases = []
        
        # Extract noun phrases
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) <= 3:  # Limit phrase length
                phrases.append(chunk.text.lower())
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['ORG', 'PERSON', 'PRODUCT', 'WORK_OF_ART']:
                phrases.append(ent.text.lower())
                
        return list(set(phrases))
    
    def get_topic_terms(self, feature_names: List[str], topic_idx: int, n_top: int = 10) -> List[str]:
        """Get top terms for a topic."""
        topic = self.lda.components_[topic_idx]
        return [feature_names[i] for i in topic.argsort()[:-n_top - 1:-1]]
    
    def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze a batch of texts for topics and key phrases."""
        # Transform texts to TF-IDF vectors
        vectors = self.vectorizer.fit_transform(texts)
        
        # Extract topics
        topic_distribution = self.lda.fit_transform(vectors)
        
        # Get feature names for interpretation
        feature_names = self.vectorizer.get_feature_names_out()
        
        # Extract topics and their terms
        topics = {}
        for idx in range(self.lda.n_components):
            topics[f"topic_{idx}"] = {
                'terms': self.get_topic_terms(feature_names, idx),
                'weight': float(topic_distribution[:, idx].mean())
            }
        
        # Extract key phrases for each document
        key_phrases = [self.extract_key_phrases(text) for text in texts]
        
        return {
            'topic_distribution': topic_distribution.tolist(),
            'topics': topics,
            'key_phrases': key_phrases
        }

class FillerWordAnalyzer:
    """Analyzes filler words and patterns in text."""
    
    FILLER_WORDS = {
        'like', 'you know', 'um', 'uh', 'er', 'ah', 'kind of', 'sort of',
        'basically', 'literally', 'actually', 'really', 'just', 'so',
        'no yeah', 'yeah no', 'i mean', 'right', 'well', 'just kind',
        'just like', 'kind like', 'sort like'
    }
    
    FILLER_PATTERNS = [
        r'\blike\b(?!\s+to\b)',  # "like" not followed by "to"
        r'\byou know\b',
        r'\bum+\b',
        r'\buh+\b',
        r'\bkind of\b',
        r'\bsort of\b',
        r'\bno yeah\b',
        r'\byeah no\b',
        r'\bjust kind\b'
    ]
    
    def __init__(self):
        self.pattern = re.compile('|'.join(self.FILLER_PATTERNS), re.IGNORECASE)
    
    def analyze(self, text: str) -> FillerWordAnalysis:
        """Analyze filler words in text."""
        words = text.split()
        total_words = len(words)
        
        # Count filler words
        filler_counts = defaultdict(int)
        for word in self.FILLER_WORDS:
            count = len(re.findall(r'\b' + re.escape(word) + r'\b', text.lower()))
            if count > 0:
                filler_counts[word] = count
        
        # Find common patterns
        matches = self.pattern.finditer(text.lower())
        patterns = [m.group() for m in matches]
        
        total_fillers = sum(filler_counts.values())
        filler_percentage = (total_fillers / total_words) * 100 if total_words > 0 else 0
        
        return FillerWordAnalysis(
            total_words=total_words,
            filler_counts=dict(filler_counts),
            filler_percentage=filler_percentage,
            common_patterns=patterns
        )

class PodcastScraper:
    """Scrapes Free Money podcast content."""
    
    def __init__(self):
        self.website_url = "https://freemoneypodcast.com"
        self.youtube_channel = "https://www.youtube.com/@FreeMoneyPod"
    
    def scrape_website(self) -> List[PodcastEpisode]:
        """Scrape podcast episodes from website."""
        episodes = []
        response = requests.get(self.website_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Implement website-specific scraping logic
        # This is a placeholder - needs actual implementation based on website structure
        for episode_elem in soup.find_all('div', class_='episode'):
            title = episode_elem.find('h2').text
            date_str = episode_elem.find('date').text
            url = episode_elem.find('a')['href']
            description = episode_elem.find('description').text
            
            episodes.append(PodcastEpisode(
                title=title,
                date=datetime.strptime(date_str, '%Y-%m-%d'),
                url=url,
                description=description
            ))
        
        return episodes
    
    def scrape_youtube(self) -> List[PodcastEpisode]:
        """Scrape episodes from YouTube channel."""
        episodes = []
        ydl_opts = {
            'extract_flat': True,
            'force_generic_extractor': True
        }
        
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            channel_data = ydl.extract_info(self.youtube_channel, download=False)
            for entry in channel_data.get('entries', []):
                episodes.append(PodcastEpisode(
                    title=entry['title'],
                    date=datetime.strptime(entry['upload_date'], '%Y%m%d'),
                    url=entry['webpage_url'],
                    description=entry.get('description', ''),
                    youtube_url=entry['url']
                ))
        
        return episodes

class SegmentAnalyzer:
    """Analyzes specific segments in transcripts."""
    
    def __init__(self):
        self.dear_ashby_pattern = re.compile(
            r'dear ashby[:\s]+(.*?)\?.*?(?:ashby|answer)[:\s]+(.*?)(?=\n\n|\Z)',
            re.IGNORECASE | re.DOTALL
        )
        self.gardening_pattern = re.compile(
            r'(?:gardening tip|garden tip|plant tip)[:\s]+(.*?)(?=\n\n|\Z)',
            re.IGNORECASE | re.DOTALL
        )
    
    def find_dear_ashby_segments(self, text: str, episode_title: str) -> List[DearAshbySegment]:
        """Find Dear Ashby segments in transcript."""
        segments = []
        for match in self.dear_ashby_pattern.finditer(text):
            question = match.group(1).strip()
            answer = match.group(2).strip()
            segments.append(DearAshbySegment(
                question=question,
                answer=answer,
                episode_title=episode_title
            ))
        return segments
    
    def find_gardening_tips(self, text: str, episode_title: str) -> List[GardeningTip]:
        """Find gardening tips in transcript."""
        tips = []
        for match in self.gardening_pattern.finditer(text):
            tip_text = match.group(1).strip()
            # Get some context (100 chars before and after)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].strip()
            
            tips.append(GardeningTip(
                tip=tip_text,
                episode_title=episode_title,
                context=context
            ))
        return tips

class TranscriptProcessor:
    """Process and analyze transcripts from various sources."""
    
    def __init__(self, config):
        """Initialize the processor."""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.topic_analyzer = TopicAnalyzer()
        self.output_dir = Path(config.output_dir)
        self.filler_analyzer = FillerWordAnalyzer()
        self.segment_analyzer = SegmentAnalyzer()
        self.podcast_scraper = PodcastScraper()
        
        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'topics').mkdir(exist_ok=True)
        (self.output_dir / 'summaries').mkdir(exist_ok=True)
        (self.output_dir / 'networks').mkdir(exist_ok=True)
        (self.output_dir / 'markdown').mkdir(exist_ok=True)
    
    def sanitize_filename(self, filename: str) -> str:
        """Convert a string to a valid filename."""
        # Replace problematic characters with underscores
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # Remove any leading/trailing periods or spaces
        safe_name = safe_name.strip('. ')
        # Ensure the filename isn't empty
        if not safe_name:
            safe_name = 'unnamed_transcript'
        return safe_name
    
    def load_transcript(self, file_path: Path) -> str:
        """Load and clean transcript text."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            return text
        except UnicodeDecodeError:
            # Try different encodings
            encodings = ['latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            raise
    
    def process_directory(self, input_dir: str):
        """Process all transcripts in a directory."""
        input_path = Path(input_dir)
        transcript_files = list(input_path.glob('*.txt'))
        
        if not transcript_files:
            self.logger.warning(f"No transcript files found in {input_dir}")
            return
        
        self.logger.info(f"Found {len(transcript_files)} transcript files")
        
        # Load all transcripts
        transcripts = []
        texts = []
        
        for file_path in transcript_files:
            try:
                text = self.load_transcript(file_path)
                texts.append(text)
                
                # Basic metadata extraction
                word_count = len(text.split())
                speaker_count = len(set(line.split(':')[0] for line in text.splitlines() if ':' in line))
                
                # Try to extract date from filename or content
                date_match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', file_path.stem)
                date = None
                if date_match:
                    try:
                        date = datetime.strptime(date_match.group(1).replace('_', '-'), '%Y-%m-%d')
                    except ValueError:
                        pass
                
                transcripts.append(TranscriptMetadata(
                    file_path=str(file_path),
                    title=file_path.stem,
                    date=date,
                    duration=None,
                    speaker_count=speaker_count,
                    word_count=word_count,
                    topics=[],
                    key_phrases=[],
                    summary=None,
                    source_type="txt"
                ))
            except Exception as e:
                self.logger.error(f"Error processing {file_path}: {str(e)}")
                continue
        
        if not transcripts:
            self.logger.error("No transcripts could be processed")
            return
        
        # Analyze topics and key phrases
        self.logger.info("Analyzing topics and key phrases...")
        analysis = self.topic_analyzer.analyze_batch(texts)
        
        # Update metadata with analysis results
        for idx, transcript in enumerate(transcripts):
            # Assign top 3 topics based on distribution
            topic_weights = analysis['topic_distribution'][idx]
            top_topic_indices = np.argsort(topic_weights)[-3:][::-1]
            transcript.topics = [
                analysis['topics'][f'topic_{i}']['terms'][0]
                for i in top_topic_indices
            ]
            transcript.key_phrases = analysis['key_phrases'][idx]
        
        # Calculate transcript similarities
        self.logger.info("Calculating transcript similarities...")
        vectorizer = TfidfVectorizer(max_features=1000)
        vectors = vectorizer.fit_transform(texts)
        similarities = cosine_similarity(vectors)
        
        # Save results
        self.save_results(transcripts, analysis, similarities)
    
    def save_results(self, transcripts: List[TranscriptMetadata], 
                    analysis: Dict[str, Any],
                    similarities: np.ndarray):
        """Save analysis results in various formats."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save transcript metadata as JSON
        metadata_file = self.output_dir / 'transcript_metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump([t.to_dict() for t in transcripts], f, indent=2)
        
        # Save topic analysis
        topic_file = self.output_dir / 'topics' / f'topic_analysis_{timestamp}.json'
        with open(topic_file, 'w') as f:
            json.dump(analysis['topics'], f, indent=2)
        
        # Save similarity network
        network_file = self.output_dir / 'networks' / f'transcript_network_{timestamp}.json'
        similarity_data = {
            'nodes': [t.title for t in transcripts],
            'edges': [
                {
                    'source': transcripts[i].title,
                    'target': transcripts[j].title,
                    'weight': float(similarities[i, j])
                }
                for i in range(len(transcripts))
                for j in range(i + 1, len(transcripts))
                if similarities[i, j] > 0.3  # Only save significant connections
            ]
        }
        with open(network_file, 'w') as f:
            json.dump(similarity_data, f, indent=2)
        
        # Generate Markdown summary
        summary_file = self.output_dir / 'summaries' / f'analysis_summary_{timestamp}.md'
        with open(summary_file, 'w') as f:
            f.write("# Transcript Analysis Summary\n\n")
            f.write(f"Analysis Date: {timestamp}\n\n")
            
            f.write("## Overview\n")
            f.write(f"- Total Transcripts: {len(transcripts)}\n")
            f.write(f"- Total Words: {sum(t.word_count for t in transcripts)}\n")
            f.write(f"- Average Speakers per Transcript: {sum(t.speaker_count for t in transcripts) / len(transcripts):.1f}\n\n")
            
            f.write("## Key Topics\n")
            for topic_id, topic_data in analysis['topics'].items():
                terms = ', '.join(topic_data['terms'][:5])
                weight = topic_data['weight']
                f.write(f"- {topic_id}: {terms} (weight: {weight:.3f})\n")
            
            f.write("\n## Transcript Table\n")
            f.write("| Title | Date | Duration | Words | Top Topics |\n")
            f.write("|-------|------|----------|-------|------------|\n")
            for transcript in sorted(transcripts, key=lambda x: x.date if x.date else datetime.max):
                f.write(transcript.to_markdown_row() + "\n")
            
            f.write("\n## Detailed Summaries\n")
            for transcript in transcripts:
                f.write(f"\n### {transcript.title}\n")
                f.write(f"- Words: {transcript.word_count}\n")
                f.write(f"- Speakers: {transcript.speaker_count}\n")
                f.write(f"- Key Topics: {', '.join(transcript.topics)}\n")
                f.write(f"- Key Phrases: {', '.join(transcript.key_phrases[:5])}\n")
        
        self.logger.info(f"Analysis results saved to {self.output_dir}")

class TranscriptAnalyzer:
    """Main class for transcript analysis."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.topic_analyzer = TopicAnalyzer()
        self.filler_analyzer = FillerWordAnalyzer()
        self.segment_analyzer = SegmentAnalyzer()
        self.podcast_scraper = PodcastScraper()
        self.processor = TranscriptProcessor(config)
        
        self.logger.info("TranscriptAnalyzer initialized")
        
    def analyze_transcript(self, text: str, metadata: TranscriptMetadata) -> TranscriptMetadata:
        """Analyze a single transcript."""
        # Add filler word analysis
        metadata.filler_analysis = self.filler_analyzer.analyze(text)
        
        # Add segment analysis
        metadata.dear_ashby_segments = self.segment_analyzer.find_dear_ashby_segments(
            text, metadata.title
        )
        metadata.gardening_tips = self.segment_analyzer.find_gardening_tips(
            text, metadata.title
        )
        
        return metadata
        
    def process_directory(self, input_dir: Path):
        """Process all transcripts in a directory."""
        self.processor.process_directory(str(input_dir))
        
        # Generate Obsidian-ready summaries
        obsidian_dir = self.config.output_dir / "obsidian_ready"
        obsidian_dir.mkdir(exist_ok=True)
        
        # Process each transcript file
        for transcript_file in Path(input_dir).glob("*.txt"):
            try:
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Create basic metadata
                metadata = TranscriptMetadata(
                    file_path=str(transcript_file),
                    title=transcript_file.stem,
                    date=None,  # Will be extracted from filename if available
                    duration=None,
                    speaker_count=len(set(line.split(':')[0] for line in text.splitlines() if ':' in line)),
                    word_count=len(text.split()),
                    topics=[],
                    key_phrases=[],
                    summary=None
                )
                
                # Analyze transcript
                metadata = self.analyze_transcript(text, metadata)
                
                # Generate Obsidian summary
                summary = self.generate_obsidian_summary(metadata)
                
                # Save to Obsidian-ready directory
                output_file = obsidian_dir / f"{transcript_file.stem}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(summary)
                    
            except Exception as e:
                self.logger.error(f"Error processing {transcript_file}: {str(e)}")
                continue
                
    def generate_obsidian_summary(self, metadata: TranscriptMetadata) -> str:
        """Generate Obsidian-formatted summary."""
        summary = f"""# {metadata.title}

## Metadata
- **Date**: {metadata.date.strftime('%Y-%m-%d') if metadata.date else 'Unknown'}
- **Duration**: {metadata.duration or 'Unknown'}
- **Speakers**: {metadata.speaker_count}
- **Word Count**: {metadata.word_count}
- **Source**: {metadata.source_type}
- **URL**: {metadata.source_url or 'N/A'}

## Topics
{chr(10).join(f'- {topic}' for topic in metadata.topics)}

## Key Phrases
{chr(10).join(f'- {phrase}' for phrase in metadata.key_phrases)}
"""
        
        if metadata.filler_analysis:
            summary += f"""
## Speech Pattern Analysis
- **Total Words**: {metadata.filler_analysis.total_words}
- **Filler Word Percentage**: {metadata.filler_analysis.filler_percentage:.1f}%

### Common Filler Words
{chr(10).join(f'- "{word}": {count} times' for word, count in metadata.filler_analysis.filler_counts.items())}
"""
        
        if metadata.dear_ashby_segments:
            summary += """
## Dear Ashby Segments
"""
            for segment in metadata.dear_ashby_segments:
                summary += f"""
### Q: {segment.question}
A: {segment.answer}
"""
        
        if metadata.gardening_tips:
            summary += """
## Gardening Tips
"""
            for tip in metadata.gardening_tips:
                summary += f"""
- {tip.tip}
  Context: {tip.context}
"""
        
        return summary

def main():
    """Main entry point."""
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting transcript analysis")
        cfg = Config()
        processor = TranscriptProcessor(cfg)
        processor.process_directory(cfg.input_dir)
        
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        raise

def setup_logging():
    """Set up logging configuration."""
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler) 