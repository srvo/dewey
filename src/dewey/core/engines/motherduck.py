#!/usr/bin/env python3
"""
MotherDuck Engine

This module provides a unified interface for interacting with MotherDuck databases.
It handles:
1. Database connections and management
2. Data upload from various file formats
3. Schema validation and management
"""

import os
import json
import csv
import logging
import duckdb
import time
import chardet
import sqlite3
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

# Configure logging
logger = logging.getLogger(__name__)

class MarkdownSection:
    """Represents a section in a markdown file."""
    def __init__(self, title: str, level: int, content: str):
        self.title = title
        self.level = level
        self.content = content
        self.metadata = {}  # For frontmatter or other metadata
        self.tables = []    # For any tables in the section
        self.code_blocks = []  # For code blocks
        self.links = []     # For links

class MarkdownTable:
    """Represents a table found in markdown content."""
    def __init__(self, headers: List[str], rows: List[List[str]]):
        self.headers = headers
        self.rows = rows

def _parse_markdown_table(table_text: str) -> Optional[MarkdownTable]:
    """Parse a markdown table into headers and rows."""
    lines = [line.strip() for line in table_text.strip().split('\n')]
    if len(lines) < 3:  # Need header, separator, and at least one row
        return None
        
    # Parse headers
    headers = [col.strip() for col in lines[0].strip('|').split('|')]
    
    # Verify separator line
    separator = lines[1].strip('|').split('|')
    if not all('-' in col for col in separator):
        return None
        
    # Parse rows
    rows = []
    for line in lines[2:]:
        if line and '|' in line:  # Skip empty lines
            row = [col.strip() for col in line.strip('|').split('|')]
            rows.append(row)
            
    return MarkdownTable(headers, rows)

