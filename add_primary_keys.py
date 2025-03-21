#!/usr/bin/env python3
"""
Script to add primary keys to all SQLAlchemy models in models.py
"""

import os
import re
import sys

def add_primary_keys(file_path):
    """Add primary key to all tables that don't have one in models.py"""
    with open(file_path, 'r') as f:
        content = f.read()

    # Find all model class definitions
    class_pattern = r'class (\w+)\(Base\):[\s\n]+__tablename__ = [\'"](\w+)[\'"]'
    classes = re.findall(class_pattern, content)
    
    # Keep track of modifications
    modified = False
    
    # Process each class
    for class_name, table_name in classes:
        # Check if the class already has a primary key defined
        pk_pattern = r'class {}\(Base\):[\s\n]+__tablename__ = [\'"]{}[\'"][\s\n]+.*?primary_key\s*=\s*True'.format(
            re.escape(class_name), re.escape(table_name))
        
        has_pk = re.search(pk_pattern, content, re.DOTALL)
        
        if not has_pk:
            print(f"Adding primary key to {class_name}")
            
            # Find the position after __tablename__ line
            tablename_pattern = r'class {}\(Base\):[\s\n]+__tablename__ = [\'"]{}[\'"][\s\n]+'.format(
                re.escape(class_name), re.escape(table_name))
            match = re.search(tablename_pattern, content)
            
            if match:
                insert_pos = match.end()
                # Add id column as primary key
                primary_key_line = f"    id = Column(sa.Integer, primary_key=True, autoincrement=True)\n"
                content = content[:insert_pos] + primary_key_line + content[insert_pos:]
                modified = True
    
    if modified:
        # Make a backup of the original file
        backup_path = file_path + '.bak'
        print(f"Creating backup at {backup_path}")
        with open(backup_path, 'w') as f:
            with open(file_path, 'r') as original:
                f.write(original.read())
        
        # Write the modified content
        with open(file_path, 'w') as f:
            f.write(content)
        
        print("Primary keys added successfully")
    else:
        print("No changes needed - all classes already have primary keys")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = os.path.join('src', 'dewey', 'core', 'db', 'models.py')
    
    add_primary_keys(file_path) 