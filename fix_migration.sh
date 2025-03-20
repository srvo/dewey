#!/bin/bash

# Find all Python migration scripts and save to a temporary file
find /Users/srvo/dewey/migration_scripts -name "*.py" > /tmp/migration_files.txt

# Count total files
total_files=$(wc -l < /tmp/migration_files.txt)
echo "Found $total_files migration scripts."

# Initialize counter for fixed files
fixed_files=0

# Process each file
while IFS= read -r file; do
    # Check if the file contains the problematic patterns
    if grep -q 'content = "from dewey.core.base_script import BaseScript' "$file" || grep -q '" + content' "$file"; then
        # Fix the string assignment by adding the missing newline and proper concatenation
        sed -i '' 's/content = "from dewey.core.base_script import BaseScript\\n\\n"\\n\\n"/content = "from dewey.core.base_script import BaseScript\\n\\n" + content/g' "$file"
        
        # Remove any stray " + content" lines
        sed -i '' '/^" + content$/d' "$file"
        
        echo "Fixed: $file"
        ((fixed_files++))
    fi
done < /tmp/migration_files.txt

# Clean up
rm /tmp/migration_files.txt

echo "Fixed $fixed_files out of $total_files files." 