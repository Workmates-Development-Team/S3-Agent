# new_folder/s3_query_agent.py
import json
import os
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("s3-agent.query")


class S3QueryAgent:
    def __init__(self, bucket_reports):
        self.bucket_reports = bucket_reports
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("MODEL_ID_CHAT")  # Only chat model from .env

        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not access_key or not secret_key:
            raise ValueError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set in .env for Bedrock"
            )

        self.bedrock = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region,
        )  # Uses creds from .env only

    def ask(self, query):
        """Ask the model a question about the precomputed S3 reports using chat model (Converse API for Nova).

        Returns the model answer string. On failure, falls back to local heuristics.
        """
        context = json.dumps(self.bucket_reports, indent=2)

        user_message = f"""
You are an intelligent AWS S3 analytics assistant.
Below is the structured data from the user's AWS account S3 analysis (connected via env creds).
Use it to accurately answer the user's question about S3 buckets.

S3 Data:
{context}

User Question:
{query}

Provide a clear, factual response based only on the given data.
If data is missing, say "I don't have that information."
"""

        # Converse API format for Amazon Nova models
        messages = [{"role": "user", "content": [{"text": user_message}]}]

        if not self.model_id:
            logger.error("MODEL_ID_CHAT is not set in .env; cannot invoke model")
            return "Model is not configured (MODEL_ID_CHAT missing in .env)."

        try:
            logger.debug(
                "Invoking Bedrock chat model %s with prompt length %d",
                self.model_id,
                len(user_message),
            )
            # Use converse() for non-streaming response
            response = self.bedrock.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={
                    "maxTokens": 512,
                    "temperature": 0.5,
                    "topP": 0.9,
                },
            )

            # Extract the response text
            answer = ""
            for content_block in response["output"]["message"]["content"]:
                if content_block["text"]:
                    answer += content_block["text"]

            if not answer:
                answer = "No answer found."

            logger.info(
                "Agent answered question: %s",
                (answer[:200] + "...") if len(answer) > 200 else answer,
            )
            print("\n🤖 Agent Answer:\n", answer)
            return answer

        except (ClientError, BotoCoreError) as e:
            logger.exception("Bedrock model invocation failed: %s", e)
            # Fallback to local answer
            local = self._answer_locally(query)
            if local is not None:
                print("\n🤖 (local fallback) Agent Answer:\n", local)
                return local
            return (
                f"Model invocation failed: {str(e)}. Check Bedrock permissions, region, and MODEL_ID_CHAT in .env. "
                "See logs for details."
            )
        except Exception as e:
            logger.exception("Unexpected error: %s", e)
            local = self._answer_locally(query)
            if local is not None:
                print("\n🤖 (local fallback) Agent Answer:\n", local)
                return local
            return "An unexpected error occurred. See logs for details."

    def _answer_locally(self, query: str):
        """Heuristic fallback for basic S3 queries from bucket_reports."""
        q = (query or "").lower()

        # Number of buckets
        if any(
            kw in q for kw in ["how many buckets", "number of buckets", "buckets count"]
        ):
            num_buckets = len(self.bucket_reports)
            return f"There are {num_buckets} buckets in your account."

        # Largest bucket
        if any(
            kw in q
            for kw in [
                "most storage",
                "largest",
                "uses the most storage",
                "bucket with largest size",
            ]
        ):
            if not self.bucket_reports:
                return "I don't have bucket data."
            best = None
            best_size = -1
            for name, report in self.bucket_reports.items():
                try:
                    size = int(report.get("total_size") or report.get("size") or 0)
                except:
                    size = 0
                if size > best_size:
                    best_size = size
                    best = name
            if best is None:
                return "No size data available."
            return f"{best} uses the most storage: {best_size:,} bytes."

        # Total storage
        if any(kw in q for kw in ["total storage", "total size"]):
            total = 0
            for report in self.bucket_reports.values():
                try:
                    total += int(report.get("total_size") or report.get("size") or 0)
                except:
                    pass
            return f"Total storage: {total:,} bytes."

        # Object counts
        if any(kw in q for kw in ["object count", "objects", "how many objects"]):
            lines = []
            for name, report in self.bucket_reports.items():
                count = report.get("object_count") or report.get("count") or 0
                lines.append(f"{name}: {count}")
            return "\n".join(lines) if lines else None

        return None
