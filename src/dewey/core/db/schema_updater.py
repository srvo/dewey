#!/usr/bin/env python
"""
MotherDuck Schema Extractor

This script connects to MotherDuck, extracts the database schema,
and updates the SQLAlchemy models in models.py file.
"""

import os
import sys
import yaml
import re
import duckdb
import keyword
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import sqlalchemy as sa
from sqlalchemy import inspect, MetaData, Table, Column
from sqlalchemy.ext.declarative import declarative_base

# Add project root to path if running this script directly
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

# Set file paths
CONFIG_PATH = Path("/Users/srvo/dewey/config/dewey.yaml")
MODELS_PATH = Path("/Users/srvo/dewey/src/dewey/core/db/models.py")

# DuckDB to SQLAlchemy type mapping
DUCKDB_TO_SQLALCHEMY_TYPES = {
    "INTEGER": "sa.Integer",
    "BIGINT": "sa.BigInteger",
    "SMALLINT": "sa.SmallInteger",
    "TINYINT": "sa.SmallInteger",
    "UBIGINT": "sa.BigInteger",
    "UINTEGER": "sa.Integer",
    "USMALLINT": "sa.SmallInteger",
    "UTINYINT": "sa.SmallInteger",
    "DECIMAL": "sa.DECIMAL",
    "FLOAT": "sa.Float",
    "DOUBLE": "sa.Float",
    "VARCHAR": "sa.String",
    "CHAR": "sa.CHAR",
    "TEXT": "sa.Text",
    "BOOLEAN": "sa.Boolean",
    "DATE": "sa.Date",
    "TIME": "sa.Time",
    "TIMESTAMP": "sa.DateTime",
    "TIMESTAMP WITH TIME ZONE": "sa.DateTime(timezone=True)",
    "BLOB": "sa.LargeBinary",
    "UUID": "sa.String",
    "JSON": "sa.JSON",
    "ENUM": "sa.Enum",
}

# Add list of Python keywords and other problematic identifiers
PYTHON_KEYWORDS = set(keyword.kwlist)
# Add additional problematic identifiers
PROBLEMATIC_IDENTIFIERS = {
    'yield': 'yield_value',
    'class': 'class_type',
    'global': 'global_flag',
    'import': 'import_flag',
    'return': 'return_value',
    'break': 'break_flag',
    'continue': 'continue_flag',
    'for': 'for_loop',
    'while': 'while_loop',
    'try': 'try_block',
    'except': 'except_handler',
    'finally': 'finally_block',
    'with': 'with_context',
    'as': 'as_alias',
    'from': 'from_source',
    'in': 'in_container',
    'is': 'is_equal',
    'lambda': 'lambda_func',
    'def': 'def_function',
    'if': 'if_condition',
    'else': 'else_clause',
    'elif': 'elif_clause'
}

def sanitize_identifier(identifier: str) -> str:
    """
    Sanitize an identifier to make it a valid Python identifier.
    - Replace spaces with underscores
    - Handle reserved keywords
    - Handle identifiers starting with numbers
    - Handle special characters
    """
    # Replace spaces with underscores
    sanitized = identifier.replace(' ', '_')
    
    # Handle identifiers starting with numbers
    if sanitized and sanitized[0].isdigit():
        # Map common patterns like '5yr' to 'five_yr'
        number_words = {
            '0': 'zero',
            '1': 'one',
            '2': 'two',
            '3': 'three',
            '4': 'four',
            '5': 'five',
            '6': 'six',
            '7': 'seven',
            '8': 'eight',
            '9': 'nine',
            '10': 'ten',
            '11': 'eleven',
            '12': 'twelve',
            '15': 'fifteen',
            '20': 'twenty',
            '30': 'thirty',
            '50': 'fifty',
            '100': 'one_hundred'
        }
        
        # Try to find the longest matching number prefix
        for num_str in sorted(number_words.keys(), key=len, reverse=True):
            if sanitized.startswith(num_str):
                sanitized = number_words[num_str] + '_' + sanitized[len(num_str):]
                break
        
        # If no specific match was found but still starts with a digit
        if sanitized[0].isdigit():
            sanitized = 'n' + sanitized
    
    # Replace special characters with underscores (including &)
    sanitized = re.sub(r'[^\w_]', '_', sanitized)
    
    # Check if it's a Python keyword or problematic identifier
    if sanitized in PYTHON_KEYWORDS or sanitized in PROBLEMATIC_IDENTIFIERS:
        sanitized = PROBLEMATIC_IDENTIFIERS.get(sanitized, f"{sanitized}_val")
    
    # Check for SQLAlchemy reserved attributes
    SQLALCHEMY_RESERVED = {
        'metadata', 'query', 'registry', '__init__', '__table__',
        '__tablename__', '__mapper_args__', '__dict__', 
        '__weakref__', '__module__', '__annotations__'
    }
    
    if sanitized in SQLALCHEMY_RESERVED:
        sanitized = f"{sanitized}_col"
    
    return sanitized

