import boto3
import os


def permission_node(state):
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not access_key or not secret_key:
        return {"status": "perm_fail", **state}

    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )  

    bucket = state.get("bucket")
    try:
        s3.get_bucket_policy(Bucket=bucket)
        return {"status": "perm_ok", **state}
    except:
        return {"status": "perm_fail", **state}
