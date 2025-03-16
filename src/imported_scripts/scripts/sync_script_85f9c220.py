#!/usr/bin/env python3
import paramiko


def sync_to_server() -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect("srvo.org", username="dokku")
        sftp = ssh.open_sftp()

        # Transfer files

        # Implement rsync-like functionality
        # Add progress monitoring

    finally:
        sftp.close()
        ssh.close()


if __name__ == "__main__":
    sync_to_server()
