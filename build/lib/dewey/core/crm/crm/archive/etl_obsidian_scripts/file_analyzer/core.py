#!/usr/bin/env python3

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
import mimetypes
import magic  # for better file type detection
from collections import defaultdict
import boto3
from dotenv import load_dotenv
import logging
from typing import Dict, List, Any, Optional
import re
from dataclasses import dataclass, asdict
import numpy as np
from tqdm import tqdm
import argparse
import yaml
from collections import Counter
import psutil  # for memory tracking
import statistics
import signal
import sys

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class FileMetadata:
    file_path: str
    file_name: str
    extension: str
    mime_type: str
    size_bytes: int
    created_at: datetime
    last_modified: datetime
    content_hash: str
    is_binary: bool
    metadata: Dict[str, Any]  # For JSONB storage
    cluster_id: Optional[int] = None
    embedding_id: Optional[str] = None
    keywords: List[str] = None

    def to_dict(self):
        """Convert to dictionary with datetime objects converted to ISO format."""
        d = asdict(self)
        d['created_at'] = d['created_at'].isoformat()
        d['last_modified'] = d['last_modified'].isoformat()
        return d

class AnalysisResult:
    def __init__(self, run_id: str, timestamp: datetime):
        self.run_id = run_id
        self.timestamp = timestamp
        self.total_files = 0
        self.total_size = 0
        self.clusters = defaultdict(list)
        self.keyword_counts = defaultdict(int)
        self.bandwidth_stats = {}
        
    def to_dict(self):
        """Convert analysis result to dictionary format."""
        return {
            'run_id': self.run_id,
            'timestamp': self.timestamp.isoformat(),
            'total_files': self.total_files,
            'total_size': self.total_size,
            'cluster_summary': {
                name: {
                    'file_count': len(files),
                    'total_size': sum(f.size_bytes for f in files),
                    'extensions': list(set(f.extension for f in files))
                }
                for name, files in self.clusters.items()
            },
            'keyword_summary': dict(self.keyword_counts),
            'bandwidth_stats': self.bandwidth_stats
        }

class BandwidthTracker:
    def __init__(self):
        self.bytes_downloaded = 0
        self.files_processed = 0
        self.start_time = datetime.now()

    def add_bytes(self, bytes_count: int):
        self.bytes_downloaded += bytes_count
        self.files_processed += 1

    def get_stats(self) -> Dict[str, Any]:
        duration = (datetime.now() - self.start_time).total_seconds()
        return {
            'bytes_downloaded': self.bytes_downloaded,
            'mb_downloaded': self.bytes_downloaded / (1024 * 1024),
            'files_processed': self.files_processed,
            'duration_seconds': duration,
            'mb_per_second': (self.bytes_downloaded / (1024 * 1024)) / duration if duration > 0 else 0
        }

