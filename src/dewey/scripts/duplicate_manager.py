"""
Advanced directory analysis tool with duplicate management, code quality checks, and structural validation.
Combines collision-resistant duplicate detection with code analysis and project convention enforcement.
"""

import argparse
import hashlib
import logging
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
import humanize

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DirectoryAnalyzer:
    """Comprehensive directory analysis with duplicate detection and code quality checks"""


    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).expanduser().resolve()
        self.file_hashes: Dict[str, List[Path]] = {}
        self.file_analysis: Dict[Path, Dict] = {}
        self.clusters: Dict[str, Dict] = {}
        self._validate_directory()

    def _validate_directory(self) -> None:
        """Ensure directory exists and is accessible."""
        if not self.root_dir.exists():
            raise FileNotFoundError(f"Directory not found: {self.root_dir}")
        if not os.access(self.root_dir, os.R_OK):
            raise PermissionError(f"Access denied to directory: {self.root_dir}")

    @staticmethod
    def calculate_file_hash(file_path: Path, block_size: int = 65536) -> str:
        """Calculate SHA-256 hash of a file with read buffering."""
        sha256 = hashlib.sha256()
        try:
            with file_path.open('rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    sha256.update(block)
            return sha256.hexdigest()
        except (IOError, PermissionError) as e:
            logger.warning(f"Could not read {file_path}: {str(e)}")
            return ""


    def find_duplicates(self) -> Dict[Tuple[str, int], List[Path]]:
        """Find duplicate files by size and hash."""
        duplicates: Dict[Tuple[str, int], List[Path]] = {}
        total_files = 0
        total_size = 0

        logger.info(f"Starting analysis of {self.root_dir}")
        
        # Walk directory with progress bar, excluding .venv
        all_files = [f for f in self.root_dir.rglob('*') if f.is_file() and '.venv' not in f.parts]
        logger.info(f"Found {len(all_files)} files to analyze")

        for file_path in all_files:
            if not file_path.is_file():
                continue

            try:
                file_size = file_path.stat().st_size
                file_hash = self.calculate_file_hash(file_path)
                
                if not file_hash:
                    continue

                key = (file_hash, file_size)
                duplicates.setdefault(key, []).append(file_path)
                total_files += 1
                total_size += file_size
                
                # Track hashes for full analysis
                if file_hash in self.file_hashes:
                    self.file_hashes[file_hash].append(file_path)
                else:
                    self.file_hashes[file_hash] = [file_path]

            except OSError as e:
                logger.error(f"Error processing {file_path}: {str(e)}")

        logger.info(f"Scanned {total_files:,} files ({humanize.naturalsize(total_size)})")
        return duplicates


    def _analyze_code_quality(self, file_path: Path) -> Dict:
        """Run code quality checks using flake8 and ruff."""
        results = {'flake8': [], 'ruff': []}
        try:
            # Run flake8
            flake8_result = subprocess.run(
                ['flake8', str(file_path)],
                capture_output=True,
                text=True
            )
            results['flake8'] = flake8_result.stdout.splitlines()
            
            # Run ruff
            ruff_result = subprocess.run(
                ['ruff', 'check', str(file_path)],
                capture_output=True,
                text=True
            )
            results['ruff'] = ruff_result.stdout.splitlines()
        except Exception as e:
            logger.error(f"Code quality analysis failed: {e}")
        return results

    def _analyze_directory_structure(self) -> Dict:
        """Check directory structure against project conventions."""
        expected_modules = [
            "src/dewey/core", "src/dewey/llm", "src/dewey/pipeline", "src/dewey/utils",
            "ui/screens", "ui/components", "config", "tests", "docs"
        ]
        
        dir_structure = {}
        deviations = []
        
        for root, dirs, files in os.walk(self.root_dir):
            rel_path = Path(root).relative_to(self.root_dir)
            if any(part.startswith('.') for part in rel_path.parts):
                continue
                
            dir_structure[str(rel_path)] = {
                'files': files,
                'subdirs': dirs,
                'expected': any(str(rel_path).startswith(m) for m in expected_modules)
            }
            
            if not dir_structure[str(rel_path)]['expected'] and rel_path != Path('.'):
                deviations.append(str(rel_path))
                
        return {'structure': dir_structure, 'deviations': deviations}

    def confirm_delete(self, files: List[Path], dry_run: bool = True) -> None:
        """Confirm and delete duplicates with code quality analysis."""
        if len(files) < 2:
            return

        # Sort by modification time - keep oldest file as original
        sorted_files = sorted(files, key=lambda f: f.stat().st_mtime)
        original = sorted_files[0]
        duplicates = sorted_files[1:]

        print(f"\nOriginal file ({datetime.fromtimestamp(original.stat().st_mtime):%Y-%m-%d}):")
        print(f"  {original}")
        print(f"  Code quality issues: {len(self._analyze_code_quality(original)['flake8'] + self._analyze_code_quality(original)['ruff'])}")

        print(f"\nPotential duplicates:")
        for dup in duplicates:
            print(f"  {dup} ({datetime.fromtimestamp(dup.stat().st_mtime):%Y-%m-%d})")
            print(f"  Code quality issues: {len(self._analyze_code_quality(dup)['flake8'] + self._analyze_code_quality(dup)['ruff'])}")

        if dry_run:
            print("\nDry run: Would delete duplicates above")
            return

        response = input("\nDelete duplicates? [y/N] ").strip().lower()
        if response != 'y':
            return

        for dup in duplicates:
            try:
                dup.unlink()
                print(f"Deleted: {dup}")
            except Exception as e:
                print(f"Error deleting {dup}: {str(e)}")


    def generate_report(self) -> str:
        """Generate consolidated analysis report."""
        dir_analysis = self._analyze_directory_structure()
        code_quality_issues = {
            path: self._analyze_code_quality(path)
            for path in self.file_analysis.keys()
        }

        report = [
            f"# Directory Analysis Report for {self.root_dir}",
            f"## Summary",
            f"- Total files analyzed: {len(self.file_analysis)}",
            f"- Duplicate clusters found: {len(self.clusters)}",
            f"- Files with code quality issues: {len([issues for issues in code_quality_issues.values() if issues['flake8'] or issues['ruff']])}",
            f"- Directory structure deviations: {len(dir_analysis['deviations'])}",
            "\n## Code Quality Issues",
            *[f"\n### {path.name}\n- Flake8: {len(issues['flake8'])} issues\n- Ruff: {len(issues['ruff'])} issues" 
              for path, issues in code_quality_issues.items()],
            "\n## Directory Structure Analysis",
            f"- Expected Modules: {', '.join(dir_analysis['expected_modules'])}",
            f"- Structural Deviations ({len(dir_analysis['deviations'])}):",
            *[f"  - {d}" for d in dir_analysis['deviations']],
            "\n## Duplicate Files Report",
            *[f"\n### Cluster {cluster_id}\n- Files: {len(cluster['files'])}\n- Size: {humanize.naturalsize(sum(f.stat().st_size for f in cluster['files']))}" 
              for cluster_id, cluster in self.clusters.items()]
        ]
        
        return '\n'.join(report)

def main():
    parser = argparse.ArgumentParser(
        description="Advanced directory analysis and duplicate management",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--dir', 
        default='/Users/srvo/input_data',
        help="Directory to analyze (default: /Users/srvo/input_data)"
    )
    parser.add_argument(
        '--delete', 
        action='store_true',
        help="Enable deletion mode (otherwise dry-run)"
    )
    parser.add_argument(
        '--report', 
        action='store_true',
        help="Generate comprehensive analysis report"
    )
    parser.add_argument(
        '--log', 
        default='directory_analysis.log',
        help="Log file path"
    )
    parser.add_argument(
        '-v', '--verbose', 
        action='store_true',
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    file_handler = logging.FileHandler(args.log)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    
    try:
        analyzer = DirectoryAnalyzer(args.dir)
        duplicates = analyzer.find_duplicates()
        
        if args.report:
            report = analyzer.generate_report()
            report_path = Path(args.dir) / "directory_analysis.md"
            with open(report_path, 'w') as f:
                f.write(report)
            logger.info(f"Analysis report saved to {report_path}")
            
        for key, files in duplicates.items():
            if len(files) > 1:
                analyzer.confirm_delete(files, dry_run=not args.delete)
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
