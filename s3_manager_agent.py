# new_folder/s3_manager_agent.py
import boto3
import os
from graph import app  # Compiled StateGraph
import json

from dotenv import load_dotenv

load_dotenv()


class S3ManagerAgent:
    def __init__(self):
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", "us-east-1")

        if not access_key or not secret_key:
            raise ValueError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env"
            )

        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )  # Picks up creds from .env only
        self.bucket_reports = {}

    def analyze_all_buckets(self):
        response = self.s3.list_buckets()
        buckets = [b["Name"] for b in response.get("Buckets", [])]
        print(f"\n🪣 Found {len(buckets)} buckets: {buckets}")

        for bucket in buckets:
            print(f"\n🔍 Analyzing bucket: {bucket}")
            try:
                result = app.invoke({"bucket": bucket})
                self.bucket_reports[bucket] = result.get("report", {})
            except Exception as e:
                print(f"❌ Error analyzing {bucket}: {e}")

        print("\n✅ All buckets analyzed.\n")
        print(json.dumps(self.bucket_reports, indent=2))
        return self.bucket_reports
