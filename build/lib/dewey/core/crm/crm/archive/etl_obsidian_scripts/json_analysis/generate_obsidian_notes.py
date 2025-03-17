#!/usr/bin/env python3
"""
Generate Obsidian Notes

This script generates Obsidian-compatible markdown files from JSON analysis files.
It creates both individual search analysis notes and aggregated company reports.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import shutil
import argparse

class ObsidianNoteGenerator:
    def __init__(self, input_dir: Path, output_dir: Path, template_dir: Path):
        """Initialize the note generator with input, output, and template directories."""
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.template_dir = Path(template_dir)
        self.templates = {}
        self.load_templates()
        self.company_data: Dict[str, Dict] = {}
        
        # Verify directories exist
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")
        if not self.template_dir.exists():
            raise ValueError(f"Template directory does not exist: {self.template_dir}")
        
    def load_templates(self):
        """Load templates from the template directory."""
        logging.info(f"Loading templates from {self.template_dir}")
        try:
            # Load Search Analysis template
            search_template_path = self.template_dir / 'Search Analysis.md'
            if search_template_path.exists():
                with open(search_template_path, 'r') as f:
                    self.templates['Search Analysis.md'] = f.read()
                logging.info("Loaded template: Search Analysis.md")
            else:
                logging.error(f"Template not found: {search_template_path}")
                self.templates['Search Analysis.md'] = """---
title: {{title}}
company: {{company_name}}
date: {{date}}
type: {{type}}
---

[[Analysis Index|← Back to Analysis Index]]

# {{title}}

## Analysis Summary

## Key Findings

## Conduct Issues

## Pattern Analysis

## Source Data

## Related Analyses
```dataview
LIST
FROM "analyses"
WHERE company = "{{company_name}}"
AND file.name != this.file.name
```
"""
                logging.info("Using default Search Analysis template")

            # Load Company Report template
            company_template_path = self.template_dir / 'Company Report.md'
            if company_template_path.exists():
                with open(company_template_path, 'r') as f:
                    self.templates['Company Report.md'] = f.read()
                logging.info("Loaded template: Company Report.md")
            else:
                logging.error(f"Template not found: {company_template_path}")
                self.templates['Company Report.md'] = """---
title: {{company_name}} - Company Report
company: {{company_name}}
date: {{date}}
type: company_report
---

[[Analysis Index|← Back to Analysis Index]]

# {{company_name}} - Company Report

## Executive Summary

## Analysis Dashboard

## Latest Findings
```dataview
LIST
FROM "analyses"
WHERE company = "{{company_name}}"
SORT date DESC
LIMIT 5
```

## Risk Assessment

## Conduct Issues Summary

## Pattern Analysis

## Related Documents
```dataview
LIST
FROM "analyses" OR "companies"
WHERE company = "{{company_name}}"
AND file.name != this.file.name
```
"""
                logging.info("Using default Company Report template")

            # Add Analysis Index template
            self.templates['Analysis Index.md'] = """---
title: Analysis Index
type: index
---

# Analysis Index

## Recent Analyses
```dataview
TABLE company, date
FROM "analyses"
SORT date DESC
LIMIT 10
```

## Companies
```dataview
TABLE date as "Last Updated"
FROM "companies"
SORT date DESC
```

## Analysis Types
### Search Analyses
```dataview
TABLE company, date
FROM "analyses"
WHERE type = "search_analysis"
SORT date DESC
```

