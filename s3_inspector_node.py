import boto3
import os
from botocore.exceptions import ClientError


def s3_inspector_node(state: dict):
    """Inspect S3 bucket using creds from .env only."""
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not access_key or not secret_key:
        raise ValueError(
            "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env"
        )

    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    bucket = state.get("bucket")

    if not bucket:
        raise ValueError("No bucket name provided")

    paginator = s3.get_paginator("list_objects_v2")
    total_size = 0
    object_count = 0
    storage_classes = {}

    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            total_size += obj["Size"]
            object_count += 1
            sc = obj.get("StorageClass", "STANDARD")
            storage_classes[sc] = storage_classes.get(sc, 0) + 1

    try:
        resp = s3.get_bucket_lifecycle_configuration(Bucket=bucket)
        lifecycle_rules = resp.get("Rules", [])
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchLifecycleConfiguration":
            lifecycle_rules = []
        else:
            raise

    result = {
        "size": total_size,
        "count": object_count,
        "classes": storage_classes,
        "rules": lifecycle_rules,
        **state,
    }

    print(f" Inspected {bucket}: {object_count} objects, {total_size:,} bytes")
    print(f"Storage classes: {storage_classes}")
    print(f"Lifecycle rules: {len(lifecycle_rules)}")

    return result
