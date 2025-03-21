#!/usr/bin/env python
"""
Schedule daily full sync between MotherDuck and local DuckDB.

This script sets up a scheduled job to run a full database sync at a specified time,
typically at night when the system is less likely to be in use.

On macOS, this uses launchd. For Linux, this would use cron.
"""

import os
import sys
import argparse
import platform
import subprocess
from pathlib import Path
from datetime import datetime

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

def setup_macos_launchd(hour=3, minute=0, label="com.dewey.duckdb_sync"):
    """Set up a launchd job on macOS.
    
    Args:
        hour: Hour to run the job (24-hour format)
        minute: Minute to run the job
        label: Label for the launchd job
        
    Returns:
        True if successful, False otherwise
    """
    # Get absolute paths
    script_path = Path(__file__).parent / "direct_db_sync.py"
    plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
    python_path = sys.executable
    
    # Create the plist file content
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path.absolute()}</string>
        <string>--mode</string>
        <string>full</string>
        <string>--verbose</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{project_root}/logs/db_sync.log</string>
    <key>StandardErrorPath</key>
    <string>{project_root}/logs/db_sync_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>MOTHERDUCK_TOKEN</key>
        <string>{os.environ.get('MOTHERDUCK_TOKEN', '')}</string>
    </dict>
</dict>
</plist>
"""
    
    try:
        # Create logs directory if it doesn't exist
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Write the plist file
        plist_path.parent.mkdir(exist_ok=True)
        with open(plist_path, 'w') as f:
            f.write(plist_content)
        
        # Load the job
        subprocess.run(['launchctl', 'unload', str(plist_path)], 
                      stderr=subprocess.PIPE,
                      check=False)  # Ignore errors if it's not already loaded
        subprocess.run(['launchctl', 'load', '-w', str(plist_path)], check=True)
        
        print(f"Scheduled daily DuckDB sync at {hour:02d}:{minute:02d}.")
        print(f"Plist file created at: {plist_path}")
        print(f"Logs will be written to: {log_dir}/db_sync.log")
        
        # Verify the job is loaded
        result = subprocess.run(['launchctl', 'list', label], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        if label in result.stdout:
            print("Job successfully loaded.")
            return True
        else:
            print("Warning: Job may not have been loaded correctly.")
            return False
    
    except Exception as e:
        print(f"Error setting up launchd job: {e}")
        return False

def setup_linux_cron(hour=3, minute=0):
    """Set up a cron job on Linux.
    
    Args:
        hour: Hour to run the job (24-hour format)
        minute: Minute to run the job
        
    Returns:
        True if successful, False otherwise
    """
    # Get absolute paths
    script_path = Path(__file__).parent / "direct_db_sync.py"
    python_path = sys.executable
    
    # Create the cron entry
    cron_cmd = f"MOTHERDUCK_TOKEN={os.environ.get('MOTHERDUCK_TOKEN', '')} "
    cron_cmd += f"{minute} {hour} * * * {python_path} {script_path.absolute()} --mode full --verbose "
    cron_cmd += f">> {project_root}/logs/db_sync.log 2>> {project_root}/logs/db_sync_error.log\n"
    
    try:
        # Create logs directory if it doesn't exist
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Get existing crontab
        result = subprocess.run(['crontab', '-l'], 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              text=True)
        
        if result.returncode != 0 and "no crontab" not in result.stderr:
            print(f"Error getting existing crontab: {result.stderr}")
            return False
            
        existing_crontab = result.stdout if result.returncode == 0 else ""
        
        # Remove any existing DuckDB sync entries
        lines = existing_crontab.splitlines()
        filtered_lines = [line for line in lines if "direct_db_sync.py" not in line]
        
        # Add the new entry
        new_crontab = "\n".join(filtered_lines)
        if new_crontab and not new_crontab.endswith("\n"):
            new_crontab += "\n"
        new_crontab += cron_cmd
        
        # Write to temporary file
        temp_file = Path("/tmp/dewey_crontab")
        with open(temp_file, 'w') as f:
            f.write(new_crontab)
        
        # Install the new crontab
        result = subprocess.run(['crontab', str(temp_file)], check=True)
        
        # Clean up
        temp_file.unlink()
        
        print(f"Scheduled daily DuckDB sync at {hour:02d}:{minute:02d}.")
        print(f"Logs will be written to: {log_dir}/db_sync.log")
        return True
    
    except Exception as e:
        print(f"Error setting up cron job: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Schedule daily DuckDB sync")
    parser.add_argument(
        "--hour", type=int, default=3,
        help="Hour to run the sync (24-hour format), default is 3 AM"
    )
    parser.add_argument(
        "--minute", type=int, default=0,
        help="Minute to run the sync, default is 0"
    )
    parser.add_argument(
        "--remove", action="store_true",
        help="Remove the scheduled job instead of adding it"
    )
    
    args = parser.parse_args()
    
    # Check for MotherDuck token
    if not os.environ.get('MOTHERDUCK_TOKEN') and not args.remove:
        print("Error: MOTHERDUCK_TOKEN environment variable is not set.")
        print("Please set the token before scheduling the sync job.")
        return 1
    
    # Handle job removal
    if args.remove:
        if platform.system() == "Darwin":  # macOS
            label = "com.dewey.duckdb_sync"
            plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
            
            try:
                subprocess.run(['launchctl', 'unload', str(plist_path)], check=True)
                plist_path.unlink(missing_ok=True)
                print("Removed scheduled DuckDB sync job.")
                return 0
            except Exception as e:
                print(f"Error removing launchd job: {e}")
                return 1
        else:  # Linux
            try:
                # Get existing crontab
                result = subprocess.run(['crontab', '-l'], 
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE,
                                      text=True)
                
                if result.returncode != 0 and "no crontab" not in result.stderr:
                    print(f"Error getting existing crontab: {result.stderr}")
                    return 1
                    
                existing_crontab = result.stdout if result.returncode == 0 else ""
                
                # Remove any DuckDB sync entries
                lines = existing_crontab.splitlines()
                filtered_lines = [line for line in lines if "direct_db_sync.py" not in line]
                new_crontab = "\n".join(filtered_lines)
                
                # Write to temporary file
                temp_file = Path("/tmp/dewey_crontab")
                with open(temp_file, 'w') as f:
                    f.write(new_crontab)
                
                # Install the new crontab
                subprocess.run(['crontab', str(temp_file)], check=True)
                
                # Clean up
                temp_file.unlink()
                
                print("Removed scheduled DuckDB sync job.")
                return 0
            except Exception as e:
                print(f"Error removing cron job: {e}")
                return 1
    
    # Set up the scheduled job
    if platform.system() == "Darwin":  # macOS
        success = setup_macos_launchd(args.hour, args.minute)
    else:  # Linux
        success = setup_linux_cron(args.hour, args.minute)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 