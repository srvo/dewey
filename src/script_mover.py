#!/usr/bin/env python3
import os
import time
import uuid
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import yaml
import ast
from llm.llm_utils import generate_response
from llm.api_clients.gemini import GeminiClient
from llm.api_clients.deepinfra import DeepInfraClient
from llm.exceptions import LLMError
import hashlib
from dewey.utils.pypi_search import search_pypi

class ScriptMover:
    """Refactor scripts into the Dewey project structure with LLM-assisted analysis."""
    
    def __init__(self, config_path: Optional[str] = None, fallback_to_deepinfra: bool = False):
        # Set default config path relative to project root
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "script_mover.yaml"
        self.config = self._load_config(config_path)
        self.logger = self._setup_logging()
        self.fallback_to_deepinfra = fallback_to_deepinfra
        self.llm_client = GeminiClient()
        self.checkpoint_path = Path(__file__).parent.parent / "config" / "script_checkpoints.yaml"
        self.processed_files = self._load_checkpoints()
        
        # Initialize directory structure from config
        self.root_path = Path(self.config['project_root'])
        self.module_paths = {
            module: self.root_path / path 
            for module, path in self.config['module_paths'].items()
        }

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            # Try to find config relative to project root if path doesn't exist
            config_path = Path(config_path)
            if not config_path.exists():
                config_path = Path(__file__).parent.parent / config_path
            
            with open(config_path, "r") as f:
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

    def _load_checkpoints(self) -> Dict:
        """Load processed files from checkpoint file."""
        if not self.checkpoint_path.exists():
            return {}
            
        with open(self.checkpoint_path) as f:
            return yaml.safe_load(f) or {}

    def _save_checkpoint(self, path: Path, content_hash: str) -> None:
        """Save processed file to checkpoint."""
        self.processed_files[str(path)] = content_hash
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_path, 'w') as f:
            yaml.safe_dump(self.processed_files, f)

    def process_directory(self, target_dir: str) -> None:
        """Process all scripts in a directory and its subdirectories."""
        target_path = Path(target_dir)
        if not target_path.exists():
            raise ValueError(f"Directory not found: {target_dir}")

        script_count = 0
        
        exclude_dirs = [re.compile(p) for p in self.config.get('exclude_patterns', [])]
        
        for root, _, files in os.walk(target_dir):
            # Skip excluded directories
            if any(pattern.search(root) for pattern in exclude_dirs):
                continue
                
            for file in files:
                script_path = Path(root) / file
                if self._is_script_file(file):
                    # Check if we've already processed this exact file
                    content_hash = hashlib.md5(script_path.read_bytes()).hexdigest()
                    if str(script_path) in self.processed_files:
                        if self.processed_files[str(script_path)] == content_hash:
                            self.logger.info(f"Skipping already processed file: {script_path}")
                            continue
                            
                    self.logger.info(f"Processing {script_path}")
                    try:
                        self.process_script(script_path)
                        script_count += 1
                        self._save_checkpoint(script_path, content_hash)
                    except Exception as e:
                        self.logger.error(f"Fatal error processing {script_path}: {str(e)}")
                        raise  # Re-raise to halt execution

        self.logger.info(f"Processed {script_count} scripts successfully")

    def _is_script_file(self, filename: str) -> bool:
        """Check if file matches script patterns from config."""
        return any(
            re.search(pattern, filename)
            for pattern in self.config['file_patterns']
        ) and not filename.lower().endswith(('.exe', '.dll', '.so', '.dylib'))

    def process_script(self, script_path: Path) -> None:
        """Process an individual script file with audit tracking."""
        audit_entry = {
            'source_path': str(script_path),
            'status': 'pending',
            'timestamp': time.time()
        }
        
        try:
            content = script_path.read_text(encoding='utf-8')[:50000]
        except UnicodeDecodeError:
            self.logger.warning(f"Skipping binary file {script_path}")
            audit_entry['status'] = 'skipped'
            audit_entry['reason'] = 'binary_file'
            self._record_migration(audit_entry)
            return

        try:
            analysis = self.analyze_script(content)
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to analyze {script_path}: {str(e)}")
            audit_entry['status'] = 'error'
            audit_entry['reason'] = 'analysis_failed'
            self._record_migration(audit_entry)
            return
        
        # Determine target location and validate it's within project structure
        target_path = self.determine_target_path(analysis)
        
        # Ensure target path is within project boundaries
        if not self._is_valid_target_path(target_path):
            unmapped_dir = self.root_path / 'unmapped_scripts'
            target_path = unmapped_dir / script_path.name
            audit_entry['notes'] = 'Target path outside project scope'
        
        # Check for existing implementations
        try:
            if self.should_merge(analysis, target_path):
                self.merge_script(content, analysis, target_path)
                self.logger.info(f"✅ Merged {script_path} into {target_path} [Category: {analysis.get('category', 'unclassified')}]")
                audit_entry['status'] = 'merged'
            else:
                self.write_script(content, target_path)
                self.logger.info(f"📄 Created {target_path} [Category: {analysis.get('category', 'unclassified')}]")
                audit_entry['status'] = 'moved'
            
            audit_entry['target_path'] = str(target_path)
            audit_entry['category'] = analysis.get('category', 'unclassified')
        except Exception as e:
            audit_entry['status'] = 'failed'
            audit_entry['error'] = str(e)
            self.logger.error(f"Failed to process {script_path}: {str(e)}")
        
        self._record_migration(audit_entry)
        
        # Handle dependencies
        self.process_dependencies(analysis.get('dependencies', []))

    def analyze_script(self, content: str) -> Dict:
        """Use LLM to analyze script purpose and requirements."""
        prompt = f"""ANALYZE THIS PYTHON SCRIPT AND RESPOND IN YAML FORMAT ONLY:
        ---
        purpose: <short description>
        category: [core/llm/pipeline/ui/utils]
        dependencies: 
          - "package1"
          - "package2[extra]"
        recommended_path: <project-relative path>
        ---
        
        Script content:
        {content[:10000]}"""
        
        # Try all configured Gemini models before falling back
        models = self.config['llm_settings']['models']
        cooldown_minutes = self.config['llm_settings'].get('cooldown_minutes', 5)
        self.llm_client.rate_limiter.cooldown_minutes = cooldown_minutes
        
        # Try primary model just once before falling back
        try:
            available_models = [m for m in self.config['llm_settings']['models']
                              if not self.llm_client.rate_limiter.is_in_cooldown(m)]
            model = available_models[0] if available_models else None
            
            if model:
                response = generate_response(
                    prompt,
                    model=model,
                    system_message="You are a Python code analysis assistant. Be concise and precise.",
                    fallback_client=DeepInfraClient() if self.fallback_to_deepinfra else None
                )
                # Reset cooldown if successful
                if model in self.llm_client.rate_limiter.cooldowns:
                    del self.llm_client.rate_limiter.cooldowns[model]
            else:
                raise LLMError("All primary models in cooldown")
                
        except LLMError as e:
            if not self.fallback_to_deepinfra:
                raise
                
            self.logger.warning(f"Primary model failed: {str(e)}, switching to DeepInfra fallback")
            response = generate_response(
                prompt,
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                system_message="You are a Python code analysis assistant. Be concise and precise.",
                client=DeepInfraClient()
            )
        
        try:
            # Use shared YAML parsing utility
            parsed = parse_llm_yaml_response(response, self.logger)
            
            # Normalize dependencies list
            if 'dependencies' in parsed:
                if isinstance(parsed['dependencies'], str):
                    parsed['dependencies'] = [d.strip() for d in parsed['dependencies'].split(',')]
                parsed['dependencies'] = [d.strip('"\' ') for d in parsed['dependencies']]
                
            return parsed
        except Exception as e:
            self.logger.error(f"LLM Response that failed parsing:\n{response}")
            raise ValueError(f"Failed to parse LLM response: {str(e)}") from e

    def determine_target_path(self, analysis: Dict) -> Path:
        """Determine appropriate location in project structure."""
        try:
            # Use LLM recommendation or fallback to category-based path
            if 'recommended_path' in analysis:
                # Validate recommended path is relative and has a filename
                rec_path = Path(analysis['recommended_path'])
                if rec_path.is_absolute() or rec_path.suffix == '':
                    raise ValueError("Invalid recommended path format")
                target_path = self.root_path / rec_path
            else:
                category = analysis.get('category', 'unclassified')
                base_path = self.module_paths.get(category, self.module_paths['utils'])
                purpose = analysis.get('purpose', 'migrated_script').replace(' ', '_').lower()
                target_path = base_path / 'migrated_scripts' / f"{purpose}.py"

            # Ensure path has valid filename components
            target_path = target_path.with_name(target_path.name.replace(' ', '_'))
            
            # Add UUID to prevent collisions
            unique_id = str(uuid.uuid4())[:8]
            return target_path.with_stem(f"{target_path.stem}_{unique_id}")
        except Exception as e:
            self.logger.warning(f"Path determination failed: {str(e)}, using fallback location")
            return self.root_path / 'unmapped_scripts' / f"migrated_{uuid.uuid4().hex[:8]}.py"

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
        
        try:
            # Format with project conventions
            formatted = self._format_with_conventions(content)
            target_path.write_text(formatted)
            self.logger.info(f"Created {target_path}")
        except Exception as e:
            # If formatting failed, write original content with warning
            self.logger.warning(f"⚠️ Formatting failed, writing original content to {target_path}")
            self.logger.debug(f"Formatting error: {str(e)}")
            target_path.write_text(f"# Formatting failed: {str(e)}\n\n{content}")

    def _format_with_conventions(self, content: str) -> str:
        """Apply project formatting conventions with validation."""
        prompt = f"""Reformat this Python code to match project conventions:
        - Google-style docstrings
        - Type hints
        - PEP8 spacing
        - Split into logical functions
        - Keep all original functionality
        
        Enclose the response in triple backticks.
        Output ONLY the formatted code, no explanations.
        
        Original code:
        {content}"""
        
        try:
            response = generate_response(prompt)
            # Extract code from between first ```python and last ```
            code_start = response.find('```python') + len('```python')
            code_end = response.rfind('```')
            if code_start == -1 or code_end == -1:
                raise SyntaxError("Code block markers missing")
                
            formatted_code = response[code_start:code_end].strip()
            
            # Validate syntax before returning
            ast.parse(formatted_code)
            return formatted_code
        except (SyntaxError, LLMError) as e:
            self.logger.warning(f"Formatting validation failed: {str(e)}")
            # Return original content if formatting failed validation
            return content

    def process_dependencies(self, dependencies: List[str]) -> None:
        """Ensure required dependencies are in pyproject.toml."""
        existing_deps = self._read_current_dependencies()
        
        # Filter and validate dependencies
        valid_deps = []
        for dep in dependencies:
            # Reject ibis-framework[duckdb] pattern explicitly
            if re.match(r'ibis-framework\[.*\]', dep):
                self.logger.warning(f"Skipping invalid dependency format: {dep}")
                continue
                
            # Check if valid PyPI package
            if not self._validate_dependency(dep):
                self.logger.warning(f"Skipping unverified dependency: {dep}")
                continue
                
            if dep not in existing_deps:
                valid_deps.append(dep)
        
        if valid_deps:
            self._update_pyproject(valid_deps)
            self.logger.info(f"Added validated dependencies: {', '.join(valid_deps)}")

    def _validate_dependency(self, dep: str) -> bool:
        """Verify dependency exists on PyPI or is a standard library module."""
        import sys
        
        # First check if it's a standard library module
        if dep in sys.stdlib_module_names:
            self.logger.info(f"Skipping standard library module: {dep}")
            return True
            
        # Then check PyPI
        from dewey.utils.pypi_search import search_pypi
        try:
            return search_pypi(dep) is not None
        except Exception as e:
            self.logger.error(f"Dependency validation failed for {dep}: {str(e)}")
            return False

    def _read_current_dependencies(self) -> List[str]:
        """Read current dependencies from pyproject.toml."""
        pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
        
        try:
            import tomli
            with open(pyproject_path, "rb") as f:
                data = tomli.load(f)
            return [dep.lower() for dep in data["project"]["dependencies"]]
        except ImportError:
            # Fallback to regex parsing if tomli not available
            with open(pyproject_path) as f:
                content = f.read()
            matches = re.findall(r'^\s*"([^"]+)",\s*$', content, flags=re.MULTILINE)
            return [m.lower() for m in matches]

    def _update_pyproject(self, new_deps: List[str]) -> None:
        """Update pyproject.toml with new dependencies using proper TOML handling."""
        pyproject_path = Path(__file__).parent.parent / 'pyproject.toml'
        
        try:
            import tomli
            import tomli_w
            # Read existing content
            with open(pyproject_path, "rb") as f:
                data = tomli.load(f)
            
            # Get current deps and add new ones
            current_deps = data["project"]["dependencies"]
            updated_deps = current_deps + [f'"{dep}"' for dep in new_deps if f'"{dep}"' not in current_deps]
            
            # Write back with tomli-w to maintain formatting
            with open(pyproject_path, "wb") as f:
                tomli_w.dump(data, f)
        except ImportError:
            # Fallback to append mode if tomli-w not available
            with open(pyproject_path, 'a') as f:
                f.write('\n' + '\n'.join(f'    "{dep}",' for dep in new_deps))

    def _is_valid_target_path(self, path: Path) -> bool:
        """Check if target path is within project structure."""
        try:
            path.resolve().relative_to(self.root_path.resolve())
            return True
        except ValueError:
            return False

    def _record_migration(self, audit_entry: dict) -> None:
        """Record migration outcome in audit log."""
        audit_log = self.root_path / 'config' / 'script_mappings.yaml'
        
        # Ensure directory exists
        audit_log.parent.mkdir(parents=True, exist_ok=True)
        
        existing = []
        if audit_log.exists():
            existing = yaml.safe_load(audit_log.read_text()) or []
        
        existing.append(audit_entry)
        
        with open(audit_log, 'w') as f:
            yaml.safe_dump(existing, f, sort_keys=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate scripts to Dewey project structure")
    parser.add_argument("directory", help="Directory containing scripts to process")
    parser.add_argument("--config", default="config/script_mover.yaml", 
                      help="Configuration file path")
    parser.add_argument("--fallback-to-deepinfra", action="store_true",
                      help="Use DeepInfra as fallback when Gemini API is exhausted")
    args = parser.parse_args()
    
    mover = ScriptMover(args.config, args.fallback_to_deepinfra)
    mover.process_directory(args.directory)
