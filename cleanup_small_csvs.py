#!/usr/bin/env python3
"""Script to delete CSV files with 5 or fewer rows of data."""

import os
import csv
from pathlib import Path
from tqdm import tqdm

def count_rows(file_path: Path) -> int:
    """Count the number of rows in a CSV file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Use csv.reader to handle proper CSV parsing
            reader = csv.reader(f)
            # Count rows (converting to list is faster than sum() for small files)
            return len(list(reader))
    except Exception as e:
        print(f"Warning: Error reading {file_path}: {str(e)}")
        return -1  # Return -1 to indicate error

def find_small_files(input_dir: Path) -> list:
    """Find all CSV files with 5 or fewer rows."""
    print("Scanning for small CSV files...")
    small_files = []
    
    # Walk through all directories
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.csv'):
                continue
                
            file_path = Path(root) / file
            
            # Skip system files and hidden files
            if file.startswith('.'):
                continue
                
            # Count rows
            row_count = count_rows(file_path)
            if 0 <= row_count <= 5:  # Include empty files but exclude error cases
                small_files.append((file_path, row_count))
    
    return small_files

def main():
    input_dir = Path("/Users/srvo/input_data")
    
    # Find small files
    small_files = find_small_files(input_dir)
    
    if not small_files:
        print("No small CSV files found")
        return
        
    # Display files to be deleted
    print(f"\nFound {len(small_files)} files with 5 or fewer rows:")
    for file_path, row_count in small_files:
        print(f"- {file_path} ({row_count} rows)")
        
    # Confirm deletion
    confirm = input("\nDo you want to proceed with deletion? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Operation cancelled")
        return
        
    # Delete files with progress bar
    deleted_count = 0
    with tqdm(total=len(small_files), desc="Deleting files") as pbar:
        for file_path, _ in small_files:
            try:
                os.remove(file_path)
                deleted_count += 1
                pbar.set_description(f"Deleted {file_path.name}")
            except Exception as e:
                print(f"\nError deleting {file_path}: {str(e)}")
            pbar.update(1)
            
    print("\nDone!")
    print(f"Successfully deleted {deleted_count} out of {len(small_files)} files")

if __name__ == '__main__':
    main() 