"""Module for formatting files into Obsidian documentation."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

class ObsidianFormatter:
    """Formats files into Obsidian documentation with metadata and links."""
    
    def __init__(self, base_dir: str, analysis_dir: Optional[str] = None):
        self.base_dir = Path(base_dir)
        self.processed_files: Dict[str, Dict] = {}
        self.analysis_data: Dict = {}
        
        if analysis_dir:
            self.load_analysis_data(analysis_dir)
            
    def load_analysis_data(self, analysis_dir: str):
        """Load file analysis data from analysis_results.json."""
        analysis_path = Path(analysis_dir) / "analysis_results.json"
        if analysis_path.exists():
            with open(analysis_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Index by file path for quick lookup
                self.analysis_data = {
                    file['file_path']: file 
                    for file in data.get('files', [])
                }
                
    def get_file_analysis(self, file_path: str) -> Dict:
        """Get analysis data for a specific file."""
        return self.analysis_data.get(str(file_path), {})
        
    def format_file(self, file_path: str) -> str:
        """Format a single file into Obsidian documentation."""
        path = Path(file_path)
        stats = path.stat()
        
        # Extract metadata
        created = datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.fromtimestamp(stats.st_mtime)
        size = stats.st_size
        
        # Read original content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Get analysis data
        analysis = self.get_file_analysis(str(file_path))
        
        # Store metadata for linking
        self.processed_files[path.stem] = {
            'path': str(path),
            'title': path.stem,
            'created': created,
            'modified': modified,
            'size': size,
            'analysis': analysis
        }
        
        # Format analysis section
        analysis_section = ""
        if analysis:
            analysis_section = """
## File Analysis
### Technical Details
- **MIME Type**: `{mime_type}`
- **Content Hash**: `{hash}`
- **Is Binary**: {is_binary}

### Path Analysis
- **In Virtual Environment**: {is_venv}
- **In Git Repository**: {is_git}
- **Is Temporary File**: {is_temp}
- **Is Notebook**: {is_notebook}
- **Is LLM Related**: {is_llm}
- **Is Config File**: {is_config}
""".format(
                mime_type=analysis.get('mime_type', 'Unknown'),
                hash=analysis.get('content_hash', 'Unknown'),
                is_binary=analysis.get('is_binary', False),
                is_venv=analysis.get('metadata', {}).get('path_analysis', {}).get('is_venv', False),
                is_git=analysis.get('metadata', {}).get('path_analysis', {}).get('is_git', False),
                is_temp=analysis.get('metadata', {}).get('path_analysis', {}).get('is_temp', False),
                is_notebook=analysis.get('metadata', {}).get('path_analysis', {}).get('is_notebook', False),
                is_llm=analysis.get('metadata', {}).get('path_analysis', {}).get('is_llm_related', False),
                is_config=analysis.get('metadata', {}).get('path_analysis', {}).get('is_config', False)
            )
        
        # Format frontmatter
        frontmatter = f"""---
title: {path.stem}
created: {created.strftime('%Y-%m-%d %H:%M:%S')}
modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}
size: {size}
path: {file_path}
type: document
analyzed: {bool(analysis)}
---

# {path.stem}

## Metadata
- **Created**: {created.strftime('%Y-%m-%d %H:%M:%S')}
- **Modified**: {modified.strftime('%Y-%m-%d %H:%M:%S')}
- **Size**: {size} bytes
- **Path**: `{file_path}`

{analysis_section}
## Content

{content}

## Related Documents
"""
        return frontmatter
        
    def find_related_documents(self, file_path: str, max_related: int = 5) -> List[str]:
        """Find related documents based on name similarity and analysis data."""
        current = Path(file_path).stem.lower()
        current_analysis = self.get_file_analysis(str(file_path))
        
        # Score documents based on multiple factors
        scores = []
        current_words = set(current.split())
        
        for doc, meta in self.processed_files.items():
            if doc.lower() == current:
                continue
                
            score = 0
            doc_words = set(doc.lower().split())
            
            # Score based on common words in title
            common_words = len(current_words & doc_words)
            score += common_words * 2
            
            # Score based on similar metadata from analysis
            if current_analysis and meta.get('analysis'):
                # Same MIME type
                if current_analysis.get('mime_type') == meta['analysis'].get('mime_type'):
                    score += 1
                    
                # Similar path characteristics
                current_path = current_analysis.get('metadata', {}).get('path_analysis', {})
                doc_path = meta['analysis'].get('metadata', {}).get('path_analysis', {})
                
                for key in ['is_notebook', 'is_llm_related', 'is_config']:
                    if current_path.get(key) == doc_path.get(key) == True:
                        score += 1
            
            if score > 0:
                scores.append((score, doc, meta['path']))
                
        # Sort by score and take top N
        scores.sort(reverse=True)
        return scores[:max_related]
        
    def create_obsidian_docs(self, output_dir: str):
        """Create Obsidian docs for all files in base directory."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # First pass - format all files and collect metadata
        for file in self.base_dir.rglob('*.md'):
            if file.is_file():
                self.processed_files[file.stem] = {
                    'path': str(file),
                    'content': self.format_file(str(file))
                }
                
        # Second pass - add related documents
        for doc_name, meta in self.processed_files.items():
            related = self.find_related_documents(meta['path'])
            
            related_section = "\n### Related Documents\n"
            for score, related_name, related_path in related:
                related_section += f"- [[{related_name}]] (Relevance: {score}) - `{related_path}`\n"
                
            content = meta['content'] + related_section
            
            # Write to output directory
            output_file = output_path / f"{doc_name}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content) 