class ReflectionConfig:
    def __init__(self, config_dir: str = 'config/reflection_patterns'):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.patterns = self._load_patterns()
        self.learnings = {
            'directory_patterns': {},
            'skip_patterns': {},
            'performance_metrics': {},
            'false_positives': [],
            'optimization_history': []
        }
        
    def _load_patterns(self) -> dict:
        """Load existing patterns from config files."""
        patterns = {}
        if (self.config_dir / 'base_patterns.yaml').exists():
            with open(self.config_dir / 'base_patterns.yaml', 'r') as f:
                patterns = yaml.safe_load(f)
        return patterns
    
    def save_learning(self, run_id: str):
        """Save learnings from the current run."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        learning_file = self.config_dir / f'learning_{run_id}_{timestamp}.yaml'
        
        with open(learning_file, 'w') as f:
            yaml.dump(self.learnings, f, default_flow_style=False)
        
        # Update base patterns with new learnings
        self._update_base_patterns()
        
    def _update_base_patterns(self):
        """Update base patterns with validated learnings."""
        base_patterns = self._load_patterns()
        
        # Merge new learnings into base patterns
        for pattern_type, patterns in self.learnings['directory_patterns'].items():
            if pattern_type not in base_patterns:
                base_patterns[pattern_type] = {}
            
            for pattern, stats in patterns.items():
                if pattern not in base_patterns[pattern_type]:
                    base_patterns[pattern_type][pattern] = {
                        'confidence': 0,
                        'occurrences': 0,
                        'last_updated': None
                    }
                
                # Update pattern statistics
                base_stats = base_patterns[pattern_type][pattern]
                base_stats['occurrences'] += stats.get('occurrences', 0)
                base_stats['confidence'] = min(1.0, base_stats['confidence'] + 0.1)
                base_stats['last_updated'] = datetime.now().isoformat()
        
        # Save updated base patterns
        with open(self.config_dir / 'base_patterns.yaml', 'w') as f:
            yaml.dump(base_patterns, f, default_flow_style=False)
        
    def record_pattern(self, pattern_type: str, pattern: str, metadata: dict):
        """Record a new pattern observation."""
        if pattern_type not in self.learnings['directory_patterns']:
            self.learnings['directory_patterns'][pattern_type] = {}
            
        if pattern not in self.learnings['directory_patterns'][pattern_type]:
            self.learnings['directory_patterns'][pattern_type][pattern] = {
                'occurrences': 0,
                'examples': [],
                'performance_impact': {},
                'last_seen': None
            }
            
        pattern_data = self.learnings['directory_patterns'][pattern_type][pattern]
        pattern_data['occurrences'] += 1
        pattern_data['last_seen'] = datetime.now().isoformat()
        
        if metadata.get('path') and len(pattern_data['examples']) < 5:
            pattern_data['examples'].append(metadata['path'])
            
        if 'processing_time' in metadata:
            perf_data = pattern_data['performance_impact']
            if 'avg_processing_time' not in perf_data:
                perf_data['avg_processing_time'] = metadata['processing_time']
                perf_data['min_processing_time'] = metadata['processing_time']
                perf_data['max_processing_time'] = metadata['processing_time']
            else:
                perf_data['avg_processing_time'] = (
                    (perf_data['avg_processing_time'] * (pattern_data['occurrences'] - 1) +
                     metadata['processing_time']) / pattern_data['occurrences']
                )
                perf_data['min_processing_time'] = min(
                    perf_data['min_processing_time'],
                    metadata['processing_time']
                )
                perf_data['max_processing_time'] = max(
                    perf_data['max_processing_time'],
                    metadata['processing_time']
                )

    def record_false_positive(self, pattern_type: str, pattern: str, path: str, reason: str):
        """Record when a pattern incorrectly suggested skipping a file."""
        self.learnings['false_positives'].append({
            'pattern_type': pattern_type,
            'pattern': pattern,
            'path': path,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })

class ReflectionSystem:
    def __init__(self):
        self.pattern_cache = {}
        self.directory_stats = defaultdict(lambda: {
            'count': 0,
            'total_size': 0,
            'extensions': defaultdict(int),
            'processing_time': [],
            'skip_recommended': False,
            'skip_reason': None,
            'path_patterns': defaultdict(int)
        })
        self.start_time = datetime.now()
        self.config = ReflectionConfig()
        
        # Define strict patterns for skipping
        self.skip_patterns = {
            'cache': re.compile(r'^\.cache$|/\.cache/'),
            'temp': re.compile(r'^\.?temp$|^\.?tmp$'),
            'pycache': re.compile(r'__pycache__'),
            'node_modules': re.compile(r'^node_modules$'),
            'build_artifacts': re.compile(r'^(dist|build|target)$'),
        }
        
        # Define patterns that require additional validation
        self.cautious_patterns = {
            'venv': re.compile(r'venv|virtualenv'),
            'git': re.compile(r'\.git'),
            'env': re.compile(r'\.env'),
        }
        
        # Track pattern matches for analysis
        self.pattern_matches = defaultdict(list)

    def validate_venv_directory(self, path: str) -> bool:
        """Strictly validate if a directory is actually a virtual environment."""
        venv_indicators = [
            'pyvenv.cfg',
            'bin/python',
            'Scripts/python.exe',  # Windows
            'lib/python',
            'include/python',
        ]
        return any(
            (Path(path) / indicator).exists()
            for indicator in venv_indicators
        )
    
    def analyze_directory_patterns(self, path: str) -> Dict[str, bool]:
        """Analyze directory against known patterns with strict validation."""
        results = {
            'is_cache': bool(self.skip_patterns['cache'].search(path)),
            'is_temp': bool(self.skip_patterns['temp'].search(path)),
            'is_pycache': bool(self.skip_patterns['pycache'].search(path)),
            'is_node_modules': bool(self.skip_patterns['node_modules'].search(path)),
            'is_build': bool(self.skip_patterns['build_artifacts'].search(path)),
        }
        
        # Cautious pattern matching
        if self.cautious_patterns['venv'].search(path):
            results['is_venv'] = self.validate_venv_directory(path)
        else:
            results['is_venv'] = False
            
        return results
        
    def reflect_on_path(self, file_path: str, size: int, processing_time: float):
        """Analyze path patterns and collect statistics with strict validation."""
        path = Path(file_path)
        parent = str(path.parent)
        
        # Update directory statistics
        stats = self.directory_stats[parent]
        stats['count'] += 1
        stats['total_size'] += size
        stats['extensions'][path.suffix] += 1
        stats['processing_time'].append(processing_time)
        
        # Analyze patterns
        patterns = self.analyze_directory_patterns(parent)
        for pattern_name, matched in patterns.items():
            if matched:
                stats['path_patterns'][pattern_name] += 1
                self.pattern_matches[pattern_name].append(parent)
                
                # Record pattern in config
                self.config.record_pattern(
                    'directory_patterns',
                    pattern_name,
                    {
                        'path': parent,
                        'processing_time': processing_time,
                        'file_count': stats['count'],
                        'total_size': stats['total_size']
                    }
                )
        
        # Make skip recommendations based on strict criteria
        if stats['count'] > 100:  # Only consider directories with significant files
            # Check for definitive skip patterns
            if patterns['is_cache'] or patterns['is_pycache'] or patterns['is_temp']:
                stats['skip_recommended'] = True
                stats['skip_reason'] = "Confirmed cache/temp directory"
                return
                
            # Check processing time only for non-essential directories
            avg_time = np.mean(stats['processing_time'])
            if avg_time > 2.0 and not any([
                patterns['is_venv'],  # Don't skip actual venvs
                parent.endswith('src'),  # Don't skip source directories
                parent.endswith('lib'),  # Don't skip library directories
                'source' in parent.lower(),
                'data' in parent.lower()
            ]):
                stats['skip_recommended'] = True
                stats['skip_reason'] = f"High processing time ({avg_time:.2f}s/file) in non-essential directory"
    
    def should_skip_path(self, file_path: str) -> tuple[bool, Optional[str]]:
        """Determine if a path should be skipped based on strict pattern matching."""
        parent = str(Path(file_path).parent)
        stats = self.directory_stats[parent]
        
        # Never skip if we haven't processed enough files in this directory
        if stats['count'] < 50:
            return False, None
            
        return stats['skip_recommended'], stats['skip_reason']
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate a detailed report of optimization patterns and decisions."""
        total_time = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'total_directories': len(self.directory_stats),
            'pattern_matches': {
                pattern: {
                    'count': len(dirs),
                    'examples': dirs[:5]  # Show first 5 examples
                }
                for pattern, dirs in self.pattern_matches.items()
            },
            'directories_analyzed': {
                path: {
                    'files': stats['count'],
                    'total_size': stats['total_size'],
                    'avg_processing_time': np.mean(stats['processing_time']) if stats['processing_time'] else 0,
                    'extensions': dict(stats['extensions']),
                    'detected_patterns': dict(stats['path_patterns']),
                    'skip_recommended': stats['skip_recommended'],
                    'skip_reason': stats['skip_reason']
                }
                for path, stats in self.directory_stats.items()
                if stats['count'] > 50  # Only show significant directories
            },
            'optimization_recommendations': [
                {
                    'directory': path,
                    'reason': stats['skip_reason'],
                    'detected_patterns': dict(stats['path_patterns']),
                    'potential_time_saved': np.mean(stats['processing_time']) * stats['count']
                }
                for path, stats in self.directory_stats.items()
                if stats['skip_recommended']
            ],
            'analysis_duration': total_time
        }

    def save_reflection_results(self, run_id: str):
        """Save reflection results to config directory."""
        self.config.save_learning(run_id)

