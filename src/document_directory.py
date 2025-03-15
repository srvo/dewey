import os
import logging
import hashlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from tqdm import tqdm  # For progress bars

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('doc_analysis.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class DirectoryAnalyzer:
    """Analyzes directory contents for code consolidation and documentation generation."""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir).resolve()
        self.file_hashes = {}  # MD5 hash to file paths
        self.file_analysis = {}  # Path to analysis data
        self.clusters = {}  # Grouped similar files
        logger.debug(f"Initialized analyzer for directory: {self.root_dir}")

    def _validate_directory(self) -> None:
        """Ensure the directory exists and is accessible."""
        if not self.root_dir.exists():
            raise FileNotFoundError(f"Directory not found: {self.root_dir}")
        if not os.access(self.root_dir, os.R_OK):
            raise PermissionError(f"Access denied to directory: {self.root_dir}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file contents with size check."""
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                return "empty_file"  # Special case for empty files
            
            with open(file_path, 'rb') as f:
                return f"{file_size}_{hashlib.sha256(f.read()).hexdigest()}"
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {str(e)}")
            raise

    def _analyze_file(self, file_path: Path) -> Dict:
        """Analyze individual file and return metadata."""
        analysis = {
            'path': str(file_path),
            'size': file_path.stat().st_size,
            'hash': self._calculate_file_hash(file_path),
            'imports': [],
            'functions': [],
            'classes': [],
            'dependencies': [],
            'issues': []
        }

        try:
            # First check if file is text before trying to read it
            with open(file_path, 'rb') as f:
                content_bytes = f.read(1024)
                try:
                    content_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    logger.warning(f"Skipping binary/non-UTF-8 file: {file_path}")
                    analysis['issues'].append("binary_or_non_utf8_file")
                    return analysis

            # Now read full content as text
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Basic code analysis
                analysis['imports'] = [line for line in content.split('\n') 
                                      if line.strip().startswith('import ')]
                analysis['functions'] = [line.split('def ')[1].split('(')[0] 
                                        for line in content.split('\n') 
                                        if line.strip().startswith('def ')]
                analysis['classes'] = [line.split('class ')[1].split('(')[0] 
                                      for line in content.split('\n') 
                                      if line.strip().startswith('class ')]
                
                logger.debug(f"Analyzed {file_path}: {len(analysis['functions'])} functions found")
                
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {str(e)}", exc_info=True)
            analysis['issues'].append(f"analysis_error: {str(e)}")
            # Skip files we couldn't analyze
            return analysis

        return analysis

    def _cluster_similar_files(self, delete_duplicates: bool = False) -> None:
        """Group files by similarity metrics and optionally delete duplicates."""
        logger.info("Clustering similar files...")
        # First cluster by exact duplicates
        for file_hash, paths in self.file_hashes.items():
            if len(paths) > 1:
                # Skip empty files cluster
                if file_hash == "empty_file":
                    logger.debug(f"Skipping {len(paths)} empty files")
                    continue
                
                self.clusters[f"duplicate_group_{file_hash}"] = {
                    'type': 'exact_duplicate',
                    'files': paths
                }
                logger.warning(f"Found {len(paths)} duplicate files with content hash {file_hash}")

                if delete_duplicates:
                    # Keep first file, delete others
                    keeper = Path(paths[0])
                    for duplicate in paths[1:]:
                        dup_path = Path(duplicate)
                        try:
                            dup_path.unlink()
                            logger.info(f"Deleted duplicate file: {duplicate}")
                        except Exception as e:
                            logger.error(f"Failed to delete {duplicate}: {e}")

        #:: Add semantic similarity clustering using embeddings

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
            logger.error(f"Code quality analysis failed for {file_path}: {e}")
            
        return results

    def _generate_report(self) -> str:
        """Generate consolidated analysis report."""
        code_quality_issues = {
            path: analysis.get('code_quality', {})
            for path, analysis in self.file_analysis.items()
            if analysis.get('code_quality')
        }
        
        report = [
            f"# Directory Analysis Report for {self.root_dir}",
            f"## Summary",
            f"- Total files analyzed: {len(self.file_analysis)}",
            f"- Duplicate clusters found: {len([c for c in self.clusters.values() if c['type'] == 'exact_duplicate'])}",
            f"- Files with code quality issues: {len(code_quality_issues)}",
            f"- Files with other issues: {len([a for a in self.file_analysis.values() if a['issues']])}",
            "\n## Code Quality Issues",
            "### Files with quality issues:"
        ]
        
        for path, issues in code_quality_issues.items():
            report.append(f"\n### {Path(path).name}")
            report.append("#### Flake8 Issues:")
            report.extend([f"- {msg}" for msg in issues['flake8']])
            report.append("#### Ruff Issues:")
            report.extend([f"- {msg}" for msg in issues['ruff']])
            
        report.append("\n## Detailed Analysis")
        
        for cluster_id, cluster in self.clusters.items():
            report.append(f"\n### Cluster {cluster_id}")
            report.append(f"Type: {cluster['type']}")
            report.append("Files:")
            report.extend([f"- {p}" for p in cluster['files']])
        
        return '\n'.join(report)

    def analyze_directory(self) -> Dict:
        """Main analysis workflow."""
        try:
            self._validate_directory()
            logger.info(f"Starting analysis of {self.root_dir}")
            
            # Walk directory with progress bar
            # Get all files except those in .venv directory
            all_files = [f for f in self.root_dir.rglob('*') if f.is_file() and '.venv' not in f.parts]
            logger.info(f"Found {len(all_files)} files to analyze")
            
            for file_path in tqdm(all_files, desc="Analyzing files"):
                try:
                    if file_path.suffix != '.py':
                        continue  # Only analyze Python files
                        
                    analysis = self._analyze_file(file_path)
                    analysis['code_quality'] = self._analyze_code_quality(file_path)
                    self.file_analysis[file_path] = analysis
                    
                    # Track hashes for duplicates
                    if analysis['hash'] in self.file_hashes:
                        self.file_hashes[analysis['hash']].append(str(file_path))
                    else:
                        self.file_hashes[analysis['hash']] = [str(file_path)]
                        
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {str(e)}", exc_info=True)
                    continue
                    
            self._cluster_similar_files(args.delete_duplicates)
            return self._generate_report()
            
        except Exception as e:
            logger.critical(f"Analysis failed: {str(e)}", exc_info=True)
            raise

def find_git_root(path: Path = Path.cwd()) -> Path:
    """Find the root directory of the git repository."""
    while path != path.parent:
        if (path / ".git").exists():
            return path
        path = path.parent
    return Path.cwd()  # Fallback to current directory if no git repo found

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze directory for code consolidation opportunities")
    parser.add_argument("directory", 
                      help="Directory to analyze (default: git root)",
                      nargs="?",
                      default=find_git_root())
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--delete-duplicates", action="store_true",
                      help="Automatically delete exact duplicate files")
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info(f"Analyzing directory: {args.directory}")
    analyzer = DirectoryAnalyzer(args.directory)
    report = analyzer.analyze_directory()
    
    output_path = Path(args.directory) / "directory_analysis.md"
    with open(output_path, 'w') as f:
        f.write(report)
    logger.info(f"Analysis report saved to {output_path}")
