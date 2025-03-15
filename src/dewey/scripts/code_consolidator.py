"""Advanced code consolidation tool using AST analysis and semantic clustering to identify
similar functionality across scripts and suggest canonical implementations.
"""

import argparse
import ast
import hashlib
import re
import json
import logging
import os
import subprocess
import sys
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, List, Tuple

import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from tqdm import tqdm

from dewey.llm.llm_utils import generate_response

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
    """Identifies similar functionality across scripts using AST analysis and vector similarity."""

    def __init__(self, root_dir: str = ".", config_path: str | None = None) -> None:
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.config = self._load_config(config_path)
        self.function_clusters = defaultdict(list)
        self.script_analysis = {}
        self.syntax_errors = []
        self.processed_files = set()
        self.checkpoint_file = self.root_dir / ".code_consolpointpoint.json"
        self.llm_client = self._init_llm_clients()
        self.lock = threading.Lock()
        self.vector_db = self._init_vector_db()
        self._load_checkpoint()

    def _load_config(self, config_path: str | None = None) -> dict:
        """Load configuration from YAML file with defaults."""
        import yaml
        from pathlib import Path

        default_config = {
            "pipeline": {
                "max_files": None,
                "excluded_dirs": ["test", ".venv", "venv", "docs", "deploy", "config", "ingest_data"],
                "file_patterns": [r"\.py$"],
                "cluster_threshold": 0.2,
                "max_cluster_size": 5,
                "min_cluster_size": 2
            },
            "vector_db": {
                "persist_dir": ".chroma_cache",
                "embedding_model": "all-MiniLM-L6-v2",
                "collection_name": "code_functions",
                "similarity_threshold": 0.85
            },
            "llm": {
                "default_model": "gemini-2.0-pro",
                "fallback_models": ["gemini-2.0-flash", "gemini-1.5-flash"],
                "temperature": 0.2,
                "max_retries": 3,
                "batch_size": 100,
                "max_workers": 4
            },
            "formatting": {
                "lint_timeout": 120,
                "formatters": [
                    {"command": ["ruff", "check", "--fix", "--unsafe-fixes", "--select", "ALL"]},
                    {"command": ["black"]}
                ]
            }
        }

        if config_path:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file) as f:
                    loaded_config = yaml.safe_load(f)
                    # Deep merge with default config
                    return self._deep_merge(default_config, loaded_config)
        return default_config

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Recursively merge two dictionaries."""
        for key, val in update.items():
            if isinstance(val, dict):
                base[key] = self._deep_merge(base.get(key, {}), val)
            else:
                base[key] = val
        return base

    def _init_vector_db(self):
        """Initialize vector database with error handling."""
        try:
            from dewey.utils.vector_db import VectorStore

            return VectorStore()
        except ImportError as e:
            logger.exception(f"Vector database disabled: {e}")
            return None
        except Exception as e:
            logger.exception(f"Failed to initialize vector database: {e}")
            return None

    def _init_llm_clients(self) -> bool | None:
        """Initialize LLM client with retries and fallback."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Test actual LLM connectivity
                generate_response("test")
                logger.info("LLM client initialized successfully")
                return True
            except Exception as e:
                logger.warning(
                    f"LLM setup error (attempt {attempt+1}/{max_retries}): {e}"
                )
                if attempt == max_retries - 1:
                    logger.exception(
                        "LLM initialization failed - semantic analysis disabled"
                    )
                    return None
        return None

    def analyze_directory(self) -> None:
        """Public interface to run full pipeline."""
        pipeline_report = self.execute_pipeline()
        print(self.generate_report(pipeline_report))
        self._save_checkpoint()

    def _find_script_files(self) -> list[Path]:
        """Find Python files using config patterns."""
        excluded_dirs = set(self.config["pipeline"]["excluded_dirs"])
        file_patterns = self.config["pipeline"]["file_patterns"]
        max_files = self.config["pipeline"]["max_files"]

        files = []
        pattern = "|".join(file_patterns)
        for f in self.root_dir.glob("**/*"):
            if any(re.search(pattern, f.name) for pattern in file_patterns):
                if not any(d in f.parts for d in excluded_dirs):
                    files.append(f)
                    if max_files and len(files) >= max_files:
                        break
        return files

    def _extract_functions(self, file_path: Path) -> dict[str, dict]:
        """Parse AST to extract function definitions with context."""
        functions = {}
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                source = f.read(50_000)  # Limit input size for problematic files
                
                # First try full AST parsing
                try:
                    tree = ast.parse(source, filename=str(file_path))
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
                    logger.warning(f"Syntax error: {error_msg}")
                    self.syntax_errors.append(f"{error_msg} - {str(e)}")
                except Exception as e:
                    logger.warning(f"Unexpected AST error parsing {file_path}: {e}")

                # Fallback parsing with more robust error handling
                return self._parse_functions_manually(source, file_path)

        except Exception as e:
            logger.exception(f"Failed to process {file_path}: {e}")
            return {}

        return functions

    def _parse_functions_manually(
        self, source: str, file_path: Path
    ) -> dict[str, dict]:
        """Fallback function parser that uses simple pattern matching."""
        functions = {}
        current_function = None
        in_function = False
        indent_level = 0
        line_buffer = []

        # Handle multi-line function definitions
        cleaned_source = source.replace("\r\n", "\n").replace("\r", "\n")
        lines = cleaned_source.split("\n")
        
        for i, line in enumerate(lines):
            line = line.expandtabs(4)  # Normalize tabs to spaces
            stripped_line = line.strip()
            
            try:
                # Handle multi-line function definitions
                if line_buffer:
                    line_buffer.append(line)
                    joined_line = " ".join([l.strip() for l in line_buffer])
                    if "):" in joined_line:
                        full_def = " ".join(line_buffer)
                        func_match = re.match(r"^(async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", full_def)
                        if func_match:
                            func_name = func_match.group(2)
                            params = full_def.split("(", 1)[1].split(")", 1)[0].strip()
                            functions[func_name] = {
                                "name": func_name,
                                "args": [p.strip() for p in params.split(",") if p.strip()],
                                "lineno": i + 1 - len(line_buffer) + 1,
                                "docstring": None,
                                "complexity": 2,  # Slightly higher estimate for multi-line
                                "file_hash": self._file_hash(file_path),
                                "ast_fallback": True,
                                "context": "",
                            }
                            current_function = func_name
                            in_function = True
                            indent_level = len(line_buffer[0]) - len(line_buffer[0].lstrip())
                        line_buffer = []
                        continue
                    elif len(line_buffer) > 3:  # Give up after 3 lines
                        line_buffer = []
                    continue

                # Look for function definitions with more flexible matching
                if re.match(r"^\s*(async\s+)?def\s+[a-zA-Z_]", line):
                    if "):" in line:
                        #-line-line definition
                        func_match = re.match(r"^\s*(async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.*)\)\s*:", line)
                        if func_match:
                            func_name = func_match.group(2)
                            params = func_match.group(3).strip()
                            functions[func_name] = {
                                "name": func_name,
                                "args": [p.strip() for p in params.split(",") if p.strip()],
                                "lineno": i + 1,
                                "docstring": None,
                                "complexity": 1,
                                "file_hash": self._file_hash(file_path),
                                "ast_fallback": True,
                                "context": "",
                            }
                            current_function = func_name
                            in_function = True
                            indent_level = len(line) - len(line.lstrip())
                    else:
                        # Start of multi-line definition
                        line_buffer.append(line)

                # Look for docstrings in function body
                if in_function and current_function:
                    stripped_line = line.strip()
                    current_indent = len(line) - len(line.lstrip())

                    # Check if we've left the function body
                    if current_indent <= indent_level and not stripped_line.startswith(
                        "@"
                    ):
                        in_function = False
                        current_function = None
                        continue

                    # Capture docstring
                    if stripped_line.startswith(('"""', "'''")):
                        if not functions[current_function]["docstring"]:
                            # Remove quotes and leading leading/trailing whitespace
                            doc = (
                                stripped_line[3:-3].strip()
                                if len(stripped_line) > 6
                                else ""
                            )
                            functions[current_function]["docstring"] = doc
            except Exception as e:
                logger.debug(f"Error parsing line {i+1} in {file_path}: {e!s}")
                continue

        return functions

    def _cluster_functions(self, functions: dict[str, dict], script_path: Path) -> None:
        """Group similar functions using vector similarity search."""
        if not self.vector_db:
            logger.warning(
                "Vector database not available - falling back to structural clustering"
            )
            self._fallback_cluster(functions, script_path)
            return

        for name, details in functions.items():
            context = details.get("context", "")
            func_id = f"{script_path.name}:{name}"

            # Store in vector DB
            self.vector_db.upsert_function(
                func_id,
                context,
                {
                    "name": name,
                    "args": ",".join(details["args"]) if details["args"] else "",
                    "complexity": details["complexity"],
                },
            )

            # Find similar existing functions
            similar_ids = self.vector_db.find_similar_functions(
                context, 
                threshold=self.config["vector_db"]["similarity_threshold"],
                top_k=self.config["pipeline"]["max_cluster_size"]
            )

            if similar_ids:
                # Use first similar function's cluster
                cluster_key = self._get_cluster_key_for_id(similar_ids[0])
                self.function_clusters[cluster_key].append((script_path, details))
            else:
                # Create new cluster using vector hash
                vector_hash = hashlib.md5(context.encode()).hexdigest()[:8]
                cluster_key = (name, vector_hash)
                self.function_clusters[cluster_key].append((script_path, details))

    def _get_cluster_key_for_id(self, func_id: str) -> tuple:
        """Find existing cluster key for a function ID."""
        for key, items in self.function_clusters.items():
            for path, details in items:
                if f"{path.name}:{details['name']}" == func_id:
                    return key
        return (func_id.split(":")[-1], "new_cluster")

    def _fallback_cluster(self, functions: dict[str, dict], script_path: Path) -> None:
        """Structural clustering fallback when vector DB is unavailable."""
        for name, details in functions.items():
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
                normalized = generate_response(prompt, timeout=10)
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
                canonical = max(
                    implementations, key=lambda x: self._implementation_quality(x[1])
                )
                consolidation_candidates.append(
                    (cluster_key, implementations, canonical)
                )

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

        for (
            _cluster_key,
            implementations,
            (canonical_path, _canonical_details),
        ) in candidates:
            for path, _details in implementations:
                if path != canonical_path:
                    pass

            if input("\nShow diff? (y/N) ").lower() == "y":
                self._show_implementation_diff(implementations)

            if (
                self.llm_client
                and input("Get consolidation suggestion? (y/N) ").lower() == "y"
            ):
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
                    "**Locations**:\n"
                    + "\n".join(
                        f"- {p.relative_to(self.root_dir)}: Line {d['lineno']}"
                        for p, d in implementations
                    ),
                )

        return "\n".join(report)

    def _process_file(self, script_path: Path) -> tuple:
        """Process a single file directly without subprocess."""
        try:
            functions = self._extract_functions(script_path)
            # Store raw file content for full-text analysis
            if self.vector_db:
                self._cluster_files(script_path)
            return functions, script_path
        except Exception as e:
            logger.debug(f"Error processing {script_path}: {e}")
            return {}, script_path

    def _cluster_files(self, script_path: Path) -> None:
        """Store and cluster full file contents."""
        try:
            content = script_path.read_text(encoding="utf-8", errors="replace")[:50000]
            file_id = str(script_path.relative_to(self.root_dir))
            
            self.vector_db.collection.upsert(
                ids=[file_id],
                embeddings=[self.vector_db.generate_embedding(content)],
                documents=[content],
                metadatas=[{
                    "path": str(script_path),
                    "type": "full_file",
                    "content_hash": hashlib.md5(content.encode()).hexdigest()
                }]
            )
        except Exception as e:
            logger.debug(f"Failed to cluster file {script_path}: {e}")

    def _process_file_safe(self, script_path: Path) -> tuple:
        """Process file with formatting and analysis."""
        try:
            self._preprocess_script(script_path)
            logger.debug(f"Analyzing {script_path.name}...")
            functions = self._extract_functions(script_path)
            return functions, script_path
        except Exception as e:
            logger.debug(f"Error processing {script_path}: {e}")
            return {}, script_path

    def _preprocess_script(self, script_path: Path) -> None:
        """Autoformat script using ruff and black."""
        logger.info(f"Formatting {script_path.name}...")
        try:
            # Run formatting with suppressed output unless there's an error
            ruff_proc = subprocess.run(
                [
                    "ruff",
                    "check",
                    "--fix",
                    "--unsafe-fixes",
                    "--select",
                    "ALL",
                    str(script_path),
                ],
                check=False,  # Don't raise on error
                timeout=120,
                capture_output=True,
                text=True,
            )

            black_proc = subprocess.run(
                ["black", str(script_path)],
                check=False,  # Don't raise on error
                timeout=60,
                capture_output=True,
                text=True,
            )

            # Only show output if there were errors
            if ruff_proc.returncode != 0:
                logger.debug(f"Ruff output for {script_path.name}:\n{ruff_proc.stderr}")
            if black_proc.returncode != 0:
                logger.debug(
                    f"Black output for {script_path.name}:\n{black_proc.stderr}"
                )

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
                logger.warning(
                    "spaCy model 'en_core_web_sm' not installed. You can either:\n"
                    "1. Download just the model: python -m spacy download en_core_web_sm\n"
                    "2. Install spaCy from source with:\n"
                    "   uv install install -U pip setuptools wheel && "
                    "git clone https://github.com/explosion/spaCy && "
                    "cd spaCy && "
                    "uv pip install -r requirements.txt && "
                    "uv pip install --no-build-isolation --editable . && "
                    "python -m spacy download en_core_web_sm"
                )
                return ""

            nlp = spacy.load("en_core_web_sm")

            # Get full function text
            func_text = ast.get_source_segment(source, node) or ""
            doc = nlp(func_text)

            # Extract key entities and verbs
            entities = {
                ent.lemma_.lower()
                for ent in doc.ents
                if ent.label_ in {"ORG", "PRODUCT", "NORP"}
            }
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
        batch_size = self.config["llm"]["batch_size"]
        with ThreadPoolExecutor(max_workers=self.config["llm"]["max_workers"]) as executor:
            for i in range(0, len(hash_queue), batch_size):
                batch = hash_queue[i : i + batch_size]
                futures = [executor.submit(self._semantic_hash, func) for func in batch]
                for future in as_completed(futures):
                    func, hash_val = future.result()
                    func["semantic_hash"] = hash_val

        # Rebuild clusters with semantic hashes
        new_clusters = defaultdict(list)
        for struct_key, details_list in self.function_clusters.items():
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

    def _isolated_step(self, step_func, *args, **kwargs) -> Dict[str, Any]:
        """Execute a pipeline step with error containment."""
        result = {"success": False, "error": None, "data": None}
        try:
            result["data"] = step_func(*args, **kwargs)
            result["success"] = True
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Step {step_func.__name__} failed: {e}", exc_info=True)
        return result

    def _load_files_step(self) -> Dict[str, Any]:
        """Step 1: Load files into ChromaDB with error isolation."""
        results = {"processed": 0, "failed": 0, "errors": []}
        for script_path in self._find_script_files():
            try:
                content = script_path.read_text(encoding="utf-8", errors="replace")[:50000]
                file_id = str(script_path.relative_to(self.root_dir))
                
                self.vector_db.collection.upsert(
                    ids=[file_id],
                    embeddings=[self.vector_db.generate_embedding(content)],
                    documents=[content],
                    metadatas=[{
                        "path": str(script_path),
                        "type": "full_file",
                        "content_hash": hashlib.md5(content.encode()).hexdigest()
                    }]
                )
                results["processed"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"{script_path}: {str(e)}")
        return results

    def _cluster_files_step(self) -> Dict[str, Any]:
        """Step 2: Cluster similar files."""
        try:
            file_ids = [str(f.relative_to(self.root_dir)) for f in self._find_script_files()]
            clusters = {}
            for file_id in file_ids:
                content = self.vector_db.collection.get(ids=[file_id])["documents"][0]
                similar = self.vector_db.collection.query(
                    query_texts=[content],
                    n_results=5,
                    include=["distances", "metadatas"]
                )
                clusters[file_id] = [
                    id for id, distance in zip(similar["ids"][0], similar["distances"][0])
                    if distance < 0.2
                ]
            return {"clusters": clusters}
        except Exception as e:
            logger.error(f"Clustering failed: {e}")
            return {"clusters": {}}

    def _process_cluster(self, cluster: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Process a single file cluster with error handling."""
        result = {
            "cluster": cluster,
            "functions": [],
            "consolidated": None,
            "errors": [],
            "linted": False
        }
        
        try:
            # Extract functions from all files in cluster
            for file_id in cluster:
                file_path = self.root_dir / file_id
                result["functions"].extend(self._extract_functions(file_path))
                
            # Generate consolidated code
            prompt = f"Consolidate these {len(result['functions'])} related functions:\n" + "\n".join(
                [f["context"] for f in result["functions"]]
            )
            consolidated = generate_response(
                prompt,
                model=self.config["llm"]["default_model"],
                temperature=self.config["llm"]["temperature"],
                system_message="Create comprehensive function with type hints and docstrings"
            )
            
            # Lint and format
            proc = subprocess.run(
                ["ruff", "format", "-"],
                input=consolidated.encode(),
                capture_output=True
            )
            result["consolidated"] = proc.stdout.decode() if proc.returncode == 0 else consolidated
            result["linted"] = proc.returncode == 0
            
        except Exception as e:
            result["errors"].append(str(e))
            
        return (len(result["errors"]) == 0, result)

    def execute_pipeline(self) -> Dict[str, Any]:
        """Execute full consolidation pipeline with isolated steps."""
        report = {
            "load_files": self._isolated_step(self._load_files_step),
            "cluster_files": self._isolated_step(self._cluster_files_step),
            "processing": {"clusters": [], "success": 0, "failed": 0},
            "overall_success": False
        }
        
        if report["cluster_files"]["success"]:
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(self._process_cluster, cluster)
                    for cluster in report["cluster_files"]["data"]["clusters"].values()
                ]
                
                for future in as_completed(futures):
                    success, result = future.result()
                    if success:
                        report["processing"]["success"] += 1
                    else:
                        report["processing"]["failed"] += 1
                    report["processing"]["clusters"].append(result)
        
        report["overall_success"] = (
            report["load_files"]["success"] and
            report["cluster_files"]["success"] and
            report["processing"]["failed"] == 0
        )
        
        return report

    def generate_report(self, pipeline_report: Dict[str, Any]) -> str:
        """Generate detailed consolidation report."""
        report = [
            "# Code Consolidation Pipeline Report",
            "## Pipeline Execution Summary",
            f"- Files loaded: {pipeline_report['load_files']['data']['processed']}",
            f"- File loading errors: {pipeline_report['load_files']['data']['failed']}",
            f"- Clusters identified: {len(pipeline_report['cluster_files']['data']['clusters'])}",
            f"- Clusters processed successfully: {pipeline_report['processing']['success']}",
            f"- Clusters failed: {pipeline_report['processing']['failed']}",
            "\n## Detailed Cluster Results:"
        ]
        
        for cluster in pipeline_report["processing"]["clusters"]:
            status = "SUCCESS" if not cluster["errors"] else "FAILED"
            report.append(
                f"\n### Cluster: {', '.join(cluster['cluster'])} ({status})"
                f"\n**Functions:** {len(cluster['functions'])}"
                f"\n**Errors:** {len(cluster['errors'])}"
                f"\n**Consolidated Code:**\n```python\n{cluster['consolidated']}\n```"
            )
            
        return "\n".join(report)

    def _load_checkpoint(self) -> None:
        """Load previous state from checkpoint file."""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file) as f:
                    data = json.load(f)
                self.processed_files = set(data["processed_files"])
                self.function_clusters = defaultdict(
                    list,
                    {
                        tuple(key): [Path(p) for p in paths]
                        for key, paths in data["function_clusters"]
                    },
                )
                self.syntax_errors = data["syntax_errors"]
                logger.info(
                    f"Loaded checkpoint with {len(self.processed_files)} processed files"
                )
            except Exception as e:
                logger.exception(f"Failed to load checkpoint: {e}")


def main() -> None:
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description="Analyze and consolidate similar code functionality"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to analyze (default: current directory)",
    )
    parser.add_argument("--report", action="store_true", help="Generate HTML report")
    parser.add_argument(
        "--max-files",
        type=int,
        help="Maximum number of files to process (for testing)"
    )
    parser.add_argument(
        "--process-file", help=argparse.SUPPRESS
    )  # Hidden arg for subprocesses

    args = parser.parse_args()

    if args.process_file:
        # Direct processing mode with JSON output
        consolidator = CodeConsolidator()
        functions, _ = consolidator._process_file_safe(Path(args.process_file))
        print(json.dumps((functions, str(args.process_file))))
    else:
        # Normal mode
        consolidator = CodeConsolidator(args.directory)
        consolidator.analyze_directory()

    if args.report:
        report_path = Path(args.dir) / "code_consolidation_report.md"
        with open(report_path, "w") as f:
            f.write(consolidator.generate_report())
        logger.info(f"Report saved to {report_path}")


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add project root to Python path
    # Add src directory to Python path
    src_dir = str(Path(__file__).parent.parent.parent.resolve())
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    main()