class StorageErrorTracker:
    def __init__(self):
        self.errors = defaultdict(list)
        self.error_patterns = defaultdict(int)
        self.segment_limits = defaultdict(int)
        
    def track_error(self, error_msg, file_path):
        error_type = self._classify_error(error_msg)
        self.errors[error_type].append({
            'file': file_path,
            'error': error_msg,
            'timestamp': datetime.now().isoformat()
        })
        self.error_patterns[error_type] += 1
        
        if 'SegmentsLimitExceeded' in error_msg:
            path_parts = Path(file_path).parts
            self.segment_limits[path_parts[0]] += 1
    
    def _classify_error(self, error_msg):
        if 'SegmentsLimitExceeded' in error_msg:
            return 'segment_limit'
        if "Can't follow symlink" in error_msg:
            return 'symlink'
        return 'other'
    
    def generate_report(self):
        return {
            'error_summary': dict(self.error_patterns),
            'segment_limits_by_dir': dict(self.segment_limits),
            'total_errors': sum(self.error_patterns.values()),
            'errors_by_type': {k: len(v) for k, v in self.errors.items()}
        }

@dataclass
class CheckpointData:
    last_processed_key: str
    processed_count: int
    total_size: int
    clusters: Dict[str, List[str]]  # Store only file paths instead of full metadata
    keyword_counts: Dict[str, int]
    bandwidth_stats: Dict[str, Any]
    timestamp: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

