import boto3
from botocore.config import Config
import json

# Configure S3 client for Hetzner
s3_client = boto3.client(
    's3',
    endpoint_url='https://fort.fsn1.your-objectstorage.com',
    aws_access_key_id='8WV9AU74GN9WVS5TD88Z',
    aws_secret_access_key='S03DI67F75gJVECAUuHKDwRBErdEidPKWYf5YjWl',
    region_name='eu-central-1',
    config=Config(
        s3={'addressing_style': 'path'},
        signature_version='s3v4'
    )
)

try:
    # Upload a test file
    test_data = {"test": "Hello S3!", "timestamp": "now"}
    test_content = json.dumps(test_data)
    
    print("Uploading test file...")
    s3_client.put_object(
        Bucket='fort',
        Key='test.json',
        Body=test_content
    )
    print("Upload successful!")

    # Read back the file we just uploaded
    print("\nReading back the uploaded file:")
    response = s3_client.get_object(
        Bucket='fort',
        Key='test.json'
    )
    content = response['Body'].read().decode('utf-8')
    print("File contents:", content)

except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
