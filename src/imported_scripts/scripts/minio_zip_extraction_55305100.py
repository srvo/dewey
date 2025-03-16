from typing import Any

import boto3
from botocore.client import Config


def create_s3_client(
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    region_name: str = "us-east-1",
) -> boto3.client:
    """Creates an S3 client with the specified configuration.

    Args:
        endpoint_url: The endpoint URL for the S3 service.
        access_key_id: The AWS access key ID.
        secret_access_key: The AWS secret access key.
        region_name: The AWS region name (default: us-east-1).

    Returns:
        A boto3 S3 client instance.

    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name=region_name,
    )


def _add_header(request: Any, **kwargs: Any) -> None:
    """Adds a custom header to the S3 request.

    Args:
        request: The S3 request object.
        **kwargs: Additional keyword arguments.

    """
    request.headers.add_header("x-minio-extract", "true")


def register_header_addition(s3_client: boto3.client) -> None:
    """Registers the header addition function to the S3 client's event system.

    Args:
        s3_client: The boto3 S3 client instance.

    """
    event_system = s3_client.meta.events
    event_system.register_first("before-sign.s3.*", _add_header)


def list_zip_contents(
    s3_client: boto3.client,
    bucket_name: str,
    prefix: str,
) -> dict[str, Any]:
    """Lists the contents of a zip file in S3.

    Args:
        s3_client: The boto3 S3 client instance.
        bucket_name: The name of the S3 bucket.
        prefix: The prefix of the zip file in S3.

    Returns:
        The response from the list_objects_v2 API call.

    """
    return s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)


def download_file_from_zip(
    s3_client: boto3.client,
    bucket_name: str,
    key: str,
    filename: str,
) -> None:
    """Downloads a file from a zip file in S3.

    Args:
        s3_client: The boto3 S3 client instance.
        bucket_name: The name of the S3 bucket.
        key: The key of the file within the zip file in S3.
        filename: The local filename to save the downloaded file to.

    """
    s3_client.download_file(Bucket=bucket_name, Key=key, Filename=filename)


if __name__ == "__main__":
    # Configuration
    ENDPOINT_URL = "http://localhost:9000"
    ACCESS_KEY_ID = "YOUR-ACCESSKEYID"
    SECRET_ACCESS_KEY = "YOUR-SECRETACCESSKEY"
    BUCKET_NAME = "your-bucket"
    ZIP_FILE_PREFIX = "path/to/file.zip/"
    FILE_KEY = "path/to/file.zip/data.csv"
    DOWNLOAD_FILENAME = "/tmp/data.csv"

    # Create S3 client
    s3 = create_s3_client(ENDPOINT_URL, ACCESS_KEY_ID, SECRET_ACCESS_KEY)

    # Register header addition
    register_header_addition(s3)

    # List zip contents
    response = list_zip_contents(s3, BUCKET_NAME, ZIP_FILE_PREFIX)

    # Download data.csv
    download_file_from_zip(s3, BUCKET_NAME, FILE_KEY, DOWNLOAD_FILENAME)
