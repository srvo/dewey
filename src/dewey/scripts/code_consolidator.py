"""Advanced code consolidation tool using AST analysis and semantic clustering to identify
similar functionality across scripts and suggest canonical implementations.
"""

import argparse
import ast
import hashlib
import json
import logging
import os
import subprocess
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from tqdm import tqdm

from src.dewey.llm.llm_utils import generate_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TqdmHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()

    def emit(self, record) -> None:
        try:
            msg = self.format(record)
            tqdm.write(msg, end="")
        except Exception:
            self.handleError(record)

# Compact format without date/time
formatter = logging.Formatter("%(levelname)s: %(message)s")
handler = TqdmHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False  # Prevent duplicate output

class CodeConsolidator:
    """Identifies similar functionality across scripts using AST analysis and LLM-assisted clustering."""

    def __init__(self, root_dir: str = ".") -> None:
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.function_clusters = defaultdict(list)
        self.script_analysis = {}
        self.syntax_errors = []
        self.processed_files = set()
        self.checkpoint_file = self.root_dir / ".code_consol_checkpoint.json"
        self.llm_client = self._init_llm_clients()
        self.lock = threading.Lock()
        self._load_checkpoint()

    def _init_llm_clients(self) -> bool | None:
        """Initialize LLM client with retries and fallback."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Test actual LLM connectivity
                generate_response("test", max_tokens=1, timeout=10)
                logger.info("LLM client initialized successfully")
                return True
            except Exception as e:
                logger.warning(f"LLM setup error (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error("LLM initialization failed - semantic analysis disabled")
                    return None

    def analyze_directory(self) -> None:
        """Main analysis workflow with parallel processing."""
        scripts = self._find_script_files()
        logger.info(f"Found {len(scripts)} Python files to analyze")

        # Filter out already processed files
        new_scripts = [s for s in scripts if str(s) not in self.processed_files]
        logger.info(f"Resuming from checkpoint - {len(new_scripts)}/{len(scripts)} new files to process")

        # Process files in parallel with aggressive resource utilization
        with ThreadPoolExecutor(max_workers=os.cpu_count() * 4) as executor:
            futures = []
            for script_path in new_scripts:
                future = executor.submit(self._process_file, script_path)
                futures.append(future)

            # Process results with simplified progress and heartbeat logging
            with tqdm(total=len(futures), desc="Processing files", mininterval=2.0, maxinterval=10.0) as pbar:
                for i, future in enumerate(as_completed(futures)):
                    try:
                        functions, script_path = future.result(timeout=300)  # 5min timeout per file
                        if functions:
                            with self.lock:
                                self._cluster_functions(functions, script_path)
                                self.processed_files.add(str(script_path))
                                # Batch checkpoint every 10 files
                                if i % 10 == 0:
                                    self._save_checkpoint()
                        pbar.update(1)
                        pbar.set_postfix_str(f"Last processed: {script_path.name}", refresh=False)
                        
                        # Heartbeat logging every 30 seconds
                        if i % 5 == 0:
                            logger.info(f"Progress: {i+1}/{len(futures)} files | Current: {script_path.name}")
                    except Exception as e:
                        logger.error(f"Failed processing future: {e}")
                        self._save_checkpoint()  # Try to save state on any failure

        self._analyze_clusters()
        self._batch_process_semantic_hashes()

    def _find_script_files(self) -> list[Path]:
        """Find Python files in current directory and subdirectories, excluding venv."""
        excluded_dirs = {"test", ".venv", "venv", "docs", "deploy", "config", "ingest_data"}
        return [
            f for f in self.root_dir.glob("**/*.py")
            if not any(d in f.parts for d in excluded_dirs)
        ]

    def _extract_functions(self, file_path: Path) -> dict[str, dict]:
        """Parse AST to extract function definitions with context."""
        functions = {}
        try:
            with open(file_path, encoding="utf-8") as f:
                source = f.read()
                try:
                    tree = ast.parse(source, filename=str(file_path))

                    # Process AST nodes if parsing succeeded
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_info = {
                                "name": node.name,
                                "args": [a.arg for a in node.args.args],
                                "lineno": node.lineno,
                                "docstring": ast.get_docstring(node),
                                "complexity": self._calculate_complexity(node),
                                "file_hash": self._file_hash(file_path),
                                "context": self._analyze_function_context(node, source),
                            }
                            functions[node.name] = func_info
                    return functions

                except SyntaxError as e:
                    error_msg = f"{file_path}: {e.msg} (line {e.lineno})"
                    logger.warning(f"Skipped due to syntax error: {error_msg}")
                    self.syntax_errors.append(error_msg)
                    # Fall back to line-by-line parsing for basic function detection
                    return self._parse_functions_manually(source, file_path)
                except Exception as e:
                    logger.warning(f"Unexpected error parsing {file_path}: {e}")
                    return {}

        except Exception as e:
            logger.exception(f"Failed to process {file_path}: {e}")
            return {}

        return functions

    def _parse_functions_manually(self, source: str, file_path: Path) -> dict[str, dict]:
        """Fallback function parser that uses simple pattern matching."""
        functions = {}
        current_function = None
        in_function = False
        indent_level = 0

        for i, line in enumerate(source.split("\n")):
            try:
                # Look for function definitions
                if line.strip().startswith(("def ", "async def ")):
                    if "def " in line and "(" in line and "):" in line:
                        func_name = line.split("def ")[1].split("(")[0].strip()
                        params = line.split("(", 1)[1].split(")", 1)[0].strip()
                        functions[func_name] = {
                            "name": func_name,
                            "args": [p.strip() for p in params.split(",") if p.strip()],
                            "lineno": i+1,
                            "docstring": None,
                            "complexity": 1,  # Conservative estimate for fallback
                            "file_hash": self._file_hash(file_path),
                            "ast_fallback": True,
                            "context": "",  # Empty context for manual parsing
                        }
                        current_function = func_name
                        in_function = True
                        indent_level = len(line) - len(line.lstrip())
                        continue

                # Look for docstrings in function body
                if in_function and current_function:
                    stripped_line = line.strip()
                    current_indent = len(line) - len(line.lstrip())

                    # Check if we've left the function body
                    if current_indent <= indent_level and not stripped_line.startswith("@"):
                        in_function = False
                        current_function = None
                        continue

                    # Capture docstring
                    if stripped_line.startswith(('"""', "'''")):
                        if not functions[current_function]["docstring"]:
                            # Remove quotes and leading leading/trailing whitespace
                            doc = stripped_line[3:-3].strip() if len(stripped_line) > 6 else ""
                            functions[current_function]["docstring"] = doc
            except Exception as e:
                logger.debug(f"Error parsing line {i+1} in {file_path}: {e!s}")
                continue

        return functions

    def _cluster_functions(self, functions: dict[str, dict], script_path: Path) -> None:
        """Group similar functions using structural comparison first."""
        for name, details in functions.items():
            # Initial cluster key without semantic hash
            # Create cluster key with structural and semantic features
            structural_key = (
                name,
                len(details.get("args", [])),
                details.get("complexity", 1) // 5,
                hashlib.md5(details.get("context", "").encode()).hexdigest()[:8],
            )
            details["_structural_key"] = structural_key
            self.function_clusters[structural_key].append((script_path, details))

    def _semantic_hash(self, func_details: dict) -> str:
        """Generate hash based on function structure and LLM analysis."""
        if self.llm_client:
            prompt = f"Normalize this function signature for hashing:\nName: {func_details['name']}\nArgs: {func_details['args']}\nComplexity: {func_details['complexity']}"
            try:
                normalized = generate_response(prompt)
                return hashlib.md5(normalized.encode()).hexdigest()
            except Exception as e:
                logger.debug(f"LLM normalization failed: {e}")

        # Fallback to structural hash
        return hashlib.md5(
            f"{func_details['name']}-{len(func_details['args'])}-{func_details['complexity']}".encode(),
        ).hexdigest()

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.And, ast.Or)):
                complexity += 1
        return complexity

    def _file_hash(self, file_path: Path) -> str:
        """Calculate content hash of a file."""
        return hashlib.md5(file_path.read_bytes()).hexdigest()

    def _analyze_clusters(self) -> None:
        """Analyze function clusters to identify consolidation candidates."""
        consolidation_candidates = []

        for cluster_key, implementations in self.function_clusters.items():
            if len(implementations) > 1:
                # Find the canonical version (best example)
                canonical = max(implementations, key=lambda x: self._implementation_quality(x[1]))
                consolidation_candidates.append((cluster_key, implementations, canonical))

        self._present_findings(consolidation_candidates)
        self._report_syntax_errors()

    def _implementation_quality(self, func_details: dict) -> float:
        """Score function quality based on various metrics."""
        score = 0
        if func_details["docstring"]:
            score += 2
        score += min(func_details["complexity"], 10)  # Penalize over-complexity
        return score

    def _present_findings(self, candidates: list) -> None:
        """Interactive presentation of consolidation opportunities."""
        logger.info(f"\nFound {len(candidates)} consolidation opportunities:")

        for _cluster_key, implementations, (canonical_path, _canonical_details) in candidates:
            for path, _details in implementations:
                if path != canonical_path:
                    pass

            if input("\nShow diff? (y/N) ").lower() == "y":
                self._show_implementation_diff(implementations)

            if self.llm_client and input("Get consolidation suggestion? (y/N) ").lower() == "y":
                self._get_llm_consolidation_advice(implementations)

    def _show_implementation_diff(self, implementations: list) -> None:
        """Show diffs between implementations using system diff tool."""
        files = [str(i[0]) for i in implementations]
        try:
            subprocess.run(["diff", "-u", *files], check=False)
        except Exception as e:
            logger.exception(f"Diff failed: {e}")

    def _get_llm_consolidation_advice(self, implementations: list) -> None:
        """Use LLM to suggest consolidation strategy."""
        prompt = "Suggest how to consolidate these implementations into a canonical version:\n"
        for path, details in implementations:
            prompt += f"\n-- {path.name} --\n"
            prompt += f"Args: {details['args']}\n"
            prompt += f"Complexity: {details['complexity']}\n"
            if details["docstring"]:
                prompt += f"Docs: {details['docstring']}\n"

        try:
            self.llm_client.generate_content(prompt)
        except Exception as e:
            logger.exception(f"LLM consultation failed: {e}")

    def _report_syntax_errors(self) -> None:
        """Report files with syntax errors at end of analysis."""
        if self.syntax_errors:
            logger.info(f"\nFound {len(self.syntax_errors)} files with syntax errors:")
            for error in self.syntax_errors:
                logger.info(f"  - {error}")
        else:
            logger.info("\nNo files with syntax errors found")

    def generate_report(self) -> str:
        """Generate consolidation roadmap report."""
        report = [
            "# Code Consolidation Report",
            f"## Analysis of {self.root_dir}",
            f"- Files analyzed: {len(self.script_analysis)}",
            f"- Function clusters found: {len(self.function_clusters)}",
            "\n## Top Consolidation Opportunities:",
        ]

        # Add cluster details
        for cluster_key, implementations in self.function_clusters.items():
            if len(implementations) > 1:
                report.append(
                    f"\n### {cluster_key[0]} ({len(implementations)} implementations)\n"
                    f"**Best candidate**: {max(implementations, key=lambda x: self._implementation_quality(x[1]))[0].name}\n"
                    "**Locations**:\n" +
                    "\n".join(f"- {p.relative_to(self.root_dir)}: Line {d['lineno']}" for p, d in implementations),
                )

        return "\n".join(report)

    def _process_file(self, script_path: Path) -> tuple:
        """Process a single file with timeout and resource limits."""
        try:
            # Run in isolated process with proper Python path
            result = subprocess.run(
                [
                    "python", "-m", "src.dewey.scripts.code_consolidator",
                    "--process-file", str(script_path)
                ],
                capture_output=True,
                text=True,
                check=False,  # Don't raise on error
                timeout=300,
                env={**os.environ, "PYTHONPATH": ":".join(sys.path)}
            )
            
            if result.returncode != 0:
                logger.error(f"Subprocess failed for {script_path.name}: {result.stderr}")
                return {}, script_path
                
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.error(f"Invalid output from {script_path.name}")
                return {}, script_path
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout processing {script_path} - skipping")
            return {}, script_path
        except Exception as e:
            logger.exception(f"Failed to process {script_path}: {e}")
            return {}, script_path

    def _process_file_safe(self, script_path: Path) -> tuple:
        """Wrapper for isolated file processing."""
        try:
            # Format first, then analyze - sequential for each file
            self._preprocess_script(script_path)  # Blocking format
            logger.debug(f"Analyzing {script_path.name}...")
            functions = self._extract_functions(script_path)  # Then analysis
            return functions, str(script_path)
        except Exception as e:
            logger.debug(f"Error processing {script_path}: {e}")
            return {}, str(script_path)

    def _preprocess_script(self, script_path: Path) -> None:
        """Autoformat script using ruff and black."""
        logger.info(f"Formatting {script_path.name}...")
        try:
            # Run formatting with suppressed output unless there's an error
            ruff_proc = subprocess.run(
                ["ruff", "check", "--fix", "--unsafe-fixes", "--select", "ALL", str(script_path)],
                check=False,  # Don't raise on error
                timeout=120,
                capture_output=True,
                text=True
            )
            
            black_proc = subprocess.run(
                ["black", str(script_path)],
                check=False,  # Don't raise on error
                timeout=60,
                capture_output=True,
                text=True
            )
            
            # Only show output if there were errors
            if ruff_proc.returncode != 0:
                logger.debug(f"Ruff output for {script_path.name}:\n{ruff_proc.stderr}")
            if black_proc.returncode != 0:
                logger.debug(f"Black output for {script_path.name}:\n{black_proc.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.warning(f"Formatting timed out for {script_path.name}")
        except Exception as e:
            logger.warning(f"Formatting error for {script_path.name}: {e}")
        finally:
            logger.debug(f"Finished preprocessing {script_path.name}")

    def _analyze_function_context(self, node: ast.FunctionDef, source: str) -> str:
        """Analyze function context using NLP."""
        try:
            # Check if spaCy model is installed
            if not spacy.util.is_package("en_core_web_sm"):
                logger.warning("spaCy model 'en_core_web_sm' not installed. You can either:\n"
                               "1. Download just the model: python -m spacy download en_core_web_sm\n"
                               "2. Install spaCy from source with:\n"
                               "   uv install install -U pip setuptools wheel && "
                               "git clone https://github.com/explosion/spaCy && "
                               "cd spaCy && "
                               "uv pip install -r requirements.txt && "
                               "uv pip install --no-build-isolation --editable . && "
                               "python -m spacy download en_core_web_sm")
                return ""

            nlp = spacy.load("en_core_web_sm")

            # Get full function text
            func_text = ast.get_source_segment(source, node) or ""
            doc = nlp(func_text)

            # Extract key entities and verbs
            entities = {ent.lemma_.lower() for ent in doc.ents if ent.label_ in {"ORG", "PRODUCT", "NORP"}}
            verbs = {token.lemma_ for token in doc if token.pos_ == "VERB"}
            nouns = {chunk.root.lemma_ for chunk in doc.noun_chunks}

            # Combine and filter stopwords
            context_keywords = (entities | verbs | nouns) - STOP_WORDS
            return " ".join(sorted(context_keywords))
        except Exception as e:
            logger.debug(f"NLP analysis failed: {e!s}")
            return ""

    def _batch_process_semantic_hashes(self) -> None:
        """Batch process semantic hashes using LLM in parallel."""
        logger.info("Processing semantic hashes with LLM...")

        # Collect all unique function signatures needing hashes
        hash_queue = []
        for cluster_key, implementations in self.function_clusters.items():
            for _, details in implementations:
                if "semantic_hash" not in details:
                    hash_queue.append(details)

        # Process in large batches for maximum throughput
        batch_size = 100  # Aggressive batching for bulk processing
        with ThreadPoolExecutor(max_workers=4) as executor:
            for i in range(0, len(hash_queue), batch_size):
                batch = hash_queue[i:i+batch_size]
                futures = [executor.submit(self._semantic_hash, func) for func in batch]
                for future in as_completed(futures):
                    func, hash_val = future.result()
                    func["semantic_hash"] = hash_val

        # Rebuild clusters with semantic hashes
        new_clusters = defaultdict(list)
        for (struct_key, details_list) in self.function_clusters.items():
            for details in details_list:
                cluster_key = (*struct_key, details["semantic_hash"])
                new_clusters[cluster_key].append(details)
        self.function_clusters = new_clusters

    def _save_checkpoint(self) -> None:
        """Save current state to checkpoint file."""
        checkpoint_data = {
            "processed_files": list(self.processed_files),
            "function_clusters": [
                (key, [str(p) for p in paths])
                for key, paths in self.function_clusters.items()
            ],
            "syntax_errors": self.syntax_errors,
        }
        try:
            with self.lock, open(self.checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f)
        except Exception as e:
            logger.exception(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self) -> None:
        """Load previous state from checkpoint file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    data = json.load(f)
                self.processed_files = set(data["processed_files"])
                self.function_clusters = defaultdict(list, {
                    tuple(key): [Path(p) for p in paths]
                    for key, paths in data["function_clusters"]
                })
                self.syntax_errors = data["syntax_errors"]
                logger.info(f"Loaded checkpoint with {len(self.processed_files)} processed files")
            except Exception as e:
                logger.exception(f"Failed to load checkpoint: {e}")

def main() -> None:
    """Command line interface."""
    parser = argparse.ArgumentParser(description="Analyze and consolidate similar code functionality")
    parser.add_argument("--dir", default=".", help="Directory to analyze")
    parser.add_argument("--report", action="store_true", help="Generate HTML report")
    parser.add_argument("--process-file", help=argparse.SUPPRESS)  # Hidden arg for subprocesses
    
    args = parser.parse()

()

    if args.process_file:
        # Subprocess mode - just process one file and output JSON
        consolidator = CodeConsolidator()
        result = consolidator._process_file_safe(Path(args.process_file))
        print(json.dumps(result))
    else:
        # Normal mode
        consolidator = CodeConsolidator(args.dir)
        consolidator.analyze_directory()

    if args.report:
        report_path = Path(args.dir) / "code_consolidation_report.md"
        with open(report_path, "w") as f:
            f.write(consolidator.generate_report())
        logger.info(f"Report saved to {report_path}")

if __name__ == "__main__":
    main()
