import boto3
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv
from graph import app

load_dotenv()
logger = logging.getLogger("s3-agent.enhanced")

class EnhancedAgenticS3Chat:
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
        self.tools = self._define_tools()
        
    def _define_tools(self) -> List[Dict]:
        """Define comprehensive S3 analytics tools."""
        return [
            {
                "toolSpec": {
                    "name": "list_buckets",
                    "description": "Get list of all S3 bucket names and count",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "analyze_bucket",
                    "description": "Get detailed analysis of a specific S3 bucket",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "bucket_name": {"type": "string", "description": "Name of the S3 bucket to analyze"}
                            },
                            "required": ["bucket_name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "compare_buckets",
                    "description": "Compare storage usage across all buckets",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "search_buckets",
                    "description": "Search for buckets matching a pattern",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "pattern": {"type": "string", "description": "Pattern to search for in bucket names"}
                            },
                            "required": ["pattern"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "get_total_storage",
                    "description": "Calculate total storage usage across all buckets",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "get_bucket_permissions",
                    "description": "Check bucket policies and public access settings",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "bucket_name": {"type": "string", "description": "Name of the S3 bucket"}
                            },
                            "required": ["bucket_name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "analyze_storage_classes",
                    "description": "Breakdown of storage class usage across all buckets",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "get_bucket_versioning",
                    "description": "Check versioning status of buckets",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "bucket_name": {"type": "string", "description": "Name of the S3 bucket"}
                            },
                            "required": ["bucket_name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "analyze_lifecycle_rules",
                    "description": "Summary of lifecycle policies across buckets",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "get_bucket_encryption",
                    "description": "Check encryption settings for buckets",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "bucket_name": {"type": "string", "description": "Name of the S3 bucket"}
                            },
                            "required": ["bucket_name"]
                        }
                    }
                }
            }
        ]
    
    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        """Execute a tool and return the result."""
        try:
            if tool_name == "list_buckets":
                response = self.s3.list_buckets()
                buckets = [b["Name"] for b in response.get("Buckets", [])]
                return {"buckets": buckets, "count": len(buckets)}
                
            elif tool_name == "analyze_bucket":
                bucket_name = tool_input["bucket_name"]
                if bucket_name in self.bucket_cache:
                    return self.bucket_cache[bucket_name]
                
                result = app.invoke({"bucket": bucket_name})
                report = result.get("report", {})
                self.bucket_cache[bucket_name] = report
                return report
                
            elif tool_name == "compare_buckets":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                bucket_sizes = []
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    size = report.get("total_size", 0)
                    bucket_sizes.append({"bucket": bucket, "size": size})
                
                bucket_sizes.sort(key=lambda x: x["size"], reverse=True)
                return {"bucket_sizes": bucket_sizes}
                
            elif tool_name == "search_buckets":
                pattern = tool_input["pattern"].lower()
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                matching = [b for b in all_buckets if pattern in b.lower()]
                return {"matching_buckets": matching, "pattern": pattern}
                
            elif tool_name == "get_total_storage":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                total_size = 0
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    total_size += report.get("total_size", 0)
                
                return {"total_size": total_size, "bucket_count": len(all_buckets)}
                
            elif tool_name == "get_bucket_permissions":
                bucket_name = tool_input["bucket_name"]
                permissions = {}
                
                try:
                    # Check bucket policy
                    policy = self.s3.get_bucket_policy(Bucket=bucket_name)
                    permissions["policy"] = "Has bucket policy"
                except:
                    permissions["policy"] = "No bucket policy"
                
                try:
                    # Check public access block
                    pab = self.s3.get_public_access_block(Bucket=bucket_name)
                    permissions["public_access_block"] = pab["PublicAccessBlockConfiguration"]
                except:
                    permissions["public_access_block"] = "Not configured"
                
                return {"bucket": bucket_name, "permissions": permissions}
                
            elif tool_name == "analyze_storage_classes":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                storage_summary = {}
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    classes = report.get("storage_classes", {})
                    for storage_class, count in classes.items():
                        storage_summary[storage_class] = storage_summary.get(storage_class, 0) + count
                
                return {"storage_class_summary": storage_summary}
                
            elif tool_name == "get_bucket_versioning":
                bucket_name = tool_input["bucket_name"]
                try:
                    versioning = self.s3.get_bucket_versioning(Bucket=bucket_name)
                    status = versioning.get("Status", "Disabled")
                    mfa_delete = versioning.get("MfaDelete", "Disabled")
                    return {"bucket": bucket_name, "versioning": status, "mfa_delete": mfa_delete}
                except Exception as e:
                    return {"bucket": bucket_name, "versioning": "Error", "error": str(e)}
                
            elif tool_name == "analyze_lifecycle_rules":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                lifecycle_summary = []
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    rules = report.get("lifecycle_rules", [])
                    if rules:
                        lifecycle_summary.append({"bucket": bucket, "rules_count": len(rules)})
                
                return {"lifecycle_summary": lifecycle_summary}
                
            elif tool_name == "get_bucket_encryption":
                bucket_name = tool_input["bucket_name"]
                try:
                    encryption = self.s3.get_bucket_encryption(Bucket=bucket_name)
                    rules = encryption.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
                    if rules:
                        algorithm = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm", "Unknown")
                        return {"bucket": bucket_name, "encryption": "Enabled", "algorithm": algorithm}
                    else:
                        return {"bucket": bucket_name, "encryption": "Disabled"}
                except:
                    return {"bucket": bucket_name, "encryption": "Not configured"}
                
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": str(e)}
    
    def _format_response(self, text: str) -> str:
        """Remove markdown and format for display."""
        if not text:
            return text
        
        # Remove all markdown formatting
        formatted = text.replace('**', '').replace('*', '')
        formatted = formatted.replace('__', '').replace('_', '')
        formatted = formatted.replace('###', '').replace('##', '').replace('#', '')
        formatted = formatted.replace('`', '').replace('~~', '')
        
        # Convert newlines to HTML breaks
        formatted = formatted.replace('\n\n', '<br><br>').replace('\n', '<br>')
        return formatted
    
    def chat(self, query: str) -> str:
        """Enhanced chat with tool calling capabilities."""
        if not self.model_id:
            return "Model not configured."
        
        query = query.strip()
        if not query:
            return "Please ask a question about your S3 buckets."
        
        # Simple greeting
        greetings = ['hello', 'hi', 'hey']
        if any(greeting in query.lower() for greeting in greetings) and len(query.split()) <= 3:
            return "Hello! Ask me about your S3 buckets."

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""Analyze S3 data and answer the user's question directly. Use tools to gather information.