### Company Reports
```dataview
TABLE company, date
FROM "companies"
WHERE type = "company_report"
SORT date DESC
```
"""
            logging.info("Added Analysis Index template")

        except Exception as e:
            logging.error(f"Error loading templates: {str(e)}")
            raise

    def sanitize_filename(self, name):
        """Sanitize company name for use in filenames by replacing invalid characters."""
        # Replace characters that are invalid in file paths
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        return sanitized

    def process_search_analysis(self, json_data):
        """Process a search analysis JSON file and return note content."""
        try:
            # Try different JSON structures for company name
            company_name = None
            
            # Format 1: company.name
            if 'company' in json_data and isinstance(json_data['company'], dict):
                company_name = json_data['company'].get('name')
            
            # Format 2: companies[0].company_name
            if not company_name and 'companies' in json_data and isinstance(json_data['companies'], list) and len(json_data['companies']) > 0:
                company_name = json_data['companies'][0].get('company_name')
            
            # Default if no company name found
            if not company_name:
                company_name = 'Unknown Company'
                logging.warning(f"Could not find company name in JSON data")
            
            sanitized_company = self.sanitize_filename(company_name)
            
            # Get timestamp and convert to date string
            timestamp = None
            
            # Try different timestamp formats
            if 'metadata' in json_data and 'analysis_timestamp' in json_data['metadata']:
                timestamp = json_data['metadata']['analysis_timestamp']
            elif 'meta' in json_data and 'timestamp' in json_data['meta']:
                # Convert ISO format to timestamp
                try:
                    dt = datetime.fromisoformat(json_data['meta']['timestamp'].replace('Z', '+00:00'))
                    timestamp = dt.timestamp()
                except (ValueError, AttributeError):
                    pass
            
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        timestamp = int(timestamp)
                    date_str = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                except (ValueError, TypeError):
                    date_str = datetime.now().strftime('%Y-%m-%d')
            else:
                date_str = datetime.now().strftime('%Y-%m-%d')

            analysis = {
                'title': f'Search Analysis - {company_name}',
                'company_name': company_name,
                'date': date_str,
                'type': 'search_analysis'
            }

            # Add other fields from the template
            template = self.templates.get('Search Analysis.md', '')
            note_content = template

            # Replace template variables
            for key, value in analysis.items():
                note_content = note_content.replace(f'{{{{company_name}}}}', company_name)
                note_content = note_content.replace(f'{{{{date}}}}', date_str)
                note_content = note_content.replace(f'{{{{title}}}}', analysis['title'])
                note_content = note_content.replace(f'{{{{type}}}}', analysis['type'])

            return note_content, sanitized_company, date_str

        except Exception as e:
            logging.error(f"Error processing search analysis: {str(e)}")
            return None, None, None

    def generate_search_analysis_note(self, analysis: Dict, template: str) -> str:
        """Generate a search analysis note from template"""
        # Replace template variables
        content = template
        for key, value in analysis.items():
            if isinstance(value, (str, int, float)):
                content = content.replace(f"{{{{%s}}}}" % key, str(value))
            elif isinstance(value, list):
                # Handle lists using #each template syntax
                start_tag = f"{{{{#each {key}}}}}"
                end_tag = "{{/each}}"
                if start_tag in content and end_tag in content:
                    start_idx = content.find(start_tag)
                    end_idx = content.find(end_tag)
                    template_part = content[start_idx + len(start_tag):end_idx].strip()
                    replacement = "\n".join(template_part.replace("{{this}}", str(item)) 
                                         for item in value)
                    content = content[:start_idx] + replacement + content[end_idx + len(end_tag):]
                    
        return content
    
    def generate_company_report(self, company_name: str, data: Dict, template: str) -> str:
        """Generate a company report from template"""
        # Calculate aggregated data
        analyses = sorted(data['analyses'], key=lambda x: x['date'], reverse=True)
        risk_score = sum(a.get('data_confidence', 0) for a in analyses) / len(analyses)
        
        report_data = {
            'company_name': company_name,
            'company_ticker': analyses[0].get('company_ticker', 'N/A'),
            'status': 'Active',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'modified': datetime.now().strftime('%Y-%m-%d'),
            'risk_score': f"{risk_score:.1f}",
            'alert_count': len(data.get('conduct_issues', [])),
            'analysis_events': [
                {'date': a['date'], 'description': f"Search analysis performed"}
                for a in analyses
            ],
            'revisions': [
                {'date': datetime.now().strftime('%Y-%m-%d'),
                 'description': 'Initial report generated'}
            ]
        }
        
        # Replace template variables
        content = template
        for key, value in report_data.items():
            if isinstance(value, (str, int, float)):
                content = content.replace(f"{{{{%s}}}}" % key, str(value))
            elif isinstance(value, list):
                start_tag = f"{{{{#each {key}}}}}"
                end_tag = "{{/each}}"
                if start_tag in content and end_tag in content:
                    start_idx = content.find(start_tag)
                    end_idx = content.find(end_tag)
                    template_part = content[start_idx + len(start_tag):end_idx].strip()
                    replacement = "\n".join(
                        template_part.replace("{{date}}", item['date'])
                                 .replace("{{description}}", item['description'])
                        for item in value
                    )
                    content = content[:start_idx] + replacement + content[end_idx + len(end_tag):]
                    
        return content
    
    def generate_notes(self):
        """Generate notes from JSON files in the input directory."""
        try:
            # Create output directories if they don't exist
            analyses_dir = self.output_dir / 'analyses'
            companies_dir = self.output_dir / 'companies'
            analyses_dir.mkdir(parents=True, exist_ok=True)
            companies_dir.mkdir(parents=True, exist_ok=True)

            # Process each JSON file
            for json_file in self.input_dir.glob('*.json'):
                # Skip ethical analysis files
                if 'ethical_analysis' in json_file.name:
                    logging.info(f"Skipping ethical analysis file: {json_file.name}")
                    continue

                try:
                    with open(json_file, 'r') as f:
                        json_data = json.load(f)
                except json.JSONDecodeError:
                    logging.error(f"Error decoding JSON from file: {json_file}")
                    continue
                except Exception as e:
                    logging.error(f"Error reading file {json_file}: {str(e)}")
                    continue

                # Process search analysis
                note_content, company_name, date_str = self.process_search_analysis(json_data)
                if note_content and company_name:
                    # Generate filename
                    filename = f"search_analysis_{company_name}_{date_str}.md"
                    note_path = analyses_dir / filename

                    # Write note content
                    try:
                        with open(note_path, 'w') as f:
                            f.write(note_content)
                        logging.info(f"Generated analysis note: {note_path}")

                        # Store company data for company report
                        if company_name not in self.company_data:
                            self.company_data[company_name] = {
                                'name': company_name,
                                'last_updated': date_str,
                                'analyses': []
                            }
                        self.company_data[company_name]['analyses'].append({
                            'date': date_str,
                            'type': 'search_analysis',
                            'file': filename
                        })
                    except Exception as e:
                        logging.error(f"Error writing note {note_path}: {str(e)}")

            # Generate company reports
            for company_name, company_data in self.company_data.items():
                template = self.templates.get('Company Report.md', '')
                report_content = self.generate_company_report(company_name, company_data, template)
                
                # Generate filename
                filename = f"company_report_{company_name}.md"
                report_path = self.output_dir / 'companies' / filename
                
                try:
                    with open(report_path, 'w') as f:
                        f.write(report_content)
                    logging.info(f"Generated company report: {report_path}")
                except Exception as e:
                    logging.error(f"Error writing company report {report_path}: {str(e)}")

            # Generate analysis index
            self.generate_analysis_index()

            logging.info("Note generation completed successfully")

        except Exception as e:
            logging.error(f"Error generating notes: {str(e)}")
            raise

    def generate_analysis_index(self):
        """Generate an index page listing all analyses."""
        index_content = "# Analysis Index\n\n"
        
        # Group analyses by company
        for company_name, company_data in self.company_data.items():
            index_content += f"## {company_name}\n\n"
            
            # Sort analyses by date
            analyses = sorted(company_data['analyses'], key=lambda x: x['date'], reverse=True)
            
            for analysis in analyses:
                date = analysis['date']
                analysis_type = analysis['type']
                file_name = analysis['file']
                
                # Create link to analysis
                if analysis_type == 'search_analysis':
                    link_path = f"analyses/{file_name}"
                else:
                    link_path = f"companies/{file_name}"
                    
                index_content += f"- {date}: [{analysis_type}]({link_path})\n"
            
            index_content += "\n"
        
        # Write index file
        index_path = self.output_dir / 'analysis_index.md'
        try:
            with open(index_path, 'w') as f:
                f.write(index_content)
            logging.info(f"Generated analysis index: {index_path}")
        except Exception as e:
            logging.error(f"Error writing analysis index {index_path}: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description="Generate Obsidian notes from JSON analysis files")
    parser.add_argument('--input-dir', required=True,
                      help='Input directory containing JSON files')
    parser.add_argument('--output-dir', required=True,
                      help='Output directory for Obsidian notes')
    parser.add_argument('--template-dir', required=True,
                      help='Directory containing note templates')
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        generator = ObsidianNoteGenerator(
            args.input_dir,
            args.output_dir,
            args.template_dir
        )
        
        generator.generate_notes()
        logging.info("Note generation completed successfully")
        
    except Exception as e:
        logging.error(f"Error during note generation: {str(e)}")
        raise
    
if __name__ == "__main__":
    main() 