def load_env_variables():
    """Load environment variables from .env file."""
    env_path = Path('/Users/srvo/dewey/.env')
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        print("Loaded environment variables from .env file")

def load_config() -> Dict[str, Any]:
    """Load configuration from dewey.yaml."""
    # First load environment variables
    load_env_variables()
    
    # Check in home directory
    config_path = Path.home() / 'dewey.yaml'
    
    # Check in /etc
    if not config_path.exists():
        config_path = Path('/etc/dewey.yaml')
    
    # Check in project directory
    if not config_path.exists():
        config_path = Path('/Users/srvo/dewey/dewey.yaml')
    
    # Check in config directory
    if not config_path.exists():
        config_path = Path('/Users/srvo/dewey/config/dewey.yaml')
    
    if not config_path.exists():
        # If still not found, use default connection without config
        print("Warning: Could not find dewey.yaml configuration file. Using default connection.")
        return {"motherduck": {"token": os.environ.get('MOTHERDUCK_TOKEN')}}
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config

def get_motherduck_connection(config: Dict[str, Any]) -> duckdb.DuckDBPyConnection:
    """Establish connection to MotherDuck."""
    token = os.environ.get('MOTHERDUCK_TOKEN') or config.get('motherduck', {}).get('token')
    if not token:
        raise ValueError("MotherDuck token not found. Set MOTHERDUCK_TOKEN environment variable or add to dewey.yaml.")
    
    # Set token in environment variable first
    os.environ['MOTHERDUCK_TOKEN'] = token
    
    # Connect using environment token
    connection_string = "md:dewey"
    conn = duckdb.connect(connection_string)
    
    try:
        # Execute test query to verify connection
        conn.execute("SELECT 1")
        print(f"Connected to MotherDuck using connection string: {connection_string}")
    except Exception as e:
        print(f"Error connecting to MotherDuck: {e}")
        raise
    
    return conn

def extract_schema(conn: duckdb.DuckDBPyConnection) -> List[Dict[str, Any]]:
    """Extract schema information from MotherDuck."""
    # Get list of tables
    tables = conn.execute("SHOW TABLES").fetchall()
    schema_info = []
    
    for table_row in tables:
        table_name = table_row[0]
        
        # Get column information including primary key info
        columns_query = f"PRAGMA table_info('{table_name}')"
        columns_df = conn.execute(columns_query).fetchdf()
        
        # Extract primary key columns from table_info
        pk_columns = columns_df[columns_df['pk'] > 0]['name'].tolist()
        
        # Get foreign key information
        try:
            fk_query = f"PRAGMA foreign_key_list('{table_name}')"
            foreign_keys_df = conn.execute(fk_query).fetchdf()
            foreign_keys = []
            for _, row in foreign_keys_df.iterrows():
                foreign_keys.append({
                    'column': row['from'],
                    'ref_table': row['table'],
                    'ref_column': row['to']
                })
        except Exception:
            # Some tables might not support foreign key info
            foreign_keys = []
        
        # Process columns
        column_info = []
        for _, col in columns_df.iterrows():
            col_name = col['name']
            col_type = col['type'].upper()
            is_nullable = not col['notnull']
            default_value = col['dflt_value']
            is_pk = col['pk'] > 0
            
            column_info.append({
                'name': col_name,
                'type': col_type,
                'nullable': is_nullable,
                'default': default_value,
                'primary_key': is_pk
            })
        
        schema_info.append({
            'table_name': table_name,
            'columns': column_info,
            'foreign_keys': foreign_keys
        })
    
    return schema_info

