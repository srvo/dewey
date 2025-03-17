#!/usr/bin/env python3
"""
JSON Analysis Script

This script analyzes JSON files from a specified directory, performing:
1. Pattern detection and clustering
2. Relationship mapping between files
3. Detailed statistical analysis
4. Structured output for Obsidian integration
"""

import os
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Set, Any, Optional

class AnalysisFile:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.content: Dict = {}
        self.metadata: Dict = {}
        self.file_type: str = ""
        self.relationships: Set[str] = set()
        self.key_patterns: Set[str] = set()
        
    def load(self) -> bool:
        try:
            with open(self.filepath, 'r') as f:
                self.content = json.load(f)
            self._identify_type()
            self._extract_patterns()
            return True
        except Exception as e:
            logging.error(f"Error loading {self.filepath}: {str(e)}")
            return False
            
    def _identify_type(self):
        """Identify file type based on content patterns"""
        if "companies" in self.content and any("ethical" in key for key in str(self.content).lower()):
            self.file_type = "ethical_analysis"
        elif "companies" in self.content and "analysis" in self.content.get("companies", [{}])[0]:
            self.file_type = "search_analysis"
        elif "research_results" in self.content:
            self.file_type = "company_research"
        elif any("@" in key for key in str(self.content)):
            self.file_type = "email_analysis"
        else:
            self.file_type = "unknown"
            
    def _extract_patterns(self):
        """Extract key patterns and relationships from content"""
        def extract_keys(obj: Any, prefix: str = ""):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    new_prefix = f"{prefix}.{k}" if prefix else k
                    self.key_patterns.add(new_prefix)
                    extract_keys(v, new_prefix)
            elif isinstance(obj, list) and obj:
                extract_keys(obj[0], f"{prefix}[]")

        extract_keys(self.content)
        
    def extract_relationships(self, other_files: List['AnalysisFile']):
        """Find relationships with other files based on content similarity"""
        if self.file_type == "ethical_analysis":
            companies = self.content.get("companies", [])
            for company in companies:
                company_name = company.get("company_name", "").lower()
                if company_name:
                    for other in other_files:
                        if other.file_type in ["search_analysis", "company_research"]:
                            if company_name in str(other.content).lower():
                                self.relationships.add(other.filename)
                                