class MotherDuckEngine:
    """Main interface for MotherDuck operations."""
    
    def __init__(
        self,
        database_name: str = "dewey",
        token: Optional[str] = None,
    ):
        """Initialize the MotherDuck engine.
        
        Args:
            database_name: Name of the database to connect to
            token: MotherDuck token (if None, will try to get from env)
        """
        self.database_name = database_name
        self.token = token or os.environ.get("MOTHERDUCK_TOKEN")
        self._conn = None
        
        # Initialize connection
        self.connect()
    
    def connect(self) -> None:
        """Initialize connection to MotherDuck database."""
        if not self.token:
            raise ValueError("MotherDuck token is required. Set MOTHERDUCK_TOKEN environment variable.")
            
        try:
            conn_str = f"md:{self.database_name}?motherduck_token={self.token}"
            self._conn = duckdb.connect(conn_str)
            logger.info(f"Connected to MotherDuck database: {self.database_name}")
        except Exception as e:
            logger.error(f"Failed to connect to MotherDuck: {str(e)}")
            raise
    
    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            
    def list_tables(self) -> List[str]:
        """List all tables in the database.
        
        Returns:
            List of table names
        """
        try:
            result = self._conn.execute("SHOW TABLES").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Failed to list tables: {str(e)}")
            raise
    
    def get_schema(self, table_name: str) -> Dict[str, str]:
        """Get the schema of a table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Dict mapping column names to their types
        """
        try:
            # Get column information
            result = self._conn.execute(f"DESCRIBE {table_name}").fetchall()
            schema = {row[0]: row[1] for row in result}
            return schema
        except Exception as e:
            logger.error(f"Failed to get schema for table {table_name}: {str(e)}")
            raise
    
    def execute(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a SQL statement.
        
        Args:
            sql: SQL statement to execute
            params: Optional parameters for the SQL statement
            
        Returns:
            Result of the execution
        """
        try:
            if params:
                result = self._conn.execute(sql, params)
            else:
                result = self._conn.execute(sql)
            return result
        except Exception as e:
            logger.error(f"Failed to execute SQL: {str(e)}")
            raise
    
    def _detect_csv_params(self, file_path: str, sample_size: int = 1024 * 1024) -> Dict[str, Any]:
        """Detect CSV parameters like delimiter, encoding, and quote character.
        
        Args:
            file_path: Path to the CSV file
            sample_size: Number of bytes to read for detection
            
        Returns:
            Dict containing detected parameters
        """
        # Detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
        
        # Read sample with detected encoding
        with open(file_path, 'r', encoding=encoding) as f:
            sample = f.read(sample_size)
        
        # Count potential delimiters
        delimiters = [',', ';', '\t', '|']
        delimiter_counts = {d: sample.count(d) for d in delimiters}
        max_delimiter = max(delimiter_counts.items(), key=lambda x: x[1])[0]
        
        # Detect if values are quoted
        quote_chars = ['"', "'"]
        quote_counts = {q: sample.count(q) for q in quote_chars}
        quote_char = max(quote_counts.items(), key=lambda x: x[1])[0] if any(quote_counts.values()) else ''
        
        # Check if there's a header
        first_line = sample.split('\n')[0]
        has_header = all(not c.isdigit() for c in first_line.split(max_delimiter))
        
        return {
            'encoding': encoding,
            'delimiter': max_delimiter,
            'quote': quote_char,
            'has_header': has_header
        }
    
    def _get_sqlite_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """Get table information from SQLite database.
        
        Args:
            file_path: Path to SQLite database
            
        Returns:
            List of dicts containing table info (name, schema, row_count)
        """
        tables = []
        try:
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            for table_name in table_names:
                # Get schema
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                schema = {col[1]: col[2] for col in columns}
                
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                
                # Get sample data
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
                sample = cursor.fetchone()
                
                tables.append({
                    'name': table_name,
                    'schema': schema,
                    'row_count': row_count,
                    'sample': sample
                })
            
            conn.close()
            return tables
            
        except Exception as e:
            logger.error(f"Error analyzing SQLite database {file_path}: {str(e)}")
            raise

    def _analyze_json_structure(self, file_path: str) -> Dict[str, Any]:
        """Analyze JSON file structure and content.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            Dict containing JSON structure info
        """
        try:
            with open(file_path, 'r') as f:
                # Try to detect if it's a JSON Lines file
                first_line = f.readline().strip()
                f.seek(0)
                
                try:
                    # Try parsing as single JSON
                    data = json.load(f)
                    is_jsonl = False
                except json.JSONDecodeError:
                    # Try parsing as JSON Lines
                    f.seek(0)
                    first_line_data = json.loads(first_line)
                    is_jsonl = True
                    data = [first_line_data]  # Just use first line for schema detection
            
            def infer_schema(obj: Any, path: str = '') -> Dict[str, str]:
                """Recursively infer schema from JSON object."""
                schema = {}
                
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        new_path = f"{path}.{key}" if path else key
                        schema.update(infer_schema(value, new_path))
                elif isinstance(obj, list) and obj:
                    # For arrays, analyze first element
                    if isinstance(obj[0], (dict, list)):
                        schema.update(infer_schema(obj[0], f"{path}[0]"))
                    else:
                        schema[path] = type(obj[0]).__name__
                else:
                    schema[path] = type(obj).__name__
                
                return schema
            
            schema = infer_schema(data)
            
            return {
                'is_jsonl': is_jsonl,
                'schema': schema,
                'is_array': isinstance(data, list),
                'sample': data if not is_jsonl else first_line_data
            }
            
        except Exception as e:
            logger.error(f"Error analyzing JSON file {file_path}: {str(e)}")
            raise

    def _parse_markdown_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a markdown file into structured data.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Dict containing parsed markdown structure
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract frontmatter if present
            frontmatter = {}
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        content = parts[2]
                    except Exception as e:
                        logger.warning(f"Error parsing frontmatter: {str(e)}")
            
            # Split into sections
            sections = []
            current_section = None
            current_content = []
            
            for line in content.split('\n'):
                # Check for headers
                header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
                if header_match:
                    # Save previous section if exists
                    if current_section:
                        current_section.content = '\n'.join(current_content)
                        sections.append(current_section)
                    
                    # Start new section
                    level = len(header_match.group(1))
                    title = header_match.group(2).strip()
                    current_section = MarkdownSection(title, level, '')
                    current_content = []
                elif current_section:
                    current_content.append(line)
                
            # Save last section
            if current_section:
                current_section.content = '\n'.join(current_content)
                sections.append(current_section)
            
            # Process each section
            for section in sections:
                # Extract tables
                table_pattern = r'\|.+\|\n\|[-|]+\|\n(\|.+\|\n?)+'
                table_matches = re.finditer(table_pattern, section.content)
                for match in table_matches:
                    table = _parse_markdown_table(match.group(0))
                    if table:
                        section.tables.append(table)
                
                # Extract code blocks
                code_pattern = r'```(\w*)\n(.*?)```'
                code_matches = re.finditer(code_pattern, section.content, re.DOTALL)
                for match in code_matches:
                    section.code_blocks.append({
                        'language': match.group(1),
                        'code': match.group(2).strip()
                    })
                
                # Extract links
                link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
                link_matches = re.finditer(link_pattern, section.content)
                for match in link_matches:
                    section.links.append({
                        'text': match.group(1),
                        'url': match.group(2)
                    })
            
            return {
                'frontmatter': frontmatter,
                'sections': sections
            }
            
        except Exception as e:
            logger.error(f"Error parsing markdown file {file_path}: {str(e)}")
            raise

    def _create_markdown_tables(self, file_path: str, parsed_data: Dict[str, Any], module: str) -> bool:
        """Create tables from parsed markdown data.
        
        Args:
            file_path: Original markdown file path
            parsed_data: Parsed markdown structure
            module: Module name for table prefixes
        """
        try:
            base_name = self._generate_table_name(file_path, module)
            
            # Create metadata table
            metadata_table = f"{base_name}_metadata"
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {metadata_table} (
                    file_path VARCHAR,
                    title VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert metadata
            self._conn.execute(f"""
                INSERT INTO {metadata_table} (file_path, title)
                VALUES (?, ?)
            """, (file_path, parsed_data['frontmatter'].get('title', os.path.basename(file_path))))
            
            # Create sections table
            sections_table = f"{base_name}_sections"
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {sections_table} (
                    file_path VARCHAR,
                    section_title VARCHAR,
                    level INTEGER,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert sections
            for section in parsed_data['sections']:
                self._conn.execute(f"""
                    INSERT INTO {sections_table} (file_path, section_title, level, content)
                    VALUES (?, ?, ?, ?)
                """, (file_path, section.title, section.level, section.content))
            
            # Create tables for embedded tables
            for i, section in enumerate(parsed_data['sections']):
                for j, table in enumerate(section.tables):
                    table_name = f"{base_name}_table_{i}_{j}"
                    
                    # Create dynamic columns based on headers
                    columns = [f"{h.lower().replace(' ', '_')} VARCHAR" for h in table.headers]
                    self._conn.execute(f"""
                        CREATE TABLE IF NOT EXISTS {table_name} (
                            file_path VARCHAR,
                            section_title VARCHAR,
                            {', '.join(columns)},
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Insert rows
                    for row in table.rows:
                        placeholders = ', '.join(['?' for _ in range(len(row) + 2)])  # +2 for file_path and section_title
                        self._conn.execute(f"""
                            INSERT INTO {table_name} (file_path, section_title, {', '.join(h.lower().replace(' ', '_') for h in table.headers)})
                            VALUES ({placeholders})
                        """, (file_path, section.title, *row))
            
            # Create code blocks table
            code_table = f"{base_name}_code"
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {code_table} (
                    file_path VARCHAR,
                    section_title VARCHAR,
                    language VARCHAR,
                    code TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert code blocks
            for section in parsed_data['sections']:
                for block in section.code_blocks:
                    self._conn.execute(f"""
                        INSERT INTO {code_table} (file_path, section_title, language, code)
                        VALUES (?, ?, ?, ?)
                    """, (file_path, section.title, block['language'], block['code']))
            
            # Create links table
            links_table = f"{base_name}_links"
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {links_table} (
                    file_path VARCHAR,
                    section_title VARCHAR,
                    link_text VARCHAR,
                    url VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert links
            for section in parsed_data['sections']:
                for link in section.links:
                    self._conn.execute(f"""
                        INSERT INTO {links_table} (file_path, section_title, link_text, url)
                        VALUES (?, ?, ?, ?)
                    """, (file_path, section.title, link['text'], link['url']))
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating markdown tables: {str(e)}")
            return False
    
    def upload_file(
        self,
        file_path: str,
        module: Optional[str] = None,
        table_name: Optional[str] = None,
        dedup_strategy: str = "update"
    ) -> bool:
        """Upload a file to MotherDuck.
        
        Args:
            file_path: Path to the file to upload
            module: Optional module name for organization
            table_name: Optional table name override
            dedup_strategy: Strategy for handling duplicates (update, replace, skip, version)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False
                
            # Get file extension
            ext = os.path.splitext(file_path)[1].lower()
            
            # Generate table name if not provided
            if not table_name:
                table_name = self._generate_table_name(file_path, module or "")
            
            # Handle different file types
            if ext == '.md':
                # Parse markdown and create tables
                parsed_data = self._parse_markdown_file(file_path)
                logger.info(f"Parsed markdown file {file_path}: {len(parsed_data['sections'])} sections")
                return self._create_markdown_tables(file_path, parsed_data, module)
                
            elif ext == '.csv':
                # Detect CSV parameters
                params = self._detect_csv_params(file_path)
                logger.info(f"Detected CSV parameters for {file_path}: {params}")
                
                # Create SQL for reading CSV with detected parameters
                sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS 
                SELECT * FROM read_csv_auto(
                    '{file_path}',
                    delim='{params['delimiter']}',
                    quote='{params['quote']}',
                    header={str(params['has_header']).lower()},
                    filename=true,
                    all_varchar=false,
                    sample_size=1000,
                    auto_detect=true
                )
                """
                self._conn.execute(sql)
                
            elif ext == '.json':
                # Analyze JSON structure
                json_info = self._analyze_json_structure(file_path)
                logger.info(f"Analyzed JSON structure for {file_path}")
                
                # Create SQL for reading JSON
                sql = f"""
                CREATE TABLE IF NOT EXISTS {table_name} AS 
                SELECT * FROM read_json_auto('{file_path}')
                """
                self._conn.execute(sql)
                
            elif ext in ['.db', '.sqlite', '.sqlite3']:
                # Get list of tables
                tables = self._get_sqlite_tables(file_path)
                logger.info(f"Found {len(tables)} tables in SQLite file {file_path}")
                
                for table in tables:
                    table_sql = f"""
                    ATTACH '{file_path}' AS source;
                    CREATE TABLE IF NOT EXISTS {table['name']} AS 
                    SELECT * FROM source.{table['name']};
                    DETACH source;
                    """
                    self._conn.execute(table_sql)
                    
            elif ext == '.duckdb':
                # Attach DuckDB database
                sql = f"""
                ATTACH '{file_path}' AS source;
                """
                self._conn.execute(sql)
                
                # Get list of tables
                tables = self._conn.execute("SELECT table_name FROM source.information_schema.tables").fetchall()
                
                for table in tables:
                    table_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table[0]} AS 
                    SELECT * FROM source.{table[0]};
                    """
                    self._conn.execute(table_sql)
                    
                # Detach database
                self._conn.execute("DETACH source")
                
            else:
                logger.error(f"Unsupported file type: {ext}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {str(e)}")
            return False
    
    def upload_directory(
        self,
        directory: str,
        recursive: bool = True,
    ) -> Tuple[int, int]:
        """Upload all supported files in a directory.
        
        Args:
            directory: Path to directory
            recursive: Whether to search subdirectories
            
        Returns:
            Tuple of (success_count, total_count)
        """
        try:
            if not os.path.isdir(directory):
                logger.error(f"Directory not found: {directory}")
                return (0, 0)
            
            # Find all supported files
            supported_extensions = ['.duckdb', '.db', '.sqlite', '.sqlite3', '.csv', '.json', '.parquet']
            files = []
            
            if recursive:
                for root, _, filenames in os.walk(directory):
                    for filename in filenames:
                        if any(filename.lower().endswith(ext) for ext in supported_extensions):
                            files.append(os.path.join(root, filename))
            else:
                files = [
                    os.path.join(directory, f) for f in os.listdir(directory)
                    if any(f.lower().endswith(ext) for ext in supported_extensions)
                ]
            
            # Upload each file
            success_count = 0
            total_count = len(files)
            
            for file_path in files:
                if self.upload_file(file_path):
                    success_count += 1
            
            return success_count, total_count
            
        except Exception as e:
            logger.error(f"Error uploading directory {directory}: {str(e)}")
            return (0, 0)
    
    def _determine_module(self, file_path: str) -> str:
        """Determine which module a file belongs to."""
        file_path_lower = file_path.lower()
        file_name = os.path.basename(file_path_lower)
        
        # Define module keywords
        module_keywords = {
            "crm": ["crm", "contact", "email", "calendar", "opportunity"],
            "research": ["research", "analysis", "search", "keyword"],
            "accounting": ["account", "portfolio", "transaction", "financial"],
            "personal": ["audio", "note", "personal"],
        }
        
        # Check path and filename against keywords
        for module, keywords in module_keywords.items():
            if any(kw in file_path_lower for kw in keywords) or any(kw in file_name for kw in keywords):
                return module
        
        return "other"
    
    def _generate_table_name(self, file_path: str, module: str) -> str:
        """Generate a suitable table name from file path."""
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        
        # Clean up name
        base_name = base_name.lower()
        base_name = ''.join(c if c.isalnum() else '_' for c in base_name)
        base_name = base_name.strip('_')
        
        # Remove date patterns
        import re
        base_name = re.sub(r'_\d{6}_\d{6}', '', base_name)
        base_name = re.sub(r'_\d{8}', '', base_name)
        base_name = re.sub(r'_\d{14}', '', base_name)
        
        # Add module prefix if needed
        if not base_name.startswith(f"{module}_"):
            base_name = f"{module}_{base_name}"
        
        return base_name