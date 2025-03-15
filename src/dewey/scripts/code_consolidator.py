"""
Advanced code consolidation tool using AST analysis and semantic clustering to identify
similar functionality across scripts and suggest canonical implementations.
"""

import argparse
import ast
import logging
import hashlib
import json
import threading
import subprocess
import spacy
from spacy.lang.en.stop_words import STOP_WORDS
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from dewey.llm.llm_utils import generate_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class TqdmHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg, end='')
        except Exception:
            self.handleError(record)

# Compact format without date/time
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler = TqdmHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False  # Prevent duplicate output

class CodeConsolidator:
    """Identifies similar functionality across scripts using AST analysis and LLM-assisted clustering"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.function_clusters = defaultdict(list)
        self.script_analysis = {}
        self.syntax_errors = []
        self.processed_files = set()
        self.checkpoint_file = self.root_dir / ".code_consol_checkpoint.json"
        self.llm_client = self._init_llm_clients()
        self.lock = threading.Lock()
        self._load_checkpoint()
        
    def _init_llm_clients(self):
        """Initialize LLM client through llm_utils"""
        try:
            # Will use generate_response from llm_utils which handles client management
            return True
        except Exception as e:
            logger.warning(f"LLM setup error: {e}")
            return None

    def analyze_directory(self):
        """Main analysis workflow with parallel processing"""
        scripts = self._find_script_files()
        logger.info(f"Found {len(scripts)} Python files to analyze")
        
        # Filter out already processed files
        new_scripts = [s for s in scripts if str(s) not in self.processed_files]
        logger.info(f"Resuming from checkpoint - {len(new_scripts)}/{len(scripts)} new files to process")
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for script_path in new_scripts:
                future = executor.submit(self._process_file, script_path)
                futures.append(future)
                
            # Process results as they complete with nested progress bars
            with tqdm(total=len(futures), desc="Overall progress", position=0) as pbar:
                for future in tqdm(as_completed(futures), total=len(futures), 
                                 desc="Analyzing files", position=1, leave=False):
                    functions, script_path = future.result()
                    if functions:
                        with self.lock:
                            self._cluster_functions(functions, script_path)
                            self.processed_files.add(str(script_path))
                            self._save_checkpoint()
                    pbar.update(1)
                
        self._analyze_clusters()
        self._batch_process_semantic_hashes()
        
    def _find_script_files(self) -> List[Path]:
        """Find Python files in current directory and subdirectories, excluding venv"""
        excluded_dirs = {'test', '.venv', 'venv', 'docs', 'deploy', 'config', 'ingest_data'}
        return [
            f for f in self.root_dir.glob('**/*.py')
            if not any(d in f.parts for d in excluded_dirs)
        ]

    def _extract_functions(self, file_path: Path) -> Dict[str, dict]:
        """Parse AST to extract function definitions with context"""
        functions = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
                try:
                    tree = ast.parse(source, filename=str(file_path))
                    
                    # Process AST nodes if parsing succeeded
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_info = {
                                'name': node.name,
                                'args': [a.arg for a in node.args.args],
                                'lineno': node.lineno,
                                'docstring': ast.get_docstring(node),
                                'complexity': self._calculate_complexity(node),
                                'file_hash': self._file_hash(file_path),
                                'context': self._analyze_function_context(node, source)
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
            logger.error(f"Failed to process {file_path}: {e}")
            return {}
            
        return functions

    def _parse_functions_manually(self, source: str, file_path: Path) -> Dict[str, dict]:
        """Fallback function parser that uses simple pattern matching"""
        functions = {}
        current_function = None
        in_function = False
        indent_level = 0
        
        for i, line in enumerate(source.split('\n')):
            try:
                # Look for function definitions
                if line.strip().startswith(('def ', 'async def ')):
                    if 'def ' in line and '(' in line and '):' in line:
                        func_name = line.split('def ')[1].split('(')[0].strip()
                        params = line.split('(', 1)[1].split(')', 1)[0].strip()
                        functions[func_name] = {
                            'name': func_name,
                            'args': [p.strip() for p in params.split(',') if p.strip()],
                            'lineno': i+1,
                            'docstring': None,
                            'complexity': 1,  # Conservative estimate for fallback
                            'file_hash': self._file_hash(file_path),
                            'ast_fallback': True
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
                    if current_indent <= indent_level and not stripped_line.startswith('@'):
                        in_function = False
                        current_function = None
                        continue
                    
                    # Capture docstring
                    if stripped_line.startswith(('"""', "'''")):
                        if not functions[current_function]['docstring']:
                            # Remove quotes and leading leading/trailing whitespace
                            doc = stripped_line[3:-3].strip() if len(stripped_line) > 6 else ''
                            functions[current_function]['docstring'] = doc
            except Exception as e:
                logger.debug(f"Error parsing line {i+1} in {file_path}: {str(e)}")
                continue
        
        return functions

    def _cluster_functions(self, functions: Dict[str, dict], script_path: Path):
        """Group similar functions using structural comparison first"""
        for name, details in functions.items():
            # Initial cluster key without semantic hash
            # Create cluster key with structural and semantic features
            structural_key = (
                name,
                len(details['args']),
                details['complexity'] // 5,
                hashlib.md5(details['context'].encode()).hexdigest()[:8]
            )
            details['_structural_key'] = structural_key
            self.function_clusters[structural_key].append((script_path, details))

    def _semantic_hash(self, func_details: dict) -> str:
        """Generate hash based on function structure and LLM analysis"""
        if self.llm_client:
            prompt = f"Normalize this function signature for hashing:\nName: {func_details['name']}\nArgs: {func_details['args']}\nComplexity: {func_details['complexity']}"
            try:
                normalized = generate_response(prompt)
                return hashlib.md5(normalized.encode()).hexdigest()
            except Exception as e:
                logger.debug(f"LLM normalization failed: {e}")
                
        # Fallback to structural hash
        return hashlib.md5(
            f"{func_details['name']}-{len(func_details['args'])}-{func_details['complexity']}".encode()
        ).hexdigest()

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.And, ast.Or)):
                complexity += 1
        return complexity

    def _file_hash(self, file_path: Path) -> str:
        """Calculate content hash of a file"""
        return hashlib.md5(file_path.read_bytes()).hexdigest()

    def _analyze_clusters(self):
        """Analyze function clusters to identify consolidation candidates"""
        consolidation_candidates = []
        
        for cluster_key, implementations in self.function_clusters.items():
            if len(implementations) > 1:
                # Find the canonical version (best example)
                canonical = max(implementations, key=lambda x: self._implementation_quality(x[1]))
                consolidation_candidates.append((cluster_key, implementations, canonical))
                
        self._present_findings(consolidation_candidates)
        self._report_syntax_errors()

    def _implementation_quality(self, func_details: dict) -> float:
        """Score function quality based on various metrics"""
        score = 0
        if func_details['docstring']:
            score += 2
        score += min(func_details['complexity'], 10)  # Penalize over-complexity
        return score

    def _present_findings(self, candidates: list):
        """Interactive presentation of consolidation opportunities"""
        logger.info(f"\nFound {len(candidates)} consolidation opportunities:")
        
        for cluster_key, implementations, (canonical_path, canonical_details) in candidates:
            print(f"\nCluster: {cluster_key[0]} ({len(implementations)} implementations)")
            print(f"Suggested canonical: {canonical_path.name} (Line {canonical_details['lineno']})")
            print("Other implementations:")
            for path, details in implementations:
                if path != canonical_path:
                    print(f"  - {path.relative_to(self.root_dir)}: Line {details['lineno']}")
                    
            if input("\nShow diff? (y/N) ").lower() == 'y':
                self._show_implementation_diff(implementations)
                
            if self.llm_client and input("Get consolidation suggestion? (y/N) ").lower() == 'y':
                self._get_llm_consolidation_advice(implementations)

    def _show_implementation_diff(self, implementations: list):
        """Show diffs between implementations using system diff tool"""
        files = [str(i[0]) for i in implementations]
        try:
            subprocess.run(['diff', '-u'] + files)
        except Exception as e:
            logger.error(f"Diff failed: {e}")

    def _get_llm_consolidation_advice(self, implementations: list):
        """Use LLM to suggest consolidation strategy"""
        prompt = "Suggest how to consolidate these implementations into a canonical version:\n"
        for path, details in implementations:
            prompt += f"\n-- {path.name} --\n"
            prompt += f"Args: {details['args']}\n"
            prompt += f"Complexity: {details['complexity']}\n"
            if details['docstring']:
                prompt += f"Docs: {details['docstring']}\n"
                
        try:
            advice = self.llm_client.generate_content(prompt)
            print("\nLLM Consolidation Advice:")
            print(advice)
        except Exception as e:
            logger.error(f"LLM consultation failed: {e}")

    def _report_syntax_errors(self) -> None:
        """Report files with syntax errors at end of analysis"""
        if self.syntax_errors:
            logger.info(f"\nFound {len(self.syntax_errors)} files with syntax errors:")
            for error in self.syntax_errors:
                logger.info(f"  - {error}")
        else:
            logger.info("\nNo files with syntax errors found")

    def generate_report(self) -> str:
        """Generate consolidation roadmap report"""
        report = [
            "# Code Consolidation Report",
            f"## Analysis of {self.root_dir}",
            f"- Files analyzed: {len(self.script_analysis)}",
            f"- Function clusters found: {len(self.function_clusters)}",
            "\n## Top Consolidation Opportunities:"
        ]
        
        # Add cluster details
        for cluster_key, implementations in self.function_clusters.items():
            if len(implementations) > 1:
                report.append(
                    f"\n### {cluster_key[0]} ({len(implementations)} implementations)\n"
                    f"**Best candidate**: {max(implementations, key=lambda x: self._implementation_quality(x[1]))[0].name}\n"
                    "**Locations**:\n" + 
                    "\n".join(f"- {p.relative_to(self.root_dir)}: Line {d['lineno']}" for p, d in implementations)
                )
                
        return "\n".join(report)

    def _process_file(self, script_path: Path) -> tuple:
        """Process a single file and return results (for parallel execution)"""
        try:
            self._preprocess_script(script_path)
            functions = self._extract_functions(script_path)
            return functions, script_path
        except Exception as e:
            logger.error(f"Failed to process {script_path}: {e}")
            return {}, script_path

    def _preprocess_script(self, script_path: Path) -> None:
        """Autoformat script using ruff and black"""
        try:
            subprocess.run(['ruff', 'check', '--fix', str(script_path)], check=True)
            subprocess.run(['black', '--quiet', str(script_path)], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Formatting failed for {script_path}: {e}")

    def _analyze_function_context(self, node: ast.FunctionDef, source: str) -> str:
        """Analyze function context using NLP"""
        nlp = spacy.load('en_core_web_sm')
        context = []
        
        # Get full function text
        func_text = ast.get_source_segment(source, node) or ''
        doc = nlp(func_text)
        
        # Extract key entities and verbs
        entities = {ent.lemma_.lower() for ent in doc.ents if ent.label_ in {'ORG', 'PRODUCT', 'NORP'}}
        verbs = {token.lemma_ for token in doc if token.pos_ == 'VERB'}
        nouns = {chunk.root.lemma_ for chunk in doc.noun_chunks}
        
        # Combine and filter stopwords
        context_keywords = (entities | verbs | nouns) - STOP_WORDS
        return ' '.join(sorted(context_keywords))

    def _batch_process_semantic_hashes(self):
        """Batch process semantic hashes using LLM in parallel"""
        logger.info("Processing semantic hashes with LLM...")
        
        # Collect all unique function signatures needing hashes
        hash_queue = []
        for cluster_key, implementations in self.function_clusters.items():
            for _, details in implementations:
                if 'semantic_hash' not in details:
                    hash_queue.append(details)
        
        # Process in parallel batches
        batch_size = 10  # Adjust based on rate limits
        with ThreadPoolExecutor(max_workers=4) as executor:
            for i in range(0, len(hash_queue), batch_size):
                batch = hash_queue[i:i+batch_size]
                futures = [executor.submit(self._semantic_hash, func) for func in batch]
                for future in as_completed(futures):
                    func, hash_val = future.result()
                    func['semantic_hash'] = hash_val
        
        # Rebuild clusters with semantic hashes
        new_clusters = defaultdict(list)
        for (struct_key, details_list) in self.function_clusters.items():
            for details in details_list:
                cluster_key = (*struct_key, details['semantic_hash'])
                new_clusters[cluster_key].append(details)
        self.function_clusters = new_clusters

    def _save_checkpoint(self):
        """Save current state to checkpoint file"""
        checkpoint_data = {
            'processed_files': list(self.processed_files),
            'function_clusters': [
                (key, [str(p) for p in paths]) 
                for key, paths in self.function_clusters.items()
            ],
            'syntax_errors': self.syntax_errors
        }
        try:
            with self.lock:
                with open(self.checkpoint_file, 'w') as f:
                    json.dump(checkpoint_data, f)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def _load_checkpoint(self):
        """Load previous state from checkpoint file"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r') as f:
                    data = json.load(f)
                self.processed_files = set(data['processed_files'])
                self.function_clusters = defaultdict(list, {
                    tuple(key): [Path(p) for p in paths] 
                    for key, paths in data['function_clusters']
                })
                self.syntax_errors = data['syntax_errors']
                logger.info(f"Loaded checkpoint with {len(self.processed_files)} processed files")
            except Exception as e:
                logger.error(f"Failed to load checkpoint: {e}")

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Analyze and consolidate similar code functionality")
    parser.add_argument('--dir', default='.', help="Directory to analyze")
    parser.add_argument('--report', action='store_true', help="Generate HTML report")
    args = parser.parse_args()
    
    consolidator = CodeConsolidator(args.dir)
    consolidator.analyze_directory()
    
    if args.report:
        report_path = Path(args.dir) / "code_consolidation_report.md"
        with open(report_path, 'w') as f:
            f.write(consolidator.generate_report())
        logger.info(f"Report saved to {report_path}")

if __name__ == "__main__":
    main()
