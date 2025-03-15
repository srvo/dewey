import os
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from llm.llm_utils import generate_response
from llm.api_clients.gemini import GeminiClient

class ScriptMover:
    """Refactor scripts into the Dewey project structure with LLM-assisted analysis."""
    
    def __init__(self, config_path: str = "config/script_mover.yaml"):
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.llm_client = DeepInfraClient()
        
        # Initialize directory structure from config
        self.root_path = Path(self.config['project_root'])
        self.module_paths = {
            module: self.root_path / path 
            for module, path in self.config['module_paths'].items()
        }

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {str(e)}") from e

    def _setup_logging(self) -> logging.Logger:
        """Configure logging system."""
        logger = logging.getLogger('ScriptMover')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        return logger

    def process_directory(self, target_dir: str) -> None:
        """Process all scripts in a directory and its subdirectories."""
        target_path = Path(target_dir)
        if not target_path.exists():
            raise ValueError(f"Directory not found: {target_dir}")

        script_count = 0
        
        for root, _, files in os.walk(target_dir):
            for file in files:
                if self._is_script_file(file):
                    script_path = Path(root) / file
                    self.logger.info(f"Processing {script_path}")
                    try:
                        self.process_script(script_path)
                        script_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to process {script_path}: {str(e)}")

        self.logger.info(f"Processed {script_count} scripts successfully")

    def _is_script_file(self, filename: str) -> bool:
        """Check if file matches script patterns from config."""
        return any(
            re.search(pattern, filename)
            for pattern in self.config['file_patterns']
        )

    def process_script(self, script_path: Path) -> None:
        """Process an individual script file."""
        # Analyze script content
        # Read first 50k characters as Gemini 1.5 Flash supports up to 1M tokens
        content = script_path.read_text()[:50000]
        analysis = self.analyze_script(content)
        
        # Determine target location
        target_path = self.determine_target_path(analysis)
        
        # Check for existing implementations
        if self.should_merge(analysis, target_path):
            self.merge_script(content, analysis, target_path)
        else:
            self.write_script(content, target_path)
        
        # Handle dependencies
        self.process_dependencies(analysis.get('dependencies', []))

    def analyze_script(self, content: str) -> Dict:
        """Use LLM to analyze script purpose and requirements."""
        prompt = f"""Analyze this Python script and respond in YAML format:
        - purpose: <short description>
        - category: [core/llm/pipeline/ui/utils]
        - dependencies: [list of external packages]
        - recommended_path: <project-relative path>
        
        Script content:
        {content[:10000]}"""  # Truncate to avoid token limits
        
        response = generate_response(
            prompt,
            model="gemini-1.5-flash",
            system_message="You are a Python code analysis assistant. Be concise and precise.",
            max_tokens=4096  # Using Gemini's higher token limit
        )
        
        try:
            return yaml.safe_load(response)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse LLM response: {str(e)}")

    def determine_target_path(self, analysis: Dict) -> Path:
        """Determine appropriate location in project structure."""
        # Use LLM recommendation or fallback to category-based path
        if 'recommended_path' in analysis:
            return self.root_path / analysis['recommended_path']
            
        category = analysis.get('category', 'utils')
        base_path = self.module_paths.get(category, self.module_paths['utils'])
        return base_path / 'migrated_scripts' / analysis.get('purpose', 'general') 

    def should_merge(self, analysis: Dict, target_path: Path) -> bool:
        """Check if similar functionality exists."""
        if not target_path.exists():
            return False
            
        existing_content = target_path.read_text()
        prompt = f"""Should these scripts be merged? Respond YES or NO.
        New script purpose: {analysis['purpose']}
        Existing script content: {existing_content[:5000]}"""
        
        response = generate_response(prompt).strip().upper()
        return response == "YES"

    def merge_script(self, new_content: str, analysis: Dict, target_path: Path) -> None:
        """Merge new script into existing implementation."""
        prompt = f"""Merge these scripts while maintaining project conventions:
        Existing script:
        {target_path.read_text()[:10000]}
        
        New script:
        {new_content[:10000]}
        
        Output ONLY the merged Python code."""
        
        merged_code = generate_response(prompt)
        target_path.write_text(merged_code)
        self.logger.info(f"Merged into {target_path}")

    def write_script(self, content: str, target_path: Path) -> None:
        """Write script to new location with proper formatting."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Format with project conventions
        formatted = self._format_with_conventions(content)
        target_path.write_text(formatted)
        self.logger.info(f"Created {target_path}")

    def _format_with_conventions(self, content: str) -> str:
        """Apply project formatting conventions."""
        prompt = f"""Reformat this Python code to match project conventions:
        - Google-style docstrings
        - Type hints
        - pep8 spacing
        - Split into logical functions
        Output ONLY the formatted code:
        
        {content}"""
        
        return generate_response(prompt)

    def process_dependencies(self, dependencies: List[str]) -> None:
        """Ensure required dependencies are in pyproject.toml."""
        existing_deps = self._read_current_dependencies()
        new_deps = [d for d in dependencies if d not in existing_deps]
        
        if new_deps:
            self._update_pyproject(new_deps)
            self.logger.info(f"Added new dependencies: {', '.join(new_deps)}")

    def _read_current_dependencies(self) -> List[str]:
        """Read current dependencies from pyproject.toml."""
        pyproject_path = self.root_path / 'pyproject.toml'
        with open(pyproject_path) as f:
            content = f.read()
            
        matches = re.findall(r'^    "([^"]+)",$', content, flags=re.MULTILINE)
        return [m.lower() for m in matches]

    def _update_pyproject(self, new_deps: List[str]) -> None:
        """Update pyproject.toml with new dependencies."""
        pyproject_path = self.root_path / 'pyproject.toml'
        with open(pyproject_path, 'a') as f:
            f.write('\n' + '\n'.join(f'    "{dep}",' for dep in new_deps))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate scripts to Dewey project structure")
    parser.add_argument("directory", help="Directory containing scripts to process")
    parser.add_argument("--config", default="config/script_mover.yaml", 
                      help="Configuration file path")
    args = parser.parse_args()
    
    mover = ScriptMover(args.config)
    mover.process_directory(args.directory)