class AnalysisCluster:
    def __init__(self):
        self.files: Dict[str, List[AnalysisFile]] = defaultdict(list)
        self.patterns: Dict[str, Set[str]] = defaultdict(set)
        self.relationships: Dict[str, Set[str]] = defaultdict(set)
        self.stats: Dict[str, Dict] = defaultdict(lambda: defaultdict(int))
        
    def add_file(self, analysis_file: AnalysisFile):
        self.files[analysis_file.file_type].append(analysis_file)
        self.patterns[analysis_file.file_type].update(analysis_file.key_patterns)
        
    def analyze_relationships(self):
        """Analyze relationships between files across clusters"""
        all_files = [f for files in self.files.values() for f in files]
        for file in all_files:
            file.extract_relationships(all_files)
            if file.relationships:
                self.relationships[file.filename].update(file.relationships)
                
    def generate_stats(self):
        """Generate detailed statistics for each cluster"""
        for file_type, files in self.files.items():
            self.stats[file_type]["count"] = len(files)
            self.stats[file_type]["patterns"] = len(self.patterns[file_type])
            self.stats[file_type]["relationships"] = sum(1 for f in files if f.relationships)
            
            # Calculate pattern frequency
            pattern_freq = defaultdict(int)
            for f in files:
                for pattern in f.key_patterns:
                    pattern_freq[pattern] += 1
            
            self.stats[file_type]["common_patterns"] = sorted(
                [(k, v) for k, v in pattern_freq.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]

def find_metadata_file(filepath: str) -> Optional[str]:
    """Find corresponding metadata file if it exists"""
    base_path = os.path.splitext(filepath)[0]
    metadata_path = f"{base_path}_metadata.json"
    return metadata_path if os.path.exists(metadata_path) else None

def ingest_files(input_dir: str, output_dir: str):
    """Process all JSON files and generate analysis"""
    logging.info(f"Starting analysis of JSON files in {input_dir}")
    
    # Initialize cluster
    cluster = AnalysisCluster()
    
    # Process files
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.json'):
                filepath = os.path.join(root, file)
                analysis_file = AnalysisFile(filepath)
                
                if analysis_file.load():
                    # Check for metadata
                    metadata_path = find_metadata_file(filepath)
                    if metadata_path:
                        try:
                            with open(metadata_path, 'r') as f:
                                analysis_file.metadata = json.load(f)
                        except Exception as e:
                            logging.warning(f"Error loading metadata for {file}: {str(e)}")
                    
                    cluster.add_file(analysis_file)
                    logging.info(f"Successfully processed {filepath}")
    
    # Analyze relationships
    cluster.analyze_relationships()
    
    # Generate statistics
    cluster.generate_stats()
    
    # Prepare output
    output = {
        "summary": {
            "timestamp": datetime.now().isoformat(),
            "total_files": sum(len(files) for files in cluster.files.values()),
            "clusters": {
                file_type: {
                    "count": stats["count"],
                    "pattern_count": stats["patterns"],
                    "relationship_count": stats["relationships"],
                    "common_patterns": stats["common_patterns"]
                }
                for file_type, stats in cluster.stats.items()
            }
        },
        "relationships": {
            filename: list(related)
            for filename, related in cluster.relationships.items()
        },
        "patterns": {
            file_type: list(patterns)
            for file_type, patterns in cluster.patterns.items()
        }
    }
    
    # Write output
    output_path = os.path.join(output_dir, "analysis_summary.json")
    os.makedirs(output_dir, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=4)
    
    logging.info(f"Analysis complete. Summary written to {output_path}")
    
    # Generate Obsidian-friendly output
    obsidian_output = generate_obsidian_output(cluster, output)
    obsidian_path = os.path.join(output_dir, "analysis_obsidian.md")
    
    with open(obsidian_path, 'w') as f:
        f.write(obsidian_output)
    
    logging.info(f"Obsidian-friendly output written to {obsidian_path}")

def generate_obsidian_output(cluster: AnalysisCluster, analysis: Dict) -> str:
    """Generate Markdown output formatted for Obsidian"""
    lines = [
        "# JSON Analysis Summary",
        "",
        f"Analysis completed: {analysis['summary']['timestamp']}",
        "",
        "## Overview",
        "",
        f"Total files analyzed: {analysis['summary']['total_files']}",
        "",
        "## Clusters",
        ""
    ]
    
    for file_type, stats in analysis['summary']['clusters'].items():
        lines.extend([
            f"### {file_type.replace('_', ' ').title()}",
            "",
            f"- Files: {stats['count']}",
            f"- Unique patterns: {stats['pattern_count']}",
            f"- Files with relationships: {stats['relationship_count']}",
            "",
            "#### Common Patterns",
            ""
        ])
        
        for pattern, freq in stats['common_patterns']:
            lines.append(f"- `{pattern}` ({freq} occurrences)")
        
        lines.append("")
    
    lines.extend([
        "## Relationships",
        "",
        "```mermaid",
        "graph TD"
    ])
    
    # Add relationship graph
    added_nodes = set()
    for source, targets in analysis['relationships'].items():
        source_id = source.replace('.', '_')
        if source_id not in added_nodes:
            lines.append(f"    {source_id}[{source}]")
            added_nodes.add(source_id)
        
        for target in targets:
            target_id = target.replace('.', '_')
            if target_id not in added_nodes:
                lines.append(f"    {target_id}[{target}]")
                added_nodes.add(target_id)
            lines.append(f"    {source_id} --> {target_id}")
    
    lines.extend([
        "```",
        ""
    ])
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Analyze JSON files and generate summary")
    parser.add_argument('--input-dir', default='/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents/dev/input',
                      help='Input directory containing JSON files')
    parser.add_argument('--output-dir', default='/Users/srvo/Library/Mobile Documents/iCloud~md~obsidian/Documents/dev/output',
                      help='Output directory for analysis results')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    ingest_files(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main() 