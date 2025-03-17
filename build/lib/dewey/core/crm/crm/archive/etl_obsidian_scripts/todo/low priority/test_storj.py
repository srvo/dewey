import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

def main():
    print("\n=== Starting Storj Test ===")
    
    # Load environment variables
    load_dotenv()
    
    # Print configuration (safely)
    print("\nConfiguration:")
    print(f"Access Key: {os.getenv('AWS_ACCESS_KEY_ID')[:4]}..." if os.getenv('AWS_ACCESS_KEY_ID') else "No access key found")
    print(f"Bucket: {os.getenv('S3_BUCKET_NAME')}")
    
    try:
        # Initialize S3 client
        print("\nInitializing S3 client...")
        s3 = boto3.client(
            's3',
            endpoint_url='https://gateway.storjshare.io',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name='us-1'
        )
        
        # List buckets
        print("\nListing buckets...")
        response = s3.list_buckets()
        print(f"Found buckets: {[b['Name'] for b in response['Buckets']]}")
        
        # List objects in specific bucket
        bucket_name = os.getenv('S3_BUCKET_NAME')
        print(f"\nListing objects in bucket '{bucket_name}'...")
        
        paginator = s3.get_paginator('list_objects_v2')
        total_size = 0
        total_files = 0
        
        for page in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page:
                for obj in page['Contents']:
                    total_files += 1
                    total_size += obj['Size']
                    if total_files <= 5:  # Show first 5 files as samples
                        print(f"  - {obj['Key']} ({obj['Size'] / 1024 / 1024:.2f} MB)")
        
        print(f"\nSummary:")
        print(f"Total files: {total_files}")
        print(f"Total size: {total_size / 1024 / 1024:.2f} MB")
        
    except ClientError as e:
        print(f"\nError accessing Storj: {str(e)}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    main() 