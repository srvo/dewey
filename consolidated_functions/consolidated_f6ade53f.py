```python
import argparse
import ast
import datetime
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
import traceback
import yaml
from collections import defaultdict
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    Callable,
)

# Optional imports, handle missing dependencies gracefully
try:
    import spacy
    from spacy.util import is_package
except ImportError:
    spacy = None
    is_package = None

try:
    import ruff
except ImportError:
    ruff = None

try:
    import black
except ImportError:
    black = None

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None
    Settings = None

try:
    import tqdm
except ImportError:
    tqdm = None

# Constants
DEFAULT_CONFIG_PATH = "config.yaml"
DEFAULT_BATCH_SIZE = 10
DEFAULT_MAX_WORKERS = 4
DEFAULT_LLM_MODEL = "gpt-3.5-turbo"  # Or your preferred default
DEFAULT_SIMILARITY_THRESHOLD = 0.8
DEFAULT_MAX_CLUSTER_SIZE = 5
DEFAULT_MIN_CLUSTER_SIZE = 2
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60
DEFAULT_TIMEOUT_EXP = 120
DEFAULT_MAX_FILE = 100
DEFAULT_LINT_TIMEOUT = 60
DEFAULT_TEMPERATURE = 0.2
DEFAULT_VECTOR_DB_COLLECTION_NAME = "code_functions"
DEFAULT_VECTOR_DB_PATH = ".chroma_db"
DEFAULT_VECTOR_DB_SETTINGS = Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=DEFAULT_VECTOR_DB_PATH,
)
DEFAULT_FILE_PATTERNS = ["*.py"]
DEFAULT_EXCLUDED_DIRS = [".venv", "__pycache__"]
DEFAULT_FORMATTER = "black"
DEFAULT_LINTER = "ruff"
DEFAULT_TEST_COMMAND = "pytest"
DEFAULT_DEPLOY_COMMAND = "python deploy.py"
DEFAULT_COMMAND_TIMEOUT = 60
DEFAULT_COMMAND_TIMEOUT_EXP = 120
DEFAULT_SIMILARITY_THRESHOLD = 0.8
DEFAULT_MAX_CLUSTER_SIZE = 5
DEFAULT_MIN_CLUSTER_SIZE = 2
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 60
DEFAULT_TIMEOUT_EXP = 120
DEFAULT_MAX_FILE = 100
DEFAULT_LINT_TIMEOUT = 60
DEFAULT_TEMPERATURE = 0.2
DEFAULT_VECTOR_DB_COLLECTION_NAME = "code_functions"
DEFAULT_VECTOR_DB_PATH = ".chroma_db"
DEFAULT_VECTOR_DB_SETTINGS = Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory=DEFAULT_VECTOR_DB_PATH,
)
DEFAULT_FILE_PATTERNS = ["*.py"]
DEFAULT_EXCLUDED_DIRS = [".venv", "__pycache__"]
DEFAULT_FORMATTER = "black"
DEFAULT_LINTER = "ruff"
DEFAULT_TEST_COMMAND = "pytest"
DEFAULT_DEPLOY_COMMAND = "python deploy.py"
DEFAULT_COMMAND_TIMEOUT = 60
DEFAULT_COMMAND_TIMEOUT_EXP = 120


# Rate Limiter (Simplified) - Replace with a more robust implementation if needed
class RateLimiter:
    def __init__(self, calls: int = 10, period: int = 60):
        self.calls = calls
        self.period = period
        self.timestamps: List[float] = []

    def check_limit(self, model: str = None) -> bool:
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < self.period]
        if len(self.timestamps) < self.calls:
            self.timestamps.append(now)
            return True
        else:
            return False

    def wait(self):
        if tqdm:
            tqdm.write("Rate limit reached. Waiting...")
        else:
            print("Rate limit reached. Waiting...")
        time.sleep(self.period)
        self.timestamps = []  # Reset after waiting


# Vector DB (Simplified) - Replace with a more robust implementation if needed
class VectorStore:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection_name = config.get(
            "collection_name", DEFAULT_VECTOR_DB_COLLECTION_NAME
        )
        self.db_path = config.get("path", DEFAULT_VECTOR_DB_PATH)
        self.settings = config.get("settings", DEFAULT_VECTOR_DB_SETTINGS)
        self.client = None
        self.collection = None
        self.initialize()

    def initialize(self):
        try:
            if chromadb is None:
                raise ImportError("chromadb is not installed")
            self.client = chromadb.PersistentClient(settings=self.settings)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
            logging.info("Vector DB initialized successfully.")
        except ImportError as e:
            logging.error(f"Failed to initialize Vector DB: {e}")
            self.client = None
            self.collection = None
        except Exception as e:
            logging.exception(f"Unexpected error initializing Vector DB: {e}")
            self.client = None
            self.collection = None

    def generate_embedding(self, text: str) -> List[float]:
        """Placeholder for embedding generation.  Replace with actual embedding."""
        return [float(hashlib.md5(text.encode()).hexdigest()[:8], 16)]  # Dummy embedding

    def upsert_function(
        self,
        func_id: str,
        func_details: Dict[str, Any],
        script_path: str,
        vector_hash: str,
    ):
        if self.collection is None:
            return
        try:
            context = func_details.get("context", "")
            embedding = self.generate_embedding(context)
            self.collection.upsert(
                ids=[func_id],
                embeddings=[embedding],
                metadatas=[
                    {
                        "script_path": script_path,
                        "name": func_details.get("name", ""),
                        "complexity": func_details.get("complexity", 0),
                        "args": func_details.get("args", []),
                        "docstring": func_details.get("docstring", ""),
                        "vector_hash": vector_hash,
                    }
                ],
                documents=[context],
            )
            logging.debug(f"Upserted function {func_id} to vector DB.")
        except Exception as e:
            logging.error(f"Failed to upsert function {func_id} to vector DB: {e}")

    def find_similar_function(
        self, func_details: Dict[str, Any], top_k: int = 3
    ) -> List[Tuple[str, float]]:
        if self.collection is None:
            return []
        try:
            context = func_details.get("context", "")
            embedding = self.generate_embedding(context)
            results = self.collection.query(
                query_embeddings=[embedding], n_results=top_k
            )
            similar_functions = []
            for i in range(len(results["ids"][0])):
                func_id = results["ids"][0][i]
                distance = results["distances"][0][i]
                similar_functions.append((func_id, distance))
            return similar_functions
        except Exception as e:
            logging.error(f"Failed to find similar functions: {e}")
            return []

    def get_function_details(self, func_id: str) -> Optional[Dict[str, Any]]:
        if self.collection is None:
            return None
        try:
            results = self.collection.get(ids=[func_id])
            if results and results["metadatas"] and len(results["metadatas"][0]) > 0:
                metadata = results["metadatas"][0][0]
                return {
                    "script_path": metadata.get("script_path"),
                    "name": metadata.get("name"),
                    "complexity": metadata.get("complexity"),
                    "args": metadata.get("args"),
                    "docstring": metadata.get("docstring"),
                    "vector_hash": metadata.get("vector_hash"),
                }
            else:
                return None
        except Exception as e:
            logging.error(f"Failed to get function details for {func_id}: {e}")
            return None


# LLM Client (Simplified) - Replace with a real LLM client
class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.default_model = config.get("default_model", DEFAULT_LLM_MODEL)
        self.max_retries = config.get("max_retries", DEFAULT_MAX_RETRIES)
        self.rate_limiter = RateLimiter()  # Use the simplified rate limiter
        self.initialize()

    def initialize(self):
        # Placeholder for LLM client initialization
        logging.info("LLM client initialized (placeholder).")

    def generate_response(
        self, prompt: str, model: Optional[str] = None
    ) -> str:
        """Placeholder for LLM interaction. Replace with actual API calls."""
        model = model or self.default_model
        for attempt in range(1, self.max_retries + 1):
            if not self.rate_limiter.check_limit(model):
                self.rate_limiter.wait()
            try:
                # Simulate LLM response
                response = f"LLM Response for model {model} (attempt {attempt}): {prompt[:50]}..."
                return response
            except Exception as e:
                logging.error(
                    f"LLM request failed (attempt {attempt}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    raise  # Re-raise after max retries
        return ""  # Should not reach here due to exception handling


class CodeConsolidator:
    """
    A class to consolidate code implementations from a directory.

    This class analyzes Python files, extracts function definitions,
    clusters similar functions, and generates reports with consolidation
    recommendations.
    """

    def __init__(
        self, root_dir: str, config_path: str = DEFAULT_CONFIG_PATH
    ) -> None:
        """
        Initializes the CodeConsolidator.

        Args:
            root_dir: The root directory to search for Python files.
            config_path: Path to the configuration file (YAML).
        """
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.config_path = Path(config_path).expanduser().resolve()
        self.config: Dict[str, Any] = {}
        self.function_clusters: Dict[str, List[Tuple[str, Dict[str, Any]]]] = (
            defaultdict(list)
        )
        self.syntax_errors: List[str] = []
        self.processed_files: set[str] = set()
        self.checkpoint_file: Path = self.root_dir / ".code_consolidator_checkpoint.json"
        self.lock = None  # Placeholder for a lock if needed
        self.llm_client: Optional[LLMClient] = None
        self.vector_db: Optional[VectorStore] = None
        self._load_config(config_path)
        self._init_vector_db()
        self._init_llm_clients()
        self._load_checkpoint()

    def _load_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file with defaults.

        Args:
            config_path: Path to the configuration file.
        """
        default_config: Dict[str, Any] = {
            "pipeline": {
                "max_file": DEFAULT_MAX_FILE,
                "file_patterns": DEFAULT_FILE_PATTERNS,
                "excluded_dirs": DEFAULT_EXCLUDED_DIRS,
                "max_cluster_size": DEFAULT_MAX_CLUSTER_SIZE,
                "min_cluster_size": DEFAULT_MIN_CLUSTER_SIZE,
            },
            "vector_db": {
                "similarity_threshold": DEFAULT_SIMILARITY_THRESHOLD,
                "collection_name": DEFAULT_VECTOR_DB_COLLECTION_NAME,
                "path": DEFAULT_VECTOR_DB_PATH,
                "settings": DEFAULT_VECTOR_DB_SETTINGS,
            },
            "llm": {
                "default_model": DEFAULT_LLM_MODEL,
                "max_retries": DEFAULT_MAX_RETRIES,
                "batch_size": DEFAULT_BATCH_SIZE,
                "max_workers": DEFAULT_MAX_WORKERS,
                "temperature": DEFAULT_TEMPERATURE,
            },
            "formatter": {
                "command": DEFAULT_FORMATTER,
                "timeout": DEFAULT_TIMEOUT,
                "timeout_expire": DEFAULT_TIMEOUT_EXP,
            },
            "linter": {
                "command": DEFAULT_LINTER,
                "timeout": DEFAULT_LINT_TIMEOUT,
            },
            "test": {
                "command": DEFAULT_TEST_COMMAND,
                "timeout": DEFAULT_COMMAND_TIMEOUT,
                "timeout_expire": DEFAULT_COMMAND_TIMEOUT_EXP,
            },
            "deploy": {
                "command": DEFAULT_DEPLOY_COMMAND,
                "timeout": DEFAULT_COMMAND_TIMEOUT,
                "timeout_expire": DEFAULT_COMMAND_TIMEOUT_EXP,
            },
        }
        try:
            with open(config_path, "r") as f:
                loaded_config = yaml.safe_load(f)
                self.config = self._deep_merge(default_config, loaded_config)
                logging.info(f"Configuration loaded from {config_path}")
        except FileNotFoundError:
            self.config = default_config
            logging.warning(
                f"Configuration file not found at {config_path}. Using default configuration."
            )
        except yaml.YAMLError as e:
            logging.error(f"Error parsing configuration file: {e}")
            self.config = default_config
        except Exception as e:
            logging.error(f"Unexpected error loading config: {e}")
            self.config = default_config

    def _deep_merge(
        self, base: Dict[Any, Any], update: Dict[Any, Any]
    ) -> Dict[Any, Any]:
        """
        Recursively merge two dictionaries.

        Args:
            base: The base dictionary.
            update: The dictionary to merge into the base.

        Returns:
            The merged dictionary.
        """
        for key, val in update.items():
            if (
                key in base
                and isinstance(base[key], dict)
                and isinstance(val, dict)
            ):
                self._deep_merge(base[key], val)
            else:
                base[key] = val
        return base

    def _init_vector_db(self) -> None:
        """
        Initialize vector database with error handling.
        """
        try:
            self.vector_db = VectorStore(self.config["vector_db"])
            if self.vector_db.client is None:
                raise Exception("Vector DB initialization failed.")
        except (ImportError, Exception) as e:
            logging.exception(f"Failed to initialize vector database: {e}")
            self.vector_db = None
            logging.warning(
                "Vector database is disabled.  Function clustering will fall back to structural analysis."
            )

    def _init_llm_clients(self) -> None:
        """
        Initialize LLM client with retries and fallback.
        """
        try:
            self.llm_client = LLMClient(self.config["llm"])
        except Exception as e:
            logging.exception(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
            logging.warning("LLM client is disabled.  Consolidation advice will be limited.")

    def analyze_directory(self) -> Dict[str, Any]:
        """
        Public interface to run full pipeline.

        Returns:
            A dictionary containing the pipeline report.
        """
        pipeline_report = self.execute_pipeline()
        self._save_checkpoint()
        return self.generate_report(pipeline_report)

    def _find_script_files(self) -> List[Path]:
        """
        Find Python files using config patterns.

        Returns:
            A list of Path objects representing the Python files.
        """
        files: List[Path] = []
        file_patterns = self.config["pipeline"]["file_patterns"]
        excluded_dirs = self.config["pipeline"]["excluded_dirs"]
        max_file = self.config["pipeline"]["max_file"]

        for pattern in file_patterns:
            for f in self.root_dir.glob(f"**/{pattern}"):
                if (
                    f.is_file()
                    and f.name not in excluded_dirs
                    and not any(d in str(f.resolve()) for d in excluded_dirs)
                ):
                    files.append(f)
        return files[:max_file]

    def _extract_functions(self, file_path: Path) -> Dict[str, Dict[str, Any]]:
        """
        Parse AST to extract function definitions with context.

        Args:
            file_path: The path to the Python file.

        Returns:
            A dictionary where keys are function names and values are
            dictionaries containing function details.
        """
        functions: Dict[str, Dict[str, Any]] = {}
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        "file_path": str(file_path),
                        "lineno": node.lineno,
                        "docstring": ast.get_docstring(node) or "",
                        "args": [arg.arg for arg in node.args.args],
                        "context": "",  # Will be populated later
                        "complexity": self._calculate_complexity(node),
                    }
                    functions[node.name] = func_info
            for func_name, func_info in functions.items():
                try:
                    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                        source = f.read()
                    tree = ast.parse(source)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef) and node.name == func_name:
                            func_info["context"] = self._analyze_function_context(
                                node, source
                            )
                except Exception as e:
                    logging.warning(
                        f"Failed to analyze context for {func_name} in {file_path}: {e}"
                    )
            return functions
        except SyntaxError as e:
            error_msg = f"SyntaxError in {file_path} line {e.lineno}: {e.msg}"
            self.syntax_errors.append(error_msg)
            logging.error(error_msg)
            return {}
        except Exception as e:
            logging.exception(f"Failed to extract functions from {file_path}: {e}")
            return {}

    def _parse_functions_manually(
        self, source: str, file_path: Path
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fallback function parser that uses simple pattern matching.

        Args:
            source: The source code as a string.
            file_path: The path to the Python file.

        Returns:
            A dictionary where keys are function names and values are
            dictionaries containing function details.
        """
        functions: Dict[str, Dict[str, Any]] = {}
        try:
            lines = source.splitlines()
            line_buffer: List[str] = []
            current_function: Optional[str] = None
            in_function: bool = False
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if stripped_line.startswith("def "):
                    func_match = re.match(r"def\s+([a-zA-Z0-9_]+)\s*\((.*)\)\s*:", stripped_line)
                    if func_match:
                        func_name = func_match.group(1)
                        params = func_match.group(2)
                        params_list = [p.strip() for p in params.split(",")]
                        functions[func_name] = {
                            "file_path": str(file_path),
                            "lineno": i + 1,
                            "docstring": "",
                            "args": params_list,
                            "context": "",  # Will be populated later
                            "complexity": 1,  # Estimate complexity
                        }
                        current_function = func_name
                        in_function = True
                        line_buffer = [line]
                elif in_function:
                    if stripped_line and not stripped_line.startswith("#"):
                        indent_level = len(line) - len(line.lstrip())
                        if indent_level == 0 and current_function:
                            in_function = False
                            current_function = None
                        else:
                            line_buffer.append(line)
                    else:
                        line_buffer.append(line)
                if current_function:
                    docstring_match = re.match(r'"""(.*?)"""', "\n".join(line_buffer))
                    if docstring_match:
                        functions[current_function]["docstring"] = docstring_match.group(1).strip()
            for func_name, func_details in functions.items():
                try:
                    func_details["context"] = self._analyze_function_context(
                        None, source, func_name=func_name
                    )
                except Exception as e:
                    logging.warning(
                        f"Failed to analyze context for {func_name} in {file_path}: {e}"
                    )
            return functions
        except Exception as e:
            logging.exception(f"Fallback parsing failed for {file_path}: {e}")
            return {}

    def _cluster_functions(
        self, functions: Dict[str, Dict[str, Any]], script_path: str
    ) -> None:
        """
        Group similar functions using vector similarity search.

        Args:
            functions: A dictionary of function details.
            script_path: The path to the script file.
        """
        if not self.vector_db or not functions:
            return self._fallback_cluster(functions, script_path)

        for func_name, details in functions.items():
            func_id = f"{script_path}:{func_name}"
            vector_hash = hashlib.md5(details["context"].encode()).hexdigest()[:8]
            self.vector_db.upsert_function(func_id, details, script_path, vector_hash)
            similar_ids = self.vector_db.find_similar_function(details)
            cluster_key = self._get_cluster_key_for_id(similar_ids[0][0]) if similar_ids else func_id
            self.function_clusters[cluster_key].append((script_path, details))

    def _get_cluster_key_for_id(self, func_id: str) -> str:
        """
        Find existing cluster key for a function ID.

        Args:
            func_id: The function ID (e.g., "path/to/file.py:function_name").

        Returns:
            The cluster key (either an existing key or the func_id itself).
        """
        for cluster_key, implementations in self.function_clusters.items():
            for script_path, details in implementations:
                if f"{script_path}:{details['name']}" == func_id:
                    return cluster_key
        return func_id

    def _fallback_cluster(
        self, functions: Dict[str, Dict[str, Any]], script_path: str
    ) -> None:
        """
        Structural clustering fallback when vector DB is unavailable.

        Args:
            functions: A dictionary of function details.
            script_path: The path to the script file.
        """
        for func_name, details in functions.items():
            cluster_key = hashlib.md5(
                f"{details.get('name')}-{details.get('complexity')}-{details.get('args')}".encode()
            ).hexdigest()[:8]
            self.function_clusters[cluster_key].append((script_path, details))

    def _semantic_hash(self, func_details: Dict[str, Any]) -> str:
        """
        Generate hash based on function structure and LLM analysis.

        Args:
            func_details: Function details dictionary.

        Returns:
            A hash string.
        """
        try:
            normalized = f"{func_details['name']}-{len(func_details['args'])}-{func_details['complexity']}"
            if self.llm_client:
                prompt = f"Normalize the following function signature and context for semantic hashing:\nName: {func_details['name']}\nArgs: {func_details['args']}\ncomplexity: {func_details['complexity']}\nDocstring: {func_details['docstring']}\nContext:\n{func_details['context']}"
                signature = self.llm_client.generate_response(prompt)
                normalized += signature
            return hashlib.md5(normalized.encode()).hexdigest()
        except Exception as e:
            logging.error(f"Failed to generate semantic hash: {e}")
            return hashlib.md5(
                f"{func_details['name']}-{len(func_details['args'])}-{func_details['complexity']}".encode()
            ).hexdigest()

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """
        Calculate cyclomatic complexity of a function.

        Args:
            node: The AST node for the function.

        Returns:
            The cyclomatic complexity.
        """
        complexity = 1  # Start with 1 for the function itself
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With)):
                complexity += 1
        return complexity

    def _file_hash(self, file_path: Path) -> str:
        """
        Calculate content hash of a file.

        Args:
            file_path: The path to the file.

        Returns:
            The MD5 hash of the file content.
        """
        try:
            with open(file_path, "rb") as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()
        except Exception as e:
            logging.error(f"Failed to calculate file hash for {file_path}: {e}")
            return ""

    def _analyze_clusters(self) -> None:
        """
        Analyze function clusters to identify consolidation candidates.
        """
        for cluster_key, implementations in self.function_clusters.items():
            if len(implementations) >= self.config["pipeline"]["min_cluster_size"]:
                consolidation_candidate = []
                for script_path, func_details in implementations:
                    quality = self._implementation_quality(func_details)
                    consolidation_candidate.append((quality, (script_path, func_details)))
                consolidation_candidate.sort(key=lambda x: x[0], reverse=True)
                self._present_findings(consolidation_candidate)

    def _implementation_quality(self, func_details: Dict[str, Any]) -> float:
        """
        Score function quality based on various metrics.

        Args:
            func_details: Function details dictionary.

        Returns:
            A quality score (higher is better).
        """
        score = 0.0
        # Penalize high complexity
        score -= func_details["complexity"] * 0.1
        # Reward docstrings
        if func_details["docstring"]:
            score += 0.5
        # Reward more arguments (more general)
        score += len(func_details["args"]) * 0.2
        return max(0, score)

    def _present_findings(self, candidates: List[Tuple[float, Tuple[str, Dict[str, Any]]]]):
        """
        Interactive presentation of consolidation opportunities.

        Args:
            candidates: A list of (quality_score, (script_path, func_details)) tuples.
        """
        if not candidates:
            return
        print("\n--- Consolidation Opportunity ---")
        canonical_detail = candidates[0][1][1]
        canonical_path = candidates[0][1][0]
        print(f"\nCanonical Implementation: {canonical_path}:{canonical_detail['name']}")
        print(f"  Complexity: {canonical_detail['complexity']}")
        print(f"  Arguments: {canonical_detail['args']}")
        print(f"  Docstring: {canonical_detail['docstring'][:50]}...")
        for i, (quality, (path, detail)) in enumerate(candidates[1:]):
            print(f"\nImplementation {i+1}: {path}:{detail['name']}")
            print(f"  Complexity: {detail['complexity']}")
            print(f"  Arguments: {detail['args']}")
            print(f"  Docstring: {detail['docstring'][:50]}...")
            diff = input(
                "Show diff? (y/n, or 'q' to quit): "
            ).lower()
            if diff == "y":
                self._show_implementation_diff(
                    [(canonical_path, canonical_detail), (path, detail)]
                )
            elif diff == "q":
                sys.exit(0)
        action = input(
            "\nConsolidate (c), Skip (s), Get LLM advice (a), or Quit (q): "
        ).lower()
        if action == "c":
            # Placeholder for consolidation action
            print("Consolidation action not implemented.")
        elif action == "a":
            self._get_llm_consolidation_advice(
                [(path, detail) for _, (path, detail) in candidates]
            )
        elif action == "q":
            sys.exit(0)

    def _show_implementation_diff(self, implementations: List[Tuple[str, Dict[str, Any]]]):
        """
        Show diffs between implementations using system diff tool.

        Args:
            implementations: A list of (script_path, func_details) tuples.
        """
        try:
            if len(implementations) != 2:
                print("Need exactly two implementations for diff.")
                return
            path1, detail1 = implementations[0]
            path2, detail2 = implementations[1]
            with open("temp1.py", "w") as f:
                f.write(f"def {detail1['name']}({', '.join(detail1['args'])}):\n")
                if detail1["docstring"]:
                    f.write(f'    """{detail1["docstring"]}"""\n')
                f.write(f"    {detail1['context']}\n")
            with open("temp2.py", "w") as f:
                f.write(f"def {detail2['name']}({', '.join(detail2['args'])}):\n")
                if detail2["docstring"]:
                    f.write(f'    """{detail2["docstring"]}"""\n')
                f.write(f"    {detail2['context']}\n")
            subprocess.run(["diff", "-u", "temp1.py", "temp2.py"], check=True)
        except FileNotFoundError:
            print("Diff tool not found. Please install a diff tool (e.g., diff, colordiff).")
        except subprocess.CalledProcessError as e:
            print(f"Diff failed: {e}")
        except Exception as e:
            logging.exception(f"Failed to show diff: {e}")
        finally:
            for temp_file in ["temp1.py", "temp2.py"]:
                try:
                    os.remove(temp_file)
                except FileNotFoundError:
                    pass

    def _get_llm_consolidation_advice(
        self, implementations: List[Tuple[str, Dict[str, Any]]]
    ):
        """
        Use LLM to suggest consolidation strategy.

        Args:
            implementations: A list of (script_path, func_details) tuples.
        """
        if not self.llm_client:
            print("LLM client not initialized. Cannot provide advice.")
            return
        try:
            prompt = "You are a code consolidation expert.  Analyze the following function implementations and suggest a consolidation strategy.  Provide a concise summary of the similarities and differences, and then suggest a consolidated implementation.\n\n"
            for i, (path, detail) in enumerate(implementations):
                prompt += f"Implementation {i+1} (from {path}):\n"
                prompt += f"  Name: {detail['name']}\n"
                prompt += f"  Arguments: {detail['args']}\n"
                prompt += f"  Complexity: {detail['complexity']}\n"
                prompt += f"  Docstring: {detail['docstring']}\n"
                prompt += f"  Context:\n{detail['context']}\n--\n"
            prompt += "\nSuggest a consolidated implementation (code only, no explanation):"
            advice = self.llm_client.generate_response(prompt)
            print("\n--- LLM Consolidation Advice ---")
            print(advice)
        except Exception as e:
            logging.exception(f"Failed to get LLM consolidation advice: {e}")

    def _report_syntax_errors(self) -> None:
        """
        Report files with syntax errors at end of analysis.