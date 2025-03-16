#!/usr/bin/env python3

import json
import os

import boto3
import pytest
import requests
from botocore.client import Config


class TestMinIO:
    """Test suite for MinIO service."""

    @pytest.fixture(autouse=True)
    def setup(self, service_urls: dict[str, str]) -> None:
        """Set up test fixtures."""
        self.base_url = service_urls["minio"]
        self.access_key = os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = os.getenv("MINIO_SECRET_KEY")
        self.test_bucket = "test-bucket"

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=self.base_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def test_health_endpoint(self) -> None:
        """Test MinIO health endpoint."""
        response = requests.get(f"{self.base_url}/minio/health/live")
        assert response.status_code == 200

    def test_bucket_operations(self) -> None:
        """Test basic bucket operations."""
        # Create bucket
        self.s3_client.create_bucket(Bucket=self.test_bucket)

        # List buckets
        response = self.s3_client.list_buckets()
        buckets = [bucket["Name"] for bucket in response["Buckets"]]
        assert self.test_bucket in buckets

        # Delete bucket
        self.s3_client.delete_bucket(Bucket=self.test_bucket)

    def test_object_operations(self) -> None:
        """Test object operations."""
        # Create bucket
        self.s3_client.create_bucket(Bucket=self.test_bucket)

        try:
            # Upload object
            test_data = b"test content"
            self.s3_client.put_object(
                Bucket=self.test_bucket,
                Key="test.txt",
                Body=test_data,
            )

            # Get object
            response = self.s3_client.get_object(
                Bucket=self.test_bucket,
                Key="test.txt",
            )
            retrieved_data = response["Body"].read()
            assert retrieved_data == test_data

            # List objects
            response = self.s3_client.list_objects_v2(Bucket=self.test_bucket)
            assert len(response.get("Contents", [])) > 0

            # Delete object
            self.s3_client.delete_object(Bucket=self.test_bucket, Key="test.txt")
        finally:
            # Cleanup
            self.s3_client.delete_bucket(Bucket=self.test_bucket)

    def test_bucket_policy(self) -> None:
        """Test bucket policy operations."""
        # Create bucket
        self.s3_client.create_bucket(Bucket=self.test_bucket)

        try:
            # Set bucket policy
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": ["s3:GetObject"],
                        "Resource": [f"arn:aws:s3:::{self.test_bucket}/*"],
                    },
                ],
            }
            self.s3_client.put_bucket_policy(
                Bucket=self.test_bucket,
                Policy=json.dumps(policy),
            )

            # Get bucket policy
            response = self.s3_client.get_bucket_policy(Bucket=self.test_bucket)
            assert json.loads(response["Policy"]) == policy
        finally:
            # Cleanup
            self.s3_client.delete_bucket(Bucket=self.test_bucket)

    def test_multipart_upload(self) -> None:
        """Test multipart upload functionality."""
        # Create bucket
        self.s3_client.create_bucket(Bucket=self.test_bucket)

        try:
            # Initialize multipart upload
            response = self.s3_client.create_multipart_upload(
                Bucket=self.test_bucket,
                Key="large_file.txt",
            )
            upload_id = response["UploadId"]

            # Upload parts (simulated)
            parts = []
            for i in range(2):
                part_data = b"x" * 1024 * 1024  # 1MB part
                response = self.s3_client.upload_part(
                    Bucket=self.test_bucket,
                    Key="large_file.txt",
                    PartNumber=i + 1,
                    UploadId=upload_id,
                    Body=part_data,
                )
                parts.append({"PartNumber": i + 1, "ETag": response["ETag"]})

            # Complete multipart upload
            self.s3_client.complete_multipart_upload(
                Bucket=self.test_bucket,
                Key="large_file.txt",
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )

            # Verify upload
            response = self.s3_client.head_object(
                Bucket=self.test_bucket,
                Key="large_file.txt",
            )
            assert response["ContentLength"] == 2 * 1024 * 1024
        finally:
            # Cleanup
            self.s3_client.delete_object(Bucket=self.test_bucket, Key="large_file.txt")
            self.s3_client.delete_bucket(Bucket=self.test_bucket)

    def test_error_handling(self) -> None:
        """Test error handling."""
        # Test non-existent bucket
        with pytest.raises(self.s3_client.exceptions.NoSuchBucket):
            self.s3_client.list_objects_v2(Bucket="non-existent-bucket")

        # Test non-existent object
        with pytest.raises(self.s3_client.exceptions.NoSuchKey):
            self.s3_client.get_object(Bucket=self.test_bucket, Key="non-existent.txt")

    @pytest.mark.integration
    def test_farfalle_integration(self) -> None:
        """Test Farfalle integration with MinIO."""
        farfalle_url = os.getenv("FARFALLE_URL", "http://100.110.141.34:3000")
        response = requests.get(
            f"{farfalle_url}/api/storage/health",
            headers={"Authorization": f"Bearer {os.getenv('DOKKU_AUTH_TOKEN')}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
