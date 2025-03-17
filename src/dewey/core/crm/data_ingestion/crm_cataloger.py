#!/usr/bin/env python3
"""
CRM Component Cataloger
Generates structured JSON report for system comparison
"""

import os
import sys
import json
import logging
import hashlib
import datetime
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("crm_cataloger")

# ANSI color codes for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    NC = '\033[0m'  # No Color

class CRMCataloger:
    """Catalogs and validates CRM system components."""
    
    def __init__(self) -> None:
        """Initialize the cataloger with component definitions."""
        self.timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        self.report_file = f"crm_catalog_{self.timestamp}.json"
        
        # Define components to check - format: "filename:description::Class|function1|function2"
        self.components = [
            "csv_ingestor.py:Data Ingestion System::CSVIngestor|_map_row|ingest_file",
            "run_enrichment.py:Enrichment Pipeline::EnrichmentEngine|validate_api_docs|parse_args",
            "db_inspector.py:Database Inspector::configure_logging|get_db_connection|export_table_to_csv|add_contact_insights",
            "attio_client.py:Attio API Client::AttioClient",
            "onyx_client.py:Onyx API Client::OnyxClient",
            "enrichment_engine.py:Enrichment Engine::EnrichmentEngine|_process_contact|_store_enrichment|run_enrichment",
            "api_docs_manager.py:API Docs Manager::load_docs",
            "schema.py:Database Schema::Base|AttioContact|OnyxEnrichment"
        ]
        
        # Required environment variables
        self.required_env_vars = ["DB_URL", "ATTIO_API_KEY", "ONYX_API_KEY"]
        
        # Required database tables and columns
        self.required_tables = ["attio_contacts", "onyx_enrichments"]
        self.required_columns = [
            "attio_contacts.contact_id",
            "attio_contacts.email_addresses",
            "onyx_enrichments.contact_id",
            "onyx_enrichments.search_results"
        ]
        
        # Enrichment engine dependencies
        self.enrichment_deps = {
            "AttioClient": "attio_client.py",
            "OnyxClient": "onyx_client.py",
            "OnyxEnrichment": "schema.py"
        }
        
        # Component metrics
        self.component_metrics = {}

    def get_git_sha(self) -> str:
        """Get the current git SHA or return 'unknown'."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return "unknown"
        except Exception:
            return "unknown"

    def check_file_exists(self, filename: str) -> bool:
        """Check if a file exists."""
        return Path(filename).exists()

    def get_file_content(self, filename: str) -> str:
        """Get the content of a file as a string."""
        try:
            with open(filename, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
            return ""

    def count_lines(self, filename: str) -> int:
        """Count the number of lines in a file."""
        try:
            with open(filename, 'r') as f:
                return sum(1 for _ in f)
        except Exception as e:
            logger.error(f"Error counting lines in {filename}: {e}")
            return 0

    def get_file_hash(self, filename: str) -> str:
        """Calculate SHA256 hash of a file."""
        try:
            with open(filename, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {filename}: {e}")
            return "error"

    def get_last_modified(self, filename: str) -> str:
        """Get the last modified date of a file."""
        try:
            mtime = Path(filename).stat().st_mtime
            return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
        except Exception as e:
            logger.error(f"Error getting modification time for {filename}: {e}")
            return "unknown"

    def check_has_shebang(self, content: str) -> bool:
        """Check if file has a Python shebang."""
        return content.startswith("#!/usr/bin/env python3")

    def check_has_logging(self, content: str) -> bool:
        """Check if file imports logging."""
        return "import logging" in content

    def check_has_main_guard(self, content: str) -> bool:
        """Check if file has a main guard."""
        return 'if __name__ == "__main__":' in content

    def check_required_functions(self, content: str, functions: List[str]) -> Dict[str, bool]:
        """Check if required functions exist in the file."""
        return {func: func in content for func in functions}

    def check_missing_env_vars(self) -> List[str]:
        """Check for missing environment variables."""
        return [var for var in self.required_env_vars if not os.environ.get(var)]

    def verify_schema(self, schema_content: str) -> int:
        """Verify database schema and return error count."""
        errors = 0
        
        # Check for required tables
        for table in self.required_tables:
            if f"__tablename__ = '{table}'" not in schema_content:
                logger.error(f"Missing table in schema: {table}")
                errors += 1
        
        # Check for required columns
        for column_spec in self.required_columns:
            table, column = column_spec.split('.')
            # This is a simplified check - in a real implementation, you'd want to parse the schema more carefully
            if f"{column} = Column" not in schema_content or f"class {table}" not in schema_content:
                logger.error(f"Missing column in schema: {column_spec}")
                errors += 1
        
        return errors

    def verify_api_docs(self, api_docs_content: str) -> List[str]:
        """Verify API documentation and return warnings."""
        warnings = []
        if "Attio API" not in api_docs_content:
            warnings.append("Attio API documentation not found in api_docs_manager.py")
        if "Onyx_ingestion" not in api_docs_content:
            warnings.append("Onyx API documentation not found in api_docs_manager.py")
        return warnings

    def verify_enrichment_dependencies(self, enrichment_content: str) -> List[str]:
        """Verify enrichment engine dependencies and return missing ones."""
        return [f"{cls} (from {file})" for cls, file in self.enrichment_deps.items() 
                if cls not in enrichment_content]

    def verify_api_clients(self) -> List[str]:
        """Verify API client configurations and return warnings."""
        warnings = []
        attio_content = self.get_file_content("attio_client.py")
        onyx_content = self.get_file_content("onyx_client.py")
        
        if "ATTIO_API_KEY" not in attio_content:
            warnings.append("Attio client missing API key handling")
        if "ONYX_API_KEY" not in onyx_content:
            warnings.append("Onyx client missing API key handling")
        return warnings

    def generate_report(self) -> Dict[str, Any]:
        """Generate the full report as a dictionary."""
        logger.info("Generating comparison report...")
        
        # Check for missing files
        missing_files = []
        for component in self.components:
            filename = component.split(':')[0]
            if not self.check_file_exists(filename):
                missing_files.append(filename)
        
        if missing_files:
            logger.error("Missing required files:")
            for file in missing_files:
                logger.error(f"  - {file}")
            raise FileNotFoundError(f"Missing required files: {', '.join(missing_files)}")
        
        # Initialize report structure
        report = {
            "system_info": {
                "timestamp": self.timestamp,
                "git_sha": self.get_git_sha(),
                "components": []
            }
        }
        
        # Verify Python files and collect metrics
        logger.info("Verifying Python files meet coding standards...")
        for component in self.components:
            parts = component.split('::')
            file_desc = parts[0].split(':')
            filename = file_desc[0]
            description = file_desc[1]
            
            # Get required functions
            required_functions = parts[1].split('|') if len(parts) > 1 else []
            
            # Get file content
            content = self.get_file_content(filename)
            
            # Check standards
            has_shebang = self.check_has_shebang(content)
            has_logging = self.check_has_logging(content)
            has_main_guard = self.check_has_main_guard(content)
            
            if not has_shebang:
                logger.warning(f"{filename} is missing Python 3 shebang")
            if not has_logging:
                logger.warning(f"{filename} is missing logging import")
            if not has_main_guard:
                logger.warning(f"{filename} is missing main guard")
            
            # Count lines
            line_count = self.count_lines(filename)
            self.component_metrics[filename] = line_count
            
            # Add component to report
            report["system_info"]["components"].append({
                "name": filename,
                "description": description,
                "checks": {
                    "has_shebang": has_shebang,
                    "has_logging": has_logging,
                    "has_main_guard": has_main_guard,
                    "required_functions": self.check_required_functions(content, required_functions)
                },
                "lines_of_code": line_count,
                "file_hash": self.get_file_hash(filename)
            })
        
        # Check for missing environment variables
        missing_env_vars = self.check_missing_env_vars()
        if missing_env_vars:
            logger.warning("Missing environment variables:")
            for var in missing_env_vars:
                logger.warning(f"  - {var}")
            logger.warning("Please set these in your .env file")
        
        # Verify pipeline connectivity
        run_enrichment_content = self.get_file_content("run_enrichment.py")
        if "EnrichmentEngine().run" not in run_enrichment_content:
            logger.warning("Missing EnrichmentEngine invocation in run_enrichment.py")
        
        # Verify database schema
        logger.info("Verifying database schema...")
        schema_content = self.get_file_content("schema.py")
        schema_errors = self.verify_schema(schema_content)
        
        if schema_errors > 0:
            logger.error(f"Found {schema_errors} schema errors")
        else:
            logger.info("Database schema validation passed")
        
        # Verify API documentation
        logger.info("Verifying API documentation...")
        api_docs_content = self.get_file_content("api_docs_manager.py")
        api_warnings = self.verify_api_docs(api_docs_content)
        for warning in api_warnings:
            logger.warning(warning)
        
        # Validate Enrichment Engine integrations
        logger.info("Validating Enrichment Engine integrations...")
        enrichment_content = self.get_file_content("enrichment_engine.py")
        missing_deps = self.verify_enrichment_dependencies(enrichment_content)
        for dep in missing_deps:
            logger.error(f"Missing dependency: {dep}")
        
        # Verify API client configurations
        logger.info("Verifying API client configurations...")
        client_warnings = self.verify_api_clients()
        for warning in client_warnings:
            logger.warning(warning)
        
        # Add environment and schema info to report
        report["system_info"]["environment"] = {
            "missing_vars": missing_env_vars,
            "schema_errors": schema_errors
        }
        
        # Display metrics summary
        logger.info(f"{Colors.YELLOW}System Metrics Summary:{Colors.NC}")
        print(f"{'Component':<25} {'Missing Checks':<20} {'Lines':<10} {'Last Modified':<15}")
        
        for component in self.components:
            filename = component.split(':')[0]
            content = self.get_file_content(filename)
            
            checks_missing = []
            if not self.check_has_shebang(content):
                checks_missing.append("shebang")
            if not self.check_has_logging(content):
                checks_missing.append("logging")
            if not self.check_has_main_guard(content):
                checks_missing.append("main_guard")
            
            missing_str = ",".join(checks_missing) if checks_missing else "none"
            print(f"{filename:<25} {missing_str:<20} {self.component_metrics.get(filename, 0):<10} {self.get_last_modified(filename):<15}")
        
        return report

    def save_report(self, report: Dict[str, Any]) -> None:
        """Save the report to a JSON file."""
        with open(self.report_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {self.report_file}")

    def run(self) -> None:
        """Run the cataloger and generate the report."""
        try:
            report = self.generate_report()
            self.save_report(report)
            logger.info(f"{Colors.GREEN}CRM component catalog generated successfully{Colors.NC}")
        except Exception as e:
            logger.error(f"{Colors.RED}Error generating catalog: {e}{Colors.NC}")
            sys.exit(1)

if __name__ == "__main__":
    cataloger = CRMCataloger()
    cataloger.run() 