RULES:
- Answer directly, don't explain your role or capabilities
- Use plain text only, no markdown formatting
- Be concise and factual
- Use this format for analysis:

"Analysis of bucket [name]:
- Bucket Name: [name]
- Total Size: [size] bytes ([readable size])
- Object Count: [count]
- Storage Classes: [details]
- Lifecycle Rules: [rules or None]"

Question: {query}"""
                    }
                ]
            }
        ]
        
        try:
            response = self.bedrock.converse(
                modelId=self.model_id,
                messages=messages,
                toolConfig={"tools": self.tools},
                inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
            )
            
            max_iterations = 3
            iteration = 0
            
            while iteration < max_iterations:
                output_message = response["output"]["message"]
                messages.append(output_message)
                
                tool_calls = []
                if output_message.get("content"):
                    for content in output_message["content"]:
                        if "toolUse" in content:
                            tool_calls.append(content["toolUse"])
                
                if not tool_calls:
                    answer = ""
                    for content in output_message["content"]:
                        if "text" in content:
                            answer += content["text"]
                    
                    if answer and answer.strip():
                        return self._format_response(answer)
                    
                    # If no answer, prompt for response
                    if iteration == 0:
                        messages.append({
                            "role": "user",
                            "content": [{"text": "Please provide the analysis based on the data you gathered."}]
                        })
                        response = self.bedrock.converse(
                            modelId=self.model_id,
                            messages=messages,
                            inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
                        )
                        iteration += 1
                        continue
                    
                    return "Unable to generate response."
                
                # Execute tools
                print(f"🔧 Executing {len(tool_calls)} tools...")
                tool_results = []
                for tool_use in tool_calls:
                    try:
                        tool_result = self._execute_tool(tool_use["name"], tool_use["input"])
                        if tool_result and "error" not in tool_result:
                            tool_results.append({
                                "toolResult": {
                                    "toolUseId": tool_use["toolUseId"],
                                    "content": [{"json": tool_result}]
                                }
                            })
                    except Exception as e:
                        print(f"Tool {tool_use['name']} failed: {e}")
                        continue
                
                if not tool_results:
                    return "Tool execution failed."
                
                messages.append({"role": "user", "content": tool_results})
                
                try:
                    response = self.bedrock.converse(
                        modelId=self.model_id,
                        messages=messages,
                        toolConfig={"tools": self.tools},
                        inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
                    )
                except Exception as e:
                    print(f"Bedrock call failed: {e}")
                    return "Service error during analysis."
                
                iteration += 1
            
            return "Analysis is complex. Please try a more specific question."
                    
        except Exception as e:
            logger.error(f"Enhanced chat failed: {e}")
            return "Service error. Please try again."

def main():
    """Interactive enhanced chat interface."""
    print("🔧 Enhanced Agentic S3 Analytics Assistant")
    print("Type 'quit' to exit.\n")
    
    try:
        chat = EnhancedAgenticS3Chat()
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
