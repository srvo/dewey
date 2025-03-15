"""
Advanced code consolidation tool using AST analysis and semantic clustering to identify
similar functionality across scripts and suggest canonical implementations.
"""

import ast
import logging
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
import subprocess
import humanize

from dewey.llm.api_clients.deepinfra import DeepInfraClient
from dewey.llm.api_clients.gemini import GeminiClient
from dewey.utils import read_csv_to_ibis  # Assuming this exists from previous utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class CodeConsolidator:
    """Identifies similar functionality across scripts using AST analysis and LLM-assisted clustering"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.function_clusters = defaultdict(list)
        self.script_analysis = {}
        self.llm_client = self._init_llm_clients()
        
    def _init_llm_clients(self):
        """Initialize available LLM clients with fallback handling"""
        try:
            return GeminiClient() or DeepInfraClient()
        except Exception as e:
            logger.warning(f"LLM clients unavailable: {e}")
            return None

    def analyze_directory(self):
        """Main analysis workflow"""
        scripts = self._find_script_files()
        logger.info(f"Found {len(scripts)} Python files to analyze")
        
        for script_path in scripts:
            functions = self._extract_functions(script_path)
            if functions:
                self._cluster_functions(functions, script_path)
                
        self._analyze_clusters()
        
    def _find_script_files(self) -> List[Path]:
        """Find all Python files in the directory, excluding tests and venv"""
        return [
            f for f in self.root_dir.rglob('*.py')
            if 'test' not in f.parts and '.venv' not in f.parts
        ]

    def _extract_functions(self, file_path: Path) -> Dict[str, dict]:
        """Parse AST to extract function definitions with context"""
        functions = {}
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read(), filename=str(file_path))
                
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_info = {
                        'name': node.name,
                        'args': [a.arg for a in node.args.args],
                        'lineno': node.lineno,
                        'docstring': ast.get_docstring(node),
                        'complexity': self._calculate_complexity(node),
                        'file_hash': self._file_hash(file_path)
                    }
                    functions[node.name] = func_info
                    
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            
        return functions

    def _cluster_functions(self, functions: Dict[str, dict], script_path: Path):
        """Group similar functions using multi-factor comparison"""
        for name, details in functions.items():
            # Create cluster key using combined metrics
            cluster_key = (
                name,
                len(details['args']),
                details['complexity'] // 5,  # Bucket complexity
                self._semantic_hash(details)
            )
            self.function_clusters[cluster_key].append((script_path, details))

    def _semantic_hash(self, func_details: dict) -> str:
        """Generate hash based on function structure and LLM analysis"""
        if self.llm_client:
            prompt = f"Normalize this function signature for hashing:\nName: {func_details['name']}\nArgs: {func_details['args']}\nComplexity: {func_details['complexity']}"
            try:
                normalized = self.llm_client.generate_content(prompt)
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