def map_duckdb_to_sqlalchemy(duckdb_type: str) -> str:
    """Map DuckDB data types to SQLAlchemy types."""
    # Extract the base type without precision or scale
    base_type = duckdb_type.split('(')[0].upper()
    return DUCKDB_TO_SQLALCHEMY_TYPES.get(base_type, 'sa.String')

def parse_existing_models(file_path: str) -> Dict[str, Dict[str, Any]]:
    """Parse existing model file to extract custom methods."""
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r') as f:
        content = f.readlines()
    
    models = {}
    current_model = None
    in_method = False
    current_method = []
    indentation = 0
    
    for line in content:
        # Check if this is a class definition
        if line.strip().startswith('class ') and '(Base)' in line:
            class_name = line.strip().split('class ')[1].split('(')[0].strip()
            current_model = class_name
            models[current_model] = {'methods': []}
            in_method = False
            indentation = len(line) - len(line.lstrip())
        
        # Check if we're in a method
        elif current_model and line.strip().startswith('def ') and line.count('(') > 0:
            # This is a method definition
            if in_method and current_method:
                # Save the previous method
                models[current_model]['methods'].append(current_method)
            
            current_method = [line]
            in_method = True
            method_indent = len(line) - len(line.lstrip())
        
        # If we're in a method, collect its lines
        elif in_method:
            if not line.strip() or len(line) - len(line.lstrip()) > method_indent:
                current_method.append(line)
            else:
                # Method ended
                models[current_model]['methods'].append(current_method)
                current_method = []
                in_method = False
                
                # Check if this is a new method
                if line.strip().startswith('def ') and line.count('(') > 0:
                    current_method = [line]
                    in_method = True
                    method_indent = len(line) - len(line.lstrip())
    
    # Save the last method if there is one
    if in_method and current_method:
        models[current_model]['methods'].append(current_method)
    
    return models

