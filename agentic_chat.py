import boto3
import os
import json
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from graph import app

load_dotenv()
logger = logging.getLogger("s3-agent.agentic")

class AgenticS3Chat:
    def __init__(self):
        self.access_key = os.getenv("AWS_ACCESS_KEY_ID")
        self.secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("MODEL_ID_CHAT")
        
        if not self.access_key or not self.secret_key:
            raise ValueError("AWS credentials must be set in .env")
            
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        
        self.bedrock = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        
        self.bucket_cache = {}
        
    def _get_bucket_list(self) -> List[str]:
        """Get list of bucket names without analyzing them."""
        try:
            response = self.s3.list_buckets()
            return [b["Name"] for b in response.get("Buckets", [])]
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            return []
    
    def _analyze_bucket(self, bucket_name: str) -> Dict:
        """Analyze a specific bucket on-demand."""
        if bucket_name in self.bucket_cache:
            return self.bucket_cache[bucket_name]
            
        try:
            result = app.invoke({"bucket": bucket_name})
            report = result.get("report", {})
            self.bucket_cache[bucket_name] = report
            return report
        except Exception as e:
            logger.error(f"Failed to analyze bucket {bucket_name}: {e}")
            return {}
    
    def _determine_intent(self, query: str) -> Dict:
        """Determine what the user wants to know and which buckets to analyze."""
        q = query.lower()
        
        # Check if user mentions specific bucket names
        bucket_list = self._get_bucket_list()
        mentioned_buckets = [b for b in bucket_list if b.lower() in q]
        
        intent = {
            "action": "general",
            "buckets": mentioned_buckets,
            "needs_all_buckets": False
        }
        
        # Determine if we need all buckets or can work with specific ones
        if any(kw in q for kw in ["all buckets", "total", "compare", "largest", "smallest", "most", "least"]):
            intent["needs_all_buckets"] = True
            intent["action"] = "aggregate"
        elif mentioned_buckets:
            intent["action"] = "specific"
        elif any(kw in q for kw in ["list", "show", "what buckets"]):
            intent["action"] = "list"
        
        return intent
    
    def _get_llm_response(self, query: str, context: str) -> str:
        """Get response from LLM with context."""
        if not self.model_id:
            return "LLM model not configured."
            
        user_message = f"""
You are an AWS S3 assistant. Answer the user's question based on the provided S3 data.
Be concise and helpful. If you need more data, suggest what specific buckets to analyze.

S3 Data:
{context}

User Question: {query}
"""
        
        messages = [{"role": "user", "content": [{"text": user_message}]}]
        
        try:
            response = self.bedrock.converse(
                modelId=self.model_id,
                messages=messages,
                inferenceConfig={"maxTokens": 512, "temperature": 0.3}
            )
            
            answer = ""
            for content_block in response["output"]["message"]["content"]:
                if content_block.get("text"):
                    answer += content_block["text"]
            
            return answer or "No response generated."
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}")
            return f"LLM error: {str(e)}"
    
    def chat(self, query: str) -> str:
        """Main chat interface - processes query agentically."""
        intent = self._determine_intent(query)
        
        if intent["action"] == "list":
            bucket_list = self._get_bucket_list()
            return f"Available buckets ({len(bucket_list)}): {', '.join(bucket_list)}"
        
        # Collect relevant data based on intent
        context_data = {}
        
        if intent["needs_all_buckets"]:
            # Only analyze all buckets if truly needed
            bucket_list = self._get_bucket_list()
            print(f"🔍 Analyzing {len(bucket_list)} buckets for comprehensive query...")
            for bucket in bucket_list:
                context_data[bucket] = self._analyze_bucket(bucket)
        elif intent["buckets"]:
            # Analyze only mentioned buckets
            print(f"🔍 Analyzing specific buckets: {intent['buckets']}")
            for bucket in intent["buckets"]:
                context_data[bucket] = self._analyze_bucket(bucket)
        else:
            # Try to answer without bucket analysis first
            bucket_list = self._get_bucket_list()
            context_data = {"bucket_names": bucket_list, "note": "Bucket details available on request"}
        
        context = json.dumps(context_data, indent=2)
        return self._get_llm_response(query, context)

def main():
    """Interactive chat interface."""
    print("🤖 Agentic S3 Chat Assistant")
    print("Ask questions about your S3 buckets. Type 'quit' to exit.\n")
    
    try:
        chat = AgenticS3Chat()
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")
        return
    
    while True:
        try:
            query = input("\n💬 You: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
                
            if not query:
                continue
                
            print("\n🤖 Assistant:", chat.chat(query))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
