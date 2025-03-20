#!/bin/bash
# Script to clean up original test directories after verifying that reorganization is successful

# Set the base directory
TESTS_DIR="/Users/srvo/dewey/tests"

# Create a temporary backup directory just in case
BACKUP_DIR="/Users/srvo/dewey/tests/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Move original directories to backup
echo "Moving original directories to backup at $BACKUP_DIR..."

# Move core and subdirectories
if [ -d "$TESTS_DIR/core" ]; then
  echo "Backing up $TESTS_DIR/core"
  cp -r "$TESTS_DIR/core" "$BACKUP_DIR/"
fi

# Move dewey and subdirectories
if [ -d "$TESTS_DIR/dewey" ]; then
  echo "Backing up $TESTS_DIR/dewey"
  cp -r "$TESTS_DIR/dewey" "$BACKUP_DIR/"
fi

# Move ui and subdirectories
if [ -d "$TESTS_DIR/ui" ]; then
  echo "Backing up $TESTS_DIR/ui"
  cp -r "$TESTS_DIR/ui" "$BACKUP_DIR/"
fi

# Move config and subdirectories
if [ -d "$TESTS_DIR/config" ]; then
  echo "Backing up $TESTS_DIR/config"
  cp -r "$TESTS_DIR/config" "$BACKUP_DIR/"
fi

# Move docs and subdirectories
if [ -d "$TESTS_DIR/docs" ]; then
  echo "Backing up $TESTS_DIR/docs"
  cp -r "$TESTS_DIR/docs" "$BACKUP_DIR/"
fi

# Now remove original directories
echo ""
echo "Now removing original directories..."

# Ask for confirmation
read -p "Are you sure you want to delete the original directories? (y/N) " confirm
if [[ $confirm != "y" ]]; then
  echo "Aborted. Original directories remain in place."
  exit 0
fi

# Remove original directories
rm -rf "$TESTS_DIR/core" 2>/dev/null
rm -rf "$TESTS_DIR/dewey" 2>/dev/null
rm -rf "$TESTS_DIR/ui" 2>/dev/null
rm -rf "$TESTS_DIR/config" 2>/dev/null
rm -rf "$TESTS_DIR/docs" 2>/dev/null
rm -f "$TESTS_DIR/test_base_script.py" 2>/dev/null
rm -f "$TESTS_DIR/test_script_integration.py" 2>/dev/null

echo ""
echo "Cleanup complete!"
echo "Original directories were backed up to $BACKUP_DIR"
echo "Run pytest to verify that all tests still run correctly." 