def generate_sql_schemas_and_indexes(schema_info: List[Dict[str, Any]]) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """Generate SQL schemas and indexes for all tables."""
    # SQL reserved keywords that need to be escaped
    SQL_RESERVED = {
        'from', 'where', 'select', 'insert', 'update', 'delete', 'drop', 
        'create', 'alter', 'table', 'index', 'view', 'order', 'by', 'group',
        'having', 'limit', 'offset', 'join', 'inner', 'outer', 'left', 'right',
        'on', 'as', 'case', 'when', 'then', 'else', 'end', 'user', 'password',
        'grant', 'revoke', 'commit', 'rollback', 'between', 'like', 'in', 'exists'
    }
    
    # Function to escape column names
    def escape_column(col_name: str) -> str:
        if col_name.lower() in SQL_RESERVED:
            return f'"{col_name}"'
        return col_name
    
    schemas = {}
    indexes = {}
    
    for table in schema_info:
        table_name = table['table_name']
        
        # Generate CREATE TABLE statement
        columns = []
        for col in table['columns']:
            col_name = col['name']
            col_type = col['type']
            constraints = []
            
            # Escape column name if it's a reserved keyword
            escaped_col_name = escape_column(col_name)
            
            if not col['nullable']:
                constraints.append('NOT NULL')
            if col['primary_key']:
                constraints.append('PRIMARY KEY')
            if col['default'] is not None:
                constraints.append(f"DEFAULT {col['default']}")
                
            col_def = f"{escaped_col_name} {col_type} {' '.join(constraints)}".strip()
            columns.append(col_def)
        
        # Add foreign key constraints
        for fk in table['foreign_keys']:
            escaped_col = escape_column(fk['column'])
            escaped_ref_col = escape_column(fk['ref_column'])
            fk_constraint = f"FOREIGN KEY ({escaped_col}) REFERENCES {fk['ref_table']}({escaped_ref_col})"
            columns.append(fk_constraint)
        
        create_table = f"CREATE TABLE IF NOT EXISTS {table_name} (\n    " + ",\n    ".join(columns) + "\n)"
        schemas[table_name] = create_table
        
        # Generate indexes - we'll create simple indexes for all columns that are primary keys
        table_indexes = []
        for col in table['columns']:
            if col['primary_key']:
                idx_name = f"idx_{table_name}_{col['name']}"
                escaped_col = escape_column(col['name'])
                index_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({escaped_col})"
                table_indexes.append(index_sql)
        
        # Add more indexes based on foreign keys
        for fk in table['foreign_keys']:
            idx_name = f"idx_{table_name}_{fk['column']}"
            escaped_col = escape_column(fk['column'])
            index_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}({escaped_col})"
            table_indexes.append(index_sql)
        
        if table_indexes:
            indexes[table_name] = table_indexes
    
    return schemas, indexes

def generate_sqlalchemy_models(schema_info: List[Dict[str, Any]], existing_models: Dict[str, Dict[str, Any]], add_primary_key_if_missing: bool = True) -> str:
    """Generate SQLAlchemy model classes from schema information."""
    # Generate SQL schemas and indexes
    sql_schemas, sql_indexes = generate_sql_schemas_and_indexes(schema_info)
    
    imports = [
        "import sqlalchemy as sa",
        "from sqlalchemy.ext.declarative import declarative_base",
        "from sqlalchemy import Column",  # Add explicit Column import
        "from sqlalchemy.orm import relationship",
        "from datetime import datetime, date, time",
        "from typing import Optional, List, Dict, Any",
        "\n",
        "Base = declarative_base()",
        "\n"
    ]
    
    model_definitions = []
    
    for table in schema_info:
        table_name = table['table_name']
        class_name = ''.join(word.capitalize() for word in table_name.split('_'))
        
        model_lines = [
            f"class {class_name}(Base):",
            f"    __tablename__ = '{table_name}'",
            ""
        ]
        
        # Check if table has a primary key defined
        has_primary_key = any(col['primary_key'] for col in table['columns'])
        
        # Add columns
        for column in table['columns']:
            col_name = sanitize_identifier(column['name'])  # Sanitize column name
            col_type = map_duckdb_to_sqlalchemy(column['type'])
            
            # Build column options
            options = []
            if column['primary_key']:
                options.append("primary_key=True")
            if not column['nullable']:
                options.append("nullable=False")
            if column['default'] is not None:
                # For default values, need to handle different types
                if isinstance(column['default'], str):
                    if column['default'].lower() in ('true', 'false'):
                        options.append(f"default={column['default'].lower()}")
                    elif column['default'].startswith("'") or column['default'].startswith('"'):
                        options.append(f"default={column['default']}")
                    else:
                        options.append(f"default='{column['default']}'")
                else:
                    options.append(f"default={column['default']}")
            
            # Check if it's a foreign key
            for fk in table['foreign_keys']:
                if fk['column'] == column['name']:
                    options.append(f"sa.ForeignKey('{fk['ref_table']}.{fk['ref_column']}')")
            
            # Combine options
            if options:
                col_def = f"    {col_name} = Column({col_type}, {', '.join(options)})"
            else:
                col_def = f"    {col_name} = Column({col_type})"
            
            model_lines.append(col_def)
        
        # Add a primary key if missing and requested
        if not has_primary_key and add_primary_key_if_missing:
            if any(col['name'] == 'id' for col in table['columns']):
                # Table has id but not marked as primary key
                id_col = next(col for col in table['columns'] if col['name'] == 'id')
                id_type = map_duckdb_to_sqlalchemy(id_col['type'])
                model_lines.append(f"    # SQLAlchemy workaround: Adding primary key to id column")
                model_lines.append(f"    id = Column({id_type}, primary_key=True)")
            else:
                # Table has no id column, add a virtual one for SQLAlchemy
                model_lines.append(f"    # SQLAlchemy workaround: Adding virtual primary key")
                model_lines.append(f"    id = Column(sa.Integer, primary_key=True)")
                model_lines.append(f"    __mapper_args__ = {{'primary_key': ['id']}}")
                model_lines.append(f"    # Note: This column doesn't exist in the database")
        
        # Add custom methods from existing model
        if class_name in existing_models:
            for method in existing_models[class_name]['methods']:
                model_lines.extend([line for line in method])
        
        model_lines.append("\n")  # Add a blank line after class
        model_definitions.append("\n".join(model_lines))
    
    # Add TABLE_SCHEMAS and TABLE_INDEXES
    table_schemas_dict = "TABLE_SCHEMAS = {\n"
    for table, schema in sql_schemas.items():
        # Escape single quotes in the schema
        escaped_schema = schema.replace("'", "\\'")
        table_schemas_dict += f"    '{table}': '''{escaped_schema}''',\n"
    table_schemas_dict += "}\n\n"
    
    table_indexes_dict = "TABLE_INDEXES = {\n"
    for table, indexes_list in sql_indexes.items():
        table_indexes_dict += f"    '{table}': [\n"
        for index in indexes_list:
            # Escape single quotes in the index
            escaped_index = index.replace("'", "\\'")
            table_indexes_dict += f"        '''{escaped_index}''',\n"
        table_indexes_dict += "    ],\n"
    table_indexes_dict += "}\n"
    
    # Combine everything
    return "\n".join(imports + model_definitions + [table_schemas_dict, table_indexes_dict])

def parse_create_table_schema(schema_str: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse a CREATE TABLE schema string into a dictionary of column definitions.
    
    Args:
        schema_str: CREATE TABLE SQL statement
        
    Returns:
        Dictionary mapping column names to their properties
    """
    # Extract table name and columns
    table_match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(\w+)\s*\((.*?)\)', schema_str, re.DOTALL)
    if not table_match:
        raise ValueError(f"Invalid CREATE TABLE statement: {schema_str}")
    
    table_name = table_match.group(1)
    columns_str = table_match.group(2)
    
    # Split into individual column definitions
    column_defs = []
    current_def = ""
    paren_level = 0
    
    for line in columns_str.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Count parentheses to handle nested definitions
        paren_level += line.count('(') - line.count(')')
        
        if current_def:
            current_def += " " + line
        else:
            current_def = line
        
        # If the definition is complete
        if paren_level == 0 and (line.endswith(',') or line == columns_str.strip().split('\n')[-1].strip()):
            column_defs.append(current_def.rstrip(','))
            current_def = ""
    
    # Process column definitions
    columns = {}
    for def_str in column_defs:
        # Skip constraints not related to columns
        if any(def_str.upper().startswith(kw) for kw in ('CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'UNIQUE', 'CHECK')):
            continue
        
        # Extract column name (handling quoted identifiers)
        name_match = re.match(r'(?:"([^"]+)"|(\w+))\s+(\w+)', def_str)
        if not name_match:
            continue
        
        col_name = name_match.group(1) or name_match.group(2)
        col_type = name_match.group(3)
        
        # Determine column properties
        not_null = 'NOT NULL' in def_str.upper()
        primary_key = 'PRIMARY KEY' in def_str.upper()
        default = None
        
        default_match = re.search(r'DEFAULT\s+([^,\s]+)', def_str, re.IGNORECASE)
        if default_match:
            default = default_match.group(1)
        
        columns[col_name] = {
            'type': col_type,
            'nullable': not not_null,
            'primary_key': primary_key,
            'default': default
        }
    
    return {'table_name': table_name, 'columns': columns}

def compare_schemas_and_generate_alters(db_schema: List[Dict[str, Any]], 
                                      code_schemas: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, List[str]]:
    """
    Compare database schema with code-defined schemas and generate ALTER statements.
    
    Args:
        db_schema: Schema extracted from the database
        code_schemas: Schemas defined in code (parsed from CREATE TABLE statements)
        
    Returns:
        Dictionary mapping table names to lists of ALTER statements
    """
    alter_statements = {}
    
    # Process each table from code schemas
    for table_name, code_schema in code_schemas.items():
        # Find matching table in DB schema
        db_table = next((t for t in db_schema if t['table_name'] == table_name), None)
        
        if db_table:
            # Table exists, check columns
            db_columns = {col['name']: col for col in db_table['columns']}
            code_columns = code_schema['columns']
            
            # Find columns in code but not in DB
            missing_columns = []
            for col_name, col_info in code_columns.items():
                if col_name not in db_columns:
                    missing_columns.append((col_name, col_info))
            
            if missing_columns:
                alter_statements[table_name] = []
                
                # Generate ALTER TABLE statements for each missing column
                for col_name, col_info in missing_columns:
                    # Build column definition
                    col_def = f"{col_name} {col_info['type']}"
                    
                    if not col_info['nullable']:
                        col_def += " NOT NULL"
                    
                    if col_info['default'] is not None:
                        col_def += f" DEFAULT {col_info['default']}"
                    
                    alter_statements[table_name].append(
                        f"ALTER TABLE {table_name} ADD COLUMN {col_def};"
                    )
        else:
            # Table doesn't exist, generate CREATE TABLE
            # Extract full CREATE TABLE statement from the original schema
            # This assumes you have access to the original CREATE TABLE statements
            # You might need to adapt this based on how you store/access the schemas
            alter_statements[table_name] = [
                f"-- Table {table_name} doesn't exist in the database"
                # Add CREATE TABLE statement if you have it
            ]
    
    return alter_statements

def bidirectional_sync(conn: duckdb.DuckDBPyConnection, 
                     schema_info: List[Dict[str, Any]], 
                     code_schemas: Dict[str, Dict[str, Dict[str, Any]]],
                     execute_alters: bool = False) -> Dict[str, List[str]]:
    """
    Perform bidirectional synchronization between database and code.
    
    Args:
        conn: Database connection
        schema_info: Schema extracted from database
        code_schemas: Schemas defined in code
        execute_alters: Whether to execute the ALTER statements
        
    Returns:
        Dictionary of ALTER statements (executed or not)
    """
    # Generate ALTER statements
    alter_statements = compare_schemas_and_generate_alters(schema_info, code_schemas)
    
    if not alter_statements:
        print("No schema changes needed. Database schema matches code-defined schemas.")
        return {}
    
    # Print ALTER statements
    print(f"Generated ALTER statements for {len(alter_statements)} tables:")
    for table, statements in alter_statements.items():
        print(f"\nTable: {table}")
        for stmt in statements:
            print(f"  {stmt}")
    
    # Execute ALTER statements if requested
    if execute_alters:
        print("\nExecuting ALTER statements...")
        for table, statements in alter_statements.items():
            for stmt in statements:
                try:
                    conn.execute(stmt)
                    print(f"  Executed: {stmt}")
                except Exception as e:
                    print(f"  Error executing {stmt}: {e}")
    
    return alter_statements

def extract_schema_from_code() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Extract schemas defined in code from various modules."""
    schemas = {}
    
    # You'll need to identify and locate all schema definitions in your code
    # This is just an example - adapt it to your project structure
    email_schema_path = Path('/Users/srvo/dewey/src/dewey/core/crm/email/imap_import_standalone.py')
    
    try:
        # This is a simplistic approach - in a real app you might need a more robust solution
        # like importing the modules and accessing their schema attributes
        if email_schema_path.exists():
            with open(email_schema_path, 'r') as f:
                content = f.read()
                # Extract EMAIL_SCHEMA using regex
                schema_match = re.search(r'EMAIL_SCHEMA\s*=\s*\'\'\'(.*?)\'\'\'', content, re.DOTALL)
                if schema_match:
                    email_schema = schema_match.group(1)
                    schema_info = parse_create_table_schema(email_schema)
                    schemas[schema_info['table_name']] = schema_info
    except Exception as e:
        print(f"Error extracting schema from {email_schema_path}: {e}")
    
    return schemas

def main(force_imports=False, add_primary_key_if_missing=True, sync_to_db=False, execute_alters=False):
    """Main function to extract schema and generate models."""
    try:
        # Load configuration
        config = load_config()
        
        # Connect to MotherDuck
        conn = get_motherduck_connection(config)
        
        # Extract schema from database
        schema_info = extract_schema(conn)
        print(f"Extracted schema information for {len(schema_info)} tables from database.")
        
        if sync_to_db:
            # Extract schemas defined in code
            code_schemas = extract_schema_from_code()
            print(f"Extracted {len(code_schemas)} schemas defined in code.")
            
            # Perform bidirectional sync
            alter_statements = bidirectional_sync(conn, schema_info, code_schemas, execute_alters)
            
            # Re-extract schema if we executed alters
            if execute_alters and alter_statements:
                schema_info = extract_schema(conn)
                print(f"Re-extracted schema after alterations for {len(schema_info)} tables.")
        
        # Output file path
        output_dir = Path('/Users/srvo/dewey/src/dewey/core/db')
        models_file = output_dir / 'models.py'
        
        # Parse existing models
        existing_models = parse_existing_models(str(models_file))
        
        # Create backup
        if models_file.exists():
            backup_file = str(models_file) + '.bak'
            with open(models_file, 'r') as src, open(backup_file, 'w') as dst:
                dst.write(src.read())
            print(f"Created backup of existing models file at {backup_file}")
        
        # Generate SQLAlchemy models
        model_code = generate_sqlalchemy_models(schema_info, existing_models, add_primary_key_if_missing)
        
        # Write to file
        with open(models_file, 'w') as f:
            f.write(model_code)
        
        print(f"Updated models file at {models_file}")
        
        # Format the file with Black
        try:
            subprocess.run(
                ["black", "--target-version", "py311", str(models_file)], 
                check=True,
                capture_output=True
            )
            print("Successfully formatted the generated file with Black.")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Formatting with Black failed: {e.stderr.decode() if e.stderr else str(e)}")
        except FileNotFoundError:
            print("Warning: Black formatter not found. Install with 'pip install black'.")
        
        print("Schema extraction and model updates completed successfully.")
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Update SQLAlchemy models from MotherDuck schema.")
    parser.add_argument("--force_imports", action="store_true", help="Force adding imports even if they might already exist.")
    parser.add_argument("--no_primary_key_workaround", action="store_false", dest="add_primary_key", 
                      help="Disable adding virtual primary keys for tables without them.")
    parser.add_argument("--sync_to_db", action="store_true", 
                      help="Synchronize database schema with schemas defined in code.")
    parser.add_argument("--execute_alters", action="store_true", 
                      help="Execute ALTER statements to update database schema (use with --sync_to_db).")
    
    args = parser.parse_args()
    
    sys.exit(main(force_imports=args.force_imports, 
                 add_primary_key_if_missing=args.add_primary_key,
                 sync_to_db=args.sync_to_db,
                 execute_alters=args.execute_alters))
