#!/usr/bin/env python3

import os
import logging
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError
from typing import List, Dict, Optional
import json
from collections import defaultdict
import mimetypes
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class S3Handler:
    def __init__(self):
        """Initialize S3 client with Storj S3-compatible API credentials."""
        load_dotenv()
        
        # Storj S3-compatible endpoint
        self.endpoint_url = 'https://gateway.storjshare.io'
        
        # Initialize the S3 client with Storj configuration
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            endpoint_url=self.endpoint_url,
            # Region is not used for Storj but boto3 requires it
            region_name='us-1'
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        
        if not self.bucket_name:
            raise ValueError("S3_BUCKET_NAME environment variable is required")
            
        # Configure specific Storj limits
        self.STORJ_LIMITS = {
            'max_buckets': 100,
            'min_part_size': 5 * 1024 * 1024,  # 5 MiB
            'max_parts': 10000,
            'max_list_objects': 1000,
        }

    def test_connection(self) -> bool:
        """Test S3 connection by listing buckets."""
        try:
            self.s3_client.list_buckets()
            logger.info("Successfully connected to S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to connect to S3: {str(e)}")
            return False

    def list_files(self, prefix: str = '', max_files: int = None) -> List[Dict]:
        """
        List files in the S3 bucket with optional prefix and limit.
        Returns: List of dicts with file info (key, size, last_modified)
        """
        try:
            paginator = self.s3_client.get_paginator('list_objects_v2')
            files = []
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
                        if max_files and len(files) >= max_files:
                            return files
            
            logger.info(f"Found {len(files)} files with prefix '{prefix}'")
            return files
        except ClientError as e:
            logger.error(f"Error listing files: {str(e)}")
            raise

    def analyze_files(self, prefix: str = '', max_files: int = None) -> Dict:
        """
        Analyze files in the bucket and return statistics.
        Note: Storj has a limit of 1000 objects per list operation.
        """
        if max_files and max_files > self.STORJ_LIMITS['max_list_objects']:
            logger.warning(f"Storj limits list operations to {self.STORJ_LIMITS['max_list_objects']} objects")
            max_files = self.STORJ_LIMITS['max_list_objects']
            
        files = self.list_files(prefix, max_files)
        
        # Initialize statistics
        stats = {
            'total_files': len(files),
            'total_size': 0,
            'extensions': defaultdict(int),
            'mime_types': defaultdict(int),
            'size_ranges': {
                '0-1MB': 0,
                '1MB-10MB': 0,
                '10MB-100MB': 0,
                '100MB+': 0
            },
            'sample_files': []
        }
        
        for file in files:
            # Update total size
            size_mb = file['size'] / (1024 * 1024)
            stats['total_size'] += file['size']
            
            # Update size ranges
            if size_mb <= 1:
                stats['size_ranges']['0-1MB'] += 1
            elif size_mb <= 10:
                stats['size_ranges']['1MB-10MB'] += 1
            elif size_mb <= 100:
                stats['size_ranges']['10MB-100MB'] += 1
            else:
                stats['size_ranges']['100MB+'] += 1
            
            # Update extensions and mime types
            ext = Path(file['key']).suffix.lower()
            mime_type, _ = mimetypes.guess_type(file['key'])
            
            stats['extensions'][ext or 'no_extension'] += 1
            stats['mime_types'][mime_type or 'unknown'] += 1
            
            # Add to sample files if it's one of the first few
            if len(stats['sample_files']) < 5:
                stats['sample_files'].append(file)
        
        # Convert total size to MB
        stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
        
        # Convert defaultdict to regular dict for JSON serialization
        stats['extensions'] = dict(stats['extensions'])
        stats['mime_types'] = dict(stats['mime_types'])
        
        return stats

    def read_file_metadata(self, file_key: str) -> Optional[Dict]:
        """
        Read file metadata from S3.
        Returns: Dict with metadata or None if file doesn't exist
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return {
                'content_type': response.get('ContentType'),
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'metadata': response.get('Metadata', {})
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"File not found: {file_key}")
                return None
            else:
                logger.error(f"Error reading file metadata: {str(e)}")
                raise

    def read_file(self, file_key: str) -> Optional[bytes]:
        """
        Read file content from S3.
        Returns: File content as bytes or None if file doesn't exist
        """
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(f"File not found: {file_key}")
                return None
            else:
                logger.error(f"Error reading file: {str(e)}")
                raise

def main():
    """Test S3 connection and analyze bucket contents."""
    try:
        print("\n=== Starting Storj Bucket Analysis ===")
        
        # Initialize handler
        print("\nInitializing S3 handler...")
        s3 = S3Handler()
        print(f"Using endpoint: {s3.endpoint_url}")
        print(f"Bucket name: {s3.bucket_name}")
        
        # Test connection
        print("\nTesting connection...")
        if not s3.test_connection():
            print("Failed to connect to Storj")
            return
        print("Connection successful!")
        
        # List and analyze files
        print("\nAnalyzing bucket contents...")
        try:
            stats = s3.analyze_files()
            
            # Print analysis results
            print("\n=== Bucket Analysis Results ===")
            print(f"\nTotal Files: {stats['total_files']}")
            print(f"Total Size: {stats['total_size_mb']:.2f} MB")
            
            print("\nFile Extensions:")
            for ext, count in sorted(stats['extensions'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {ext}: {count}")
            
            print("\nMIME Types:")
            for mime_type, count in sorted(stats['mime_types'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {mime_type}: {count}")
            
            print("\nSize Distribution:")
            for range_name, count in stats['size_ranges'].items():
                print(f"  {range_name}: {count}")
            
            if stats['sample_files']:
                print("\nSample Files:")
                for file in stats['sample_files']:
                    print(f"  - {file['key']} ({file['size'] / 1024 / 1024:.2f} MB)")
            
        except Exception as e:
            print(f"\nError during analysis: {str(e)}")
            import traceback
            print("\nFull traceback:")
            print(traceback.format_exc())
            
    except Exception as e:
        print(f"\nFatal error: {str(e)}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
    
    print("\n=== Analysis Complete ===")

if __name__ == "__main__":
    main() 