class AdaptiveAnalyzer:
    def __init__(self):
        self.pattern_success_rate = defaultdict(lambda: {'success': 0, 'failure': 0})
        self.processing_history = []
        self.batch_performance = []
        
    def learn_from_batch(self, batch_results):
        """Learn from batch processing results."""
        # Track pattern effectiveness
        for result in batch_results:
            if result.was_useful:
                self.pattern_success_rate[result.pattern]['success'] += 1
            else:
                self.pattern_success_rate[result.pattern]['failure'] += 1
        
        # Adjust batch size based on memory usage and speed
        current_memory = psutil.Process().memory_info().rss
        batch_time = sum(r.processing_time for r in batch_results)
        self.batch_performance.append({
            'size': len(batch_results),
            'time': batch_time,
            'memory': current_memory
        })
        
        # Optimize batch size
        self.adjust_batch_size()
        
        # Update pattern weights
        self.update_pattern_weights()
        
    def adjust_batch_size(self):
        """Dynamically adjust batch size based on performance."""
        recent_perf = self.batch_performance[-5:]  # Look at last 5 batches
        avg_time_per_file = statistics.mean(
            p['time'] / p['size'] for p in recent_perf
        )
        avg_memory_per_file = statistics.mean(
            p['memory'] / p['size'] for p in recent_perf
        )
        
        # Adjust batch size up or down based on metrics
        if avg_time_per_file < self.target_time and avg_memory_per_file < self.memory_limit:
            self.batch_size = min(self.batch_size * 1.2, self.max_batch_size)
        else:
            self.batch_size = max(self.batch_size * 0.8, self.min_batch_size)
            
    def update_pattern_weights(self):
        """Update pattern weights based on success rate."""
        for pattern, stats in self.pattern_success_rate.items():
            total = stats['success'] + stats['failure']
            if total > 100:  # Only update after sufficient data
                success_rate = stats['success'] / total
                self.pattern_weights[pattern] = success_rate
                
    def predict_skip_path(self, path: str) -> bool:
        """Use learned patterns to make skip decisions."""
        matching_patterns = self.find_matching_patterns(path)
        if not matching_patterns:
            return False
            
        # Use weighted voting based on pattern success rates
        weighted_votes = sum(
            self.pattern_weights[p] for p in matching_patterns
        )
        return weighted_votes > self.skip_threshold

