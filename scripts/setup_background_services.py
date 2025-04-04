#!/usr/bin/env python
"""
Setup Background Services.

This script helps configure background services for Dewey:
1. Database synchronization between MotherDuck and local DuckDB
2. Unified email processor service

It supports both cron jobs and systemd services depending on the platform.
"""

import argparse
import getpass
import logging
import os
import platform
import subprocess
import sys
from pathlib import Path

# Ensure the project root is in the path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def is_crontab_available():
    """Check if crontab is available on this system."""
    try:
        result = subprocess.run(
            ["which", "crontab"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except:
        return False


def is_systemd_available():
    """Check if systemd is available on this system."""
    try:
        result = subprocess.run(
            ["systemctl", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except:
        return False


def is_launchd_available():
    """Check if launchd is available (macOS)."""
    return platform.system() == "Darwin"


def setup_db_sync_cron(schedule="0 3 * * *", copy_first=True, incremental=True):
    """Set up database sync as a cron job."""
    try:
        # First make sure python-crontab is installed
        try:
            from crontab import CronTab
        except ImportError:
            logger.warning("python-crontab not installed, installing now...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "python-crontab"], check=True,
            )
            from crontab import CronTab

        # Create log directory if it doesn't exist
        log_dir = project_root / "logs"
        if not log_dir.exists():
            log_dir.mkdir(parents=True)
            logger.info(f"Created log directory: {log_dir}")

        # Build command
        sync_script = script_dir / "direct_db_sync.py"
        log_file = log_dir / "db_sync.log"

        command = f"cd {project_root} && "
        command += f"{sys.executable} {sync_script} "
        command += "--verbose "
        command += "--mode incremental " if incremental else "--mode full "
        command += "--copy-first " if copy_first else ""
        command += f">> {log_file} 2>&1"

        # Create new cron tab for current user
        cron = CronTab(user=True)

        # Check if the job already exists
        for job in cron:
            if "direct_db_sync.py" in str(job):
                logger.info("Removing existing db sync cron job")
                cron.remove(job)

        # Create new job
        job = cron.new(command=command)
        job.setall(schedule)
        job.set_comment("DeweyDB scheduled sync")

        # Write to crontab
        cron.write()

        logger.info(f"Cron job set up successfully with schedule: {schedule}")
        logger.info(f"Command: {command}")

        return True

    except Exception as e:
        logger.error(f"Error setting up cron job: {e}")
        return False


def setup_db_sync_launchd(hour=3, minute=0):
    """Set up database sync as a launchd job on macOS."""
    try:
        # Create plist file in ~/Library/LaunchAgents
        label = "com.dewey.db_sync"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

        # Create log directory
        log_dir = project_root / "logs"
        if not log_dir.exists():
            log_dir.mkdir(parents=True)

        # Get paths
        sync_script = script_dir / "direct_db_sync.py"
        log_file = log_dir / "db_sync.log"
        error_log = log_dir / "db_sync_error.log"

        # Create plist content
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{sync_script.absolute()}</string>
        <string>--verbose</string>
        <string>--mode</string>
        <string>incremental</string>
        <string>--copy-first</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>{hour}</integer>
        <key>Minute</key>
        <integer>{minute}</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{error_log}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>MOTHERDUCK_TOKEN</key>
        <string>{os.environ.get("MOTHERDUCK_TOKEN", "")}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
"""

        # Write plist file
        plist_path.parent.mkdir(exist_ok=True)
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # Unload if already loaded
        try:
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                stderr=subprocess.PIPE,
                check=False,
            )
        except:
            pass

        # Load the job
        subprocess.run(["launchctl", "load", "-w", str(plist_path)], check=True)

        logger.info(f"LaunchAgent set up successfully at {plist_path}")
        logger.info(f"Scheduled to run at {hour:02d}:{minute:02d} daily")

        return True

    except Exception as e:
        logger.error(f"Error setting up launchd job: {e}")
        return False


def setup_unified_processor_systemd():
    """Set up the unified processor as a systemd service."""
    try:
        # Check if running as root (required for system services)
        if os.geteuid() != 0:
            logger.error("Setting up systemd service requires root privileges.")
            logger.error("Please run this script with sudo.")
            return False

        # Get current user
        current_user = getpass.getuser()

        # Create service file from template
        service_template_path = script_dir / "dewey-unified-processor.service"
        if not service_template_path.exists():
            logger.error(f"Service template not found at {service_template_path}")
            return False

        # Read template
        with open(service_template_path) as f:
            service_content = f.read()

        # Replace placeholders
        service_content = service_content.replace("/path/to/dewey", str(project_root))
        service_content = service_content.replace("User=dewey", f"User={current_user}")

        # Get MotherDuck token if available
        motherduck_token = os.environ.get("MOTHERDUCK_TOKEN", "")
        service_content = service_content.replace("your_token_here", motherduck_token)

        # Write to systemd directory
        service_path = Path("/etc/systemd/system/dewey-unified-processor.service")
        with open(service_path, "w") as f:
            f.write(service_content)

        # Reload systemd
        subprocess.run(["systemctl", "daemon-reload"], check=True)

        # Enable the service
        subprocess.run(["systemctl", "enable", "dewey-unified-processor"], check=True)

        logger.info(f"Systemd service set up at {service_path}")
        logger.info(
            "To start the service, run: sudo systemctl start dewey-unified-processor",
        )

        return True

    except Exception as e:
        logger.error(f"Error setting up systemd service: {e}")
        return False


def setup_unified_processor_launchd():
    """Set up the unified processor as a LaunchAgent on macOS."""
    try:
        # Create plist file in ~/Library/LaunchAgents
        label = "com.dewey.unified_processor"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

        # Create log directory
        log_dir = project_root / "logs"
        if not log_dir.exists():
            log_dir.mkdir(parents=True)

        # Get paths
        processor_script = (
            project_root
            / "src"
            / "dewey"
            / "core"
            / "crm"
            / "gmail"
            / "run_unified_processor.py"
        )
        log_file = log_dir / "unified_processor.log"
        error_log = log_dir / "unified_processor_error.log"

        # Create plist content
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{processor_script.absolute()}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>{log_file}</string>
    <key>StandardErrorPath</key>
    <string>{error_log}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>MOTHERDUCK_TOKEN</key>
        <string>{os.environ.get("MOTHERDUCK_TOKEN", "")}</string>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONPATH</key>
        <string>{project_root}</string>
    </dict>
</dict>
</plist>
"""

        # Write plist file
        plist_path.parent.mkdir(exist_ok=True)
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # Unload if already loaded
        try:
            subprocess.run(
                ["launchctl", "unload", str(plist_path)],
                stderr=subprocess.PIPE,
                check=False,
            )
        except:
            pass

        # Load the job
        subprocess.run(["launchctl", "load", "-w", str(plist_path)], check=True)

        logger.info(f"LaunchAgent set up successfully at {plist_path}")
        logger.info(
            "The unified processor will start automatically at boot and restart if it fails",
        )

        return True

    except Exception as e:
        logger.error(f"Error setting up launchd job: {e}")
        return False


def parse_cron_time(cron_expression):
    """Parse cron expression to get hour and minute."""
    parts = cron_expression.split()
    if len(parts) != 5:
        return 3, 0  # Default to 3:00 AM

    minute = int(parts[0]) if parts[0].isdigit() else 0
    hour = int(parts[1]) if parts[1].isdigit() else 3

    return hour, minute


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Set up background services for Dewey")

    parser.add_argument(
        "--setup-db-sync",
        action="store_true",
        help="Set up database sync as a background service",
    )

    parser.add_argument(
        "--setup-processor",
        action="store_true",
        help="Set up unified email processor as a background service",
    )

    parser.add_argument(
        "--cron-schedule",
        default="0 3 * * *",
        help="Cron schedule for database sync (default: 3:00 AM daily)",
    )

    parser.add_argument(
        "--no-copy-first",
        action="store_true",
        help="Do not create a copy of the database before syncing",
    )

    parser.add_argument(
        "--full-sync",
        action="store_true",
        help="Use full sync instead of incremental for database sync",
    )

    args = parser.parse_args()

    # If no options specified, show help
    if not args.setup_db_sync and not args.setup_processor:
        parser.print_help()
        return 0

    # Make sure MOTHERDUCK_TOKEN is set
    if not os.environ.get("MOTHERDUCK_TOKEN"):
        logger.error("MOTHERDUCK_TOKEN environment variable not set")
        logger.error("Please set it before running this script:")
        logger.error("export MOTHERDUCK_TOKEN=your_token_here")
        return 1

    # Set up database sync
    if args.setup_db_sync:
        logger.info("Setting up database sync as a background service")

        # Choose the method based on platform
        if is_launchd_available():
            logger.info("Using launchd (macOS) for database sync")
            hour, minute = parse_cron_time(args.cron_schedule)
            if setup_db_sync_launchd(hour, minute):
                logger.info("Database sync service set up successfully")
            else:
                logger.error("Failed to set up database sync service")
                return 1

        elif is_crontab_available():
            logger.info("Using crontab for database sync")
            if setup_db_sync_cron(
                schedule=args.cron_schedule,
                copy_first=not args.no_copy_first,
                incremental=not args.full_sync,
            ):
                logger.info("Database sync cron job set up successfully")
            else:
                logger.error("Failed to set up database sync cron job")
                return 1

        else:
            logger.error("No supported scheduling system found (crontab or launchd)")
            return 1

    # Set up unified processor
    if args.setup_processor:
        logger.info("Setting up unified email processor as a background service")

        # Choose the method based on platform
        if is_launchd_available():
            logger.info("Using launchd (macOS) for unified processor")
            if setup_unified_processor_launchd():
                logger.info("Unified processor service set up successfully")
            else:
                logger.error("Failed to set up unified processor service")
                return 1

        elif is_systemd_available():
            logger.info("Using systemd for unified processor")
            if setup_unified_processor_systemd():
                logger.info("Unified processor service set up successfully")
            else:
                logger.error("Failed to set up unified processor service")
                return 1

        else:
            logger.error("No supported service manager found (systemd or launchd)")
            return 1

    logger.info("All requested services have been set up successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
