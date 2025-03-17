from pathlib import Path
import shutil
import re
from datetime import datetime

class DataOrganizer:
    def __init__(self, base_dir: Path = Path("/Users/srvo/lc")):
        self.base_dir = base_dir
        self.data_dir = base_dir / "data"
        
        # Define core paths
        self.portfolio = {
            'current': self.data_dir / "portfolio/current",
            'archive': self.data_dir / "portfolio/archive/20241130"
        }
        self.crm = self.data_dir / "crm"
        self.raw = self.data_dir / "raw/csv"
        self.scripts = self.base_dir / "scripts"
    
    def _create_directory_structure(self):
        """Create the base directory structure"""
        dirs = [
            # Portfolio directories
            self.portfolio['current'] / "holdings",
            self.portfolio['current'] / "transactions",
            self.portfolio['current'] / "households",
            self.portfolio['archive'],
            # CRM directories
            self.crm / "contacts",
            self.crm / "calendar",
            self.crm / "emails",
            # Scripts and output
            self.scripts / "performance",
            self.scripts / "output",
            # Raw data
            self.raw
        ]
        
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _remove_duplicate_dirs(self):
        """Remove old portfolio structure"""
        old_dirs = [
            self.data_dir / "portfolio/holdings",
            self.data_dir / "portfolio/transactions",
            self.data_dir / "portfolio/households",
            self.base_dir / "performance"
        ]
        
        for dir_path in old_dirs:
            if dir_path.exists():
                try:
                    shutil.rmtree(dir_path)
                    print(f"Removed old directory: {dir_path.relative_to(self.base_dir)}")
                except Exception as e:
                    print(f"Error removing {dir_path}: {str(e)}")

    def _safe_copy(self, source: Path, target: Path, overwrite=False):
        """Safely copy a file and report the action"""
        if not source.exists() or (target.exists() and not overwrite):
            return False
            
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            print(f"Moved: {source.name} -> {target.relative_to(self.base_dir)}")
            return True
        except Exception as e:
            print(f"Error processing {source.name}: {str(e)}")
            return False

    def organize(self):
        """Organize all files and clean up duplicates"""
        print("Starting data organization...")
        
        # Create fresh directory structure
        self._create_directory_structure()
        
        # Move performance scripts first
        perf_dir = self.base_dir / "performance"
        if perf_dir.exists():
            # Move Python scripts
            for script in perf_dir.glob("**/*.py"):
                if not script.name == "organizer.py":
                    target = self.scripts / "performance" / script.name
                    self._safe_copy(script, target, overwrite=True)
            
            # Move output files
            for output in perf_dir.glob("**/output/*"):
                target = self.scripts / "output" / output.name
                self._safe_copy(output, target, overwrite=True)
            
            # Move data files to appropriate locations
            for data in perf_dir.glob("**/*.csv"):
                if "20241130" in str(data):
                    target = self.portfolio['archive'] / data.name
                else:
                    target = self.raw / data.name
                self._safe_copy(data, target, overwrite=True)

        # Organize remaining data files
        for file in self.data_dir.glob("**/*"):
            if not file.is_file():
                continue
            
            name = file.name.lower()
            target = None
            
            # Portfolio files
            if any(x in name for x in ['holdings', 'transactions', 'households']):
                if '20241130' in name:
                    target = self.portfolio['archive'] / file.name
                else:
                    category = next(x for x in ['holdings', 'transactions', 'households'] if x in name)
                    target = self.portfolio['current'] / category / file.name
            
            # CRM files
            elif any(x in name for x in ['contacts', 'calendar', 'emails']):
                category = next(x for x in ['contacts', 'calendar', 'emails'] if x in name)
                target = self.crm / category / file.name
            
            # Raw CSV files
            elif name.endswith('.csv'):
                target = self.raw / file.name
            
            if target:
                self._safe_copy(file, target, overwrite=True)

        # Clean up old directories and empty folders
        self._remove_duplicate_dirs()
        
        print("\nOrganization complete!")
        print("\nFinal structure:")
        self._print_structure()

    def _print_structure(self):
        """Print the final directory structure"""
        def print_tree(path, prefix=""):
            paths = sorted(path.glob("*"))
            for i, path in enumerate(paths):
                is_last = i == len(paths) - 1
                print(f"{prefix}{'└── ' if is_last else '├── '}{path.name}")
                if path.is_dir():
                    print_tree(path, prefix + ("    " if is_last else "│   "))
        
        print_tree(self.base_dir)

if __name__ == "__main__":
    organizer = DataOrganizer()
    organizer.organize()
