#!/usr/bin/env python3

from typing import Any

import boto3


def create_s3_client(endpoint_url: str) -> boto3.client:
    """Creates an S3 client with the given endpoint URL and credentials.

    Args:
        endpoint_url: The endpoint URL for the S3 service.

    Returns:
        A boto3 S3 client.

    """
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id="minio",
        aws_secret_access_key="minio123",
        region_name="us-east-1",
    )


def select_object_content(
    s3: boto3.client,
    bucket: str,
    key: str,
    expression: str,
) -> dict[str, Any]:
    """Selects content from an S3 object using the given SQL expression.

    Args:
        s3: The boto3 S3 client.
        bucket: The name of the S3 bucket.
        key: The key of the S3 object.
        expression: The SQL expression to use for selection.

    Returns:
        The response from the select_object_content API.

    """
    return s3.select_object_content(
        Bucket=bucket,
        Key=key,
        ExpressionType="SQL",
        Expression=expression,
        InputSerialization={
            "CSV": {
                "FileHeaderInfo": "USE",
            },
            "CompressionType": "GZIP",
        },
        OutputSerialization={"CSV": {}},
    )


def process_select_response(response: dict[str, Any]) -> None:
    """Processes the response from the select_object_content API.

    Args:
        response: The response from the select_object_content API.

    """
    for event in response["Payload"]:
        if "Records" in event:
            event["Records"]["Payload"].decode("utf-8")
        elif "Stats" in event:
            event["Stats"]["Details"]


def main() -> None:
    """Main function to execute the S3 select object content operation."""
    endpoint_url = "http://localhost:9000"
    bucket_name = "mycsvbucket"
    object_key = "sampledata/TotalPopulation.csv.gz"
    sql_expression = "select * from s3object s where s.Location like '%United States%'"

    s3_client = create_s3_client(endpoint_url)
    response = select_object_content(s3_client, bucket_name, object_key, sql_expression)
    process_select_response(response)


if __name__ == "__main__":
    main()
