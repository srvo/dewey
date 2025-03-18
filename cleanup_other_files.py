#!/usr/bin/env python3
"""
Script to delete:
1. Files ending with .metadata
2. Numbered CSVs from 0.csv to 999.csv
3. Files corresponding to 'other_' tables
"""

import os
import re
from pathlib import Path
from tqdm import tqdm

def get_files_to_delete(base_dir: str) -> list:
    """Find all files that should be deleted."""
    files_to_delete = []
    
    # Walk through all directories
    for root, _, files in os.walk(base_dir):
        for file in files:
            file_path = Path(root) / file
            
            # Skip .git directory
            if '.git' in file_path.parts:
                continue
                
            # Skip system files
            if file.startswith('.') and not file.endswith('.metadata'):
                continue
            
            # Check conditions for deletion:
            should_delete = False
            
            # 1. Files ending with .metadata
            if file.endswith('.metadata'):
                should_delete = True
            
            # 2. Numbered CSVs from 0.csv to 999.csv
            if re.match(r'^[0-9]{1,3}\.csv$', file):
                number = int(file.split('.')[0])
                if 0 <= number <= 999:
                    should_delete = True
            
            # 3. Files corresponding to 'other_' tables
            if (file.startswith('other_') or 
                (file.endswith('.metadata') and file[:-9].startswith('other_'))):
                should_delete = True
            
            if should_delete:
                files_to_delete.append(file_path)
    
    return files_to_delete

def group_files_by_type(files: list) -> dict:
    """Group files by their type for better reporting."""
    groups = {
        'metadata': [],
        'numbered_csvs': [],
        'other_tables': [],
        'other': []
    }
    
    for file in files:
        file_name = file.name
        if file_name.endswith('.metadata'):
            groups['metadata'].append(file)
        elif re.match(r'^[0-9]{1,3}\.csv$', file_name):
            groups['numbered_csvs'].append(file)
        elif file_name.startswith('other_'):
            groups['other_tables'].append(file)
        else:
            groups['other'].append(file)
    
    return groups

def main():
    input_dir = "/Users/srvo/input_data"
    
    # Get list of files to delete
    print("Scanning for files to delete...")
    files_to_delete = get_files_to_delete(input_dir)
    
    if not files_to_delete:
        print("No files found to delete")
        return
    
    # Group and show files that will be deleted
    groups = group_files_by_type(files_to_delete)
    
    print(f"\nFound {len(files_to_delete)} files to delete:")
    print("\nMetadata files:")
    for file in groups['metadata']:
        print(f"- {file}")
    
    print("\nNumbered CSVs (0-999):")
    for file in groups['numbered_csvs']:
        print(f"- {file}")
    
    print("\nOther table files:")
    for file in groups['other_tables']:
        print(f"- {file}")
    
    if groups['other']:
        print("\nOther files:")
        for file in groups['other']:
            print(f"- {file}")
    
    # Confirm deletion
    confirm = input("\nDo you want to proceed with deletion? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        return
    
    # Delete files with progress bar
    deleted_count = 0
    with tqdm(total=len(files_to_delete), desc="Deleting files") as pbar:
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                deleted_count += 1
                pbar.set_description(f"Deleted {file_path.name}")
            except Exception as e:
                print(f"\nError deleting {file_path}: {str(e)}")
            pbar.update(1)
    
    print("\nDone!")
    print(f"Successfully deleted {deleted_count} out of {len(files_to_delete)} files")

if __name__ == '__main__':
    main() 