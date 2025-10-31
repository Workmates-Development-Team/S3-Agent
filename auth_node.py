import boto3
import os
from botocore.exceptions import ClientError


def auth_node(state):
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")

    if not access_key or not secret_key:
        return {"status": "auth_fail", **state}

    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        sts.get_caller_identity()  
        return {"status": "auth_ok", **state}
    except ClientError:
        return {"status": "auth_fail", **state}