class FileAnalyzer:
    def __init__(self, dry_run: bool = False, output_dir: str = None):
        """Initialize the analyzer with checkpointing capabilities."""
        self.dry_run = dry_run
        
        # Set up output directory structure
        script_name = Path(__file__).stem
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path(output_dir or f"output_{script_name}_{self.timestamp}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize analysis result with run ID
        self.run_id = f"analysis_{self.timestamp}"
        
        # Compile regex patterns for analysis
        self.patterns = {
            'venv': re.compile(r'(venv|env|\.env|virtualenv|\.venv)'),
            'git': re.compile(r'\.git'),
            'temp': re.compile(r'(\.tmp|\.temp|\.cache|__pycache__)'),
            'notebook': re.compile(r'\.ipynb$'),
            'llm_conversation': re.compile(r'(conversation|chat|prompt|completion|\.prompt|\.chat)'),
            'config': re.compile(r'(\.config|\.cfg|\.ini|\.env|\.yaml|\.yml)'),
            'data': re.compile(r'\.(csv|json|parquet|avro|orc|jsonl)$'),
            'code': re.compile(r'\.(py|js|ts|rs|go|c|cpp|h|hpp|java|rb|php)$')
        }
        
        # Initialize text analysis
        self.min_keyword_length = 4
        self.stop_words = {'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i', 
                          'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at'}
        
        # Progress tracking
        self.progress_file = self.output_dir / 'progress.json'
        self.last_save_time = datetime.now()
        self.save_interval = 60  # Save progress every 60 seconds
        
        # Results storage
        self.results = {
            'files': [],
            'clusters': defaultdict(list),
            'keywords': defaultdict(int),
            'total_size': 0,
            'file_types': defaultdict(int),
            'start_time': datetime.now().isoformat()
        }
        
        # Initialize shutdown flag
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals gracefully."""
        if self.shutdown_requested:
            logger.warning("Forced shutdown requested. Exiting immediately.")
            sys.exit(1)
            
        logger.info("Shutdown requested. Cleaning up...")
        self.shutdown_requested = True
        self._save_results()

    def _save_results(self):
        """Save current analysis results."""
        self.results['end_time'] = datetime.now().isoformat()
        self.results['duration'] = (datetime.now() - datetime.fromisoformat(self.results['start_time'])).total_seconds()
        
        # Save detailed results
        with open(self.output_dir / 'analysis_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
            
        # Save summary
        summary = {
            'total_files': len(self.results['files']),
            'total_size_mb': self.results['total_size'] / (1024 * 1024),
            'file_types': dict(self.results['file_types']),
            'top_keywords': dict(sorted(self.results['keywords'].items(), key=lambda x: x[1], reverse=True)[:20]),
            'duration_seconds': self.results['duration']
        }
        
        with open(self.output_dir / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

    def get_file_metadata(self, file_path: Path) -> FileMetadata:
        """Extract and analyze file metadata from a local file."""
        try:
            stat = file_path.stat()
            
            # Read first 1KB for type detection
            content = None
            is_binary = True
            try:
                with open(file_path, 'rb') as f:
                    content = f.read(1024)
                is_binary = not self._is_text(content)
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
            
            # Calculate file hash
            content_hash = ''
            try:
                with open(file_path, 'rb') as f:
                    content_hash = hashlib.md5(f.read()).hexdigest()
            except Exception as e:
                logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            
            # Analyze path and extract keywords
            path_analysis = self.analyze_path(str(file_path))
            
            return FileMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                extension=file_path.suffix.lower(),
                mime_type=self.get_mime_type(str(file_path), content),
                size_bytes=stat.st_size,
                created_at=datetime.fromtimestamp(stat.st_ctime),
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                content_hash=content_hash,
                is_binary=is_binary,
                metadata={
                    'path_analysis': path_analysis,
                },
                keywords=path_analysis['keywords']
            )
            
        except Exception as e:
            logger.error(f"Error getting metadata for {file_path}: {str(e)}")
            return None

    def analyze_directory(self, directory_path: str) -> None:
        """Analyze all files in a directory recursively."""
        logger.info(f"Starting analysis of directory: {directory_path}")
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return
        
        try:
            # Get total number of files for progress bar
            total_files = sum(1 for _ in directory.rglob('*') if _.is_file())
            
            with tqdm(total=total_files, desc="Analyzing files") as progress:
                for file_path in directory.rglob('*'):
                    if self.shutdown_requested:
                        break
                        
                    if not file_path.is_file():
                        continue
                        
                    try:
                        metadata = self.get_file_metadata(file_path)
                        if metadata:
                            self._process_file_metadata(metadata)
                        progress.update(1)
                        
                        # Print stats periodically
                        if len(self.results['files']) % 100 == 0:
                            memory = psutil.Process().memory_info().rss / 1024 / 1024
                            logger.info(
                                f"Progress: {len(self.results['files'])} files, "
                                f"Memory: {memory:.2f} MB, "
                                f"Total Size: {self.results['total_size'] / (1024*1024):.2f} MB"
                            )
                            
                    except Exception as e:
                        logger.error(f"Error analyzing file {file_path}: {str(e)}")
                        progress.update(1)
                        
            # Save final results
            self._save_results()
            
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            self._save_results()
            raise

    def _process_file_metadata(self, metadata: FileMetadata):
        """Process and store file metadata."""
        self.results['files'].append(metadata.to_dict())
        self.results['total_size'] += metadata.size_bytes
        self.results['file_types'][metadata.extension] += 1
        
        # Update keywords
        for keyword in metadata.keywords:
            self.results['keywords'][keyword] += 1
        
        # Cluster the file
        cluster = self._determine_cluster(metadata.metadata['path_analysis'])
        self.results['clusters'][cluster].append(metadata.to_dict())

    def _determine_cluster(self, path_analysis: Dict) -> str:
        """Determine which cluster a file belongs to."""
        if path_analysis['is_venv']:
            return 'virtual_environments'
        elif path_analysis['is_git']:
            return 'git_files'
        elif path_analysis['is_temp']:
            return 'temporary_files'
        elif path_analysis['is_llm_related']:
            return 'llm_conversations'
        elif path_analysis['is_notebook']:
            return 'notebooks'
        elif path_analysis['is_config']:
            return 'configuration'
        elif path_analysis['is_data']:
            return 'data_files'
        elif path_analysis['is_code']:
            return 'source_code'
        else:
            return 'other'

    def analyze_path(self, file_path: str) -> Dict[str, Any]:
        """Analyze file path for patterns and extract meaningful keywords."""
        path = Path(file_path)
        path_parts = list(path.parts)
        
        # Extract keywords from path parts and filename
        all_text = ' '.join([p for p in path_parts if not p.startswith('.')])
        keywords = self.extract_keywords(all_text)
        
        return {
            'is_venv': bool(self.patterns['venv'].search(file_path)),
            'is_git': bool(self.patterns['git'].search(file_path)),
            'is_temp': bool(self.patterns['temp'].search(file_path)),
            'is_notebook': bool(self.patterns['notebook'].search(file_path)),
            'is_llm_related': bool(self.patterns['llm_conversation'].search(file_path)),
            'is_config': bool(self.patterns['config'].search(file_path)),
            'is_data': bool(self.patterns['data'].search(file_path)),
            'is_code': bool(self.patterns['code'].search(file_path)),
            'depth': len(path_parts),
            'parent_dirs': path_parts[:-1],
            'keywords': keywords
        }

    def extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words 
                   if len(word) >= self.min_keyword_length 
                   and word not in self.stop_words
                   and not word.isnumeric()]
        return list(set(keywords))  # Remove duplicates

    def get_mime_type(self, file_path: str, content: Optional[bytes] = None) -> str:
        """Get MIME type using both mimetypes and python-magic."""
        mime_type = mimetypes.guess_type(file_path)[0]
        if not mime_type and content:
            try:
                mime_type = magic.from_buffer(content, mime=True)
            except:
                mime_type = 'application/octet-stream'
        return mime_type or 'application/octet-stream'

    def _is_text(self, content: bytes) -> bool:
        """Determine if content is text by checking for binary characters."""
        if not content:
            return True
            
        # Check if file starts with known binary signatures
        if content.startswith(b'%PDF-'):  # PDF
            return False
        if content.startswith(b'PK'):  # ZIP
            return False
            
        # Look for null bytes and other binary characters
        textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
        return bool(content.translate(None, textchars))

def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(description='Analyze files in a directory')
    parser.add_argument('directory', help='Directory to analyze')
    parser.add_argument('--dry-run', action='store_true', help='Only list files, do not read content')
    parser.add_argument('--output-dir', help='Base directory for analysis output')
    args = parser.parse_args()
    
    analyzer = FileAnalyzer(dry_run=args.dry_run, output_dir=args.output_dir)
    
    try:
        # Analyze directory
        logger.info("Starting file analysis...")
        analyzer.analyze_directory(args.directory)
        
        if not analyzer.shutdown_requested:
            # Print summary
            print("\n=== Analysis Results ===")
            print(f"\nTotal Files: {len(analyzer.results['files'])}")
            print(f"Total Size: {analyzer.results['total_size'] / (1024*1024*1024):.2f} GB")
            
            print("\nFile Types:")
            for ext, count in sorted(analyzer.results['file_types'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {ext or 'no extension'}: {count} files")
            
            print("\nTop 20 Keywords:")
            for keyword, count in sorted(analyzer.results['keywords'].items(), key=lambda x: x[1], reverse=True)[:20]:
                print(f"  {keyword}: {count} occurrences")
                
            print(f"\nDetailed results saved to: {analyzer.output_dir}")
            
        else:
            logger.info("Analysis stopped gracefully. Check results in output directory.")
            
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user.")
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise

if __name__ == "__main__":
    main() 