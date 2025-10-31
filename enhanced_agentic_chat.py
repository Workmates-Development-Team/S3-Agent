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
        self.performance_stats = {"api_calls": 0, "cache_hits": 0}
        self.tools = self._define_tools()
        
    def _define_tools(self) -> List[Dict]:
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
                    "name": "batch_analyze_buckets",
                    "description": "Analyze multiple buckets efficiently for comparison queries",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "analysis_type": {
                                    "type": "string", 
                                    "enum": ["size", "objects", "storage_classes"],
                                    "description": "Type of analysis to perform"
                                }
                            },
                            "required": ["analysis_type"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "compare_object_counts",
                    "description": "Compare object counts across all buckets to find which has the most/least objects",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
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
            },
            {
                "toolSpec": {
                    "name": "find_smallest_bucket",
                    "description": "Find the bucket with the least storage usage",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            },
            {
                "toolSpec": {
                    "name": "find_largest_bucket", 
                    "description": "Find the bucket with the most storage usage",
                    "inputSchema": {"json": {"type": "object", "properties": {}}}
                }
            }
        ]
    
    def _execute_tool(self, tool_name: str, tool_input: Dict) -> Any:
        try:
            if tool_name == "list_buckets":
                response = self.s3.list_buckets()
                buckets = [b["Name"] for b in response.get("Buckets", [])]
                return {"buckets": buckets, "count": len(buckets)}
                
            elif tool_name == "batch_analyze_buckets":
                analysis_type = tool_input["analysis_type"]
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                print(f"📊 Batch analyzing {len(all_buckets)} buckets for {analysis_type}...")
                results = []
                
                for i, bucket in enumerate(all_buckets, 1):
                    print(f"   Processing {bucket} ({i}/{len(all_buckets)})")
                    
                    if bucket in self.bucket_cache:
                        self.performance_stats["cache_hits"] += 1
                        report = self.bucket_cache[bucket]
                    else:
                        self.performance_stats["api_calls"] += 1
                        result = app.invoke({"bucket": bucket})
                        report = result.get("report", {})
                        self.bucket_cache[bucket] = report
                    
                    if analysis_type == "size":
                        results.append({"bucket": bucket, "size": report.get("total_size", 0)})
                    elif analysis_type == "objects":
                        results.append({"bucket": bucket, "object_count": report.get("object_count", 0)})
                    elif analysis_type == "storage_classes":
                        results.append({"bucket": bucket, "storage_classes": report.get("storage_classes", {})})
                
                
                if analysis_type in ["size", "objects"]:
                    key = "size" if analysis_type == "size" else "object_count"
                    results.sort(key=lambda x: x[key], reverse=True)
                
                return {
                    "analysis_type": analysis_type,
                    "results": results,
                    "performance": self.performance_stats
                }
                
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
                
            elif tool_name == "compare_object_counts":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                bucket_objects = []
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    object_count = report.get("object_count", 0)
                    bucket_objects.append({"bucket": bucket, "object_count": object_count})
                
                bucket_objects.sort(key=lambda x: x["object_count"], reverse=True)
                return {"bucket_objects": bucket_objects}
                
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
                    policy = self.s3.get_bucket_policy(Bucket=bucket_name)
                    permissions["policy"] = "Has bucket policy"
                except:
                    permissions["policy"] = "No bucket policy"
                
                try:
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
            
            elif tool_name == "find_smallest_bucket":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                if not all_buckets:
                    return {"error": "No buckets found"}
                
                smallest_bucket = None
                smallest_size = float('inf')
                
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    size = report.get("total_size", 0)
                    
                    if size < smallest_size:
                        smallest_size = size
                        smallest_bucket = bucket
                
                if smallest_bucket:
                    report = self.bucket_cache[smallest_bucket]
                    return {
                        "bucket": smallest_bucket,
                        "size": smallest_size,
                        "size_readable": self._format_size(smallest_size),
                        "object_count": report.get("object_count", 0),
                        "storage_classes": report.get("storage_classes", {}),
                        "lifecycle_rules": report.get("lifecycle_rules", [])
                    }
                return {"error": "Could not determine smallest bucket"}
            
            elif tool_name == "find_largest_bucket":
                response = self.s3.list_buckets()
                all_buckets = [b["Name"] for b in response.get("Buckets", [])]
                
                if not all_buckets:
                    return {"error": "No buckets found"}
                
                largest_bucket = None
                largest_size = 0
                
                for bucket in all_buckets:
                    if bucket not in self.bucket_cache:
                        result = app.invoke({"bucket": bucket})
                        self.bucket_cache[bucket] = result.get("report", {})
                    
                    report = self.bucket_cache[bucket]
                    size = report.get("total_size", 0)
                    
                    if size > largest_size:
                        largest_size = size
                        largest_bucket = bucket
                
                if largest_bucket:
                    report = self.bucket_cache[largest_bucket]
                    return {
                        "bucket": largest_bucket,
                        "size": largest_size,
                        "size_readable": self._format_size(largest_size),
                        "object_count": report.get("object_count", 0),
                        "storage_classes": report.get("storage_classes", {}),
                        "lifecycle_rules": report.get("lifecycle_rules", [])
                    }
                return {"error": "Could not determine largest bucket"}
                
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": str(e)}
    
    def _format_size(self, bytes_size: int) -> str:
        if bytes_size == 0:
            return "0 bytes"
        
        units = ['bytes', 'KB', 'MB', 'GB', 'TB']
        size = float(bytes_size)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.1f} {units[unit_index]}"

    def _format_response(self, text: str) -> str:
        if not text:
            return text
        
        formatted = text.replace('**', '').replace('*', '')
        formatted = formatted.replace('__', '').replace('_', '')
        formatted = formatted.replace('###', '').replace('##', '').replace('#', '')
        formatted = formatted.replace('`', '').replace('~~', '')
        
        formatted = formatted.replace('\n\n', '<br><br>').replace('\n', '<br>')
        return formatted
    
    def chat(self, query: str) -> str:
        if not self.model_id:
            return "Model not configured."
        
        query = query.strip()
        if not query:
            return "Please ask a question about your S3 buckets."
        
        greetings = ['hello', 'hi', 'hey']
        if any(greeting in query.lower() for greeting in greetings) and len(query.split()) <= 3:
            return "Hello! Ask me about your S3 needs"

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""You are a helpful S3 assistant. Answer the user's question naturally and conversationally. Use tools to gather data but NEVER mention that you're using tools or analyzing data.

PERSONALITY:
- Be friendly and direct, like a knowledgeable colleague
- Never mention "tools", "analysis", "data gathering", or technical processes
- Just provide the answer as if you already knew it
- Use natural phrases like "I found", "Here's", "Looking at", "It appears"

TOOL USAGE STRATEGY:
- For questions about "which bucket has most/least objects" → use batch_analyze_buckets with analysis_type="objects"
- For questions about "which bucket is largest/smallest" → use batch_analyze_buckets with analysis_type="size"
- For storage class comparisons → use batch_analyze_buckets with analysis_type="storage_classes"
- For single bucket questions → use analyze_bucket
- For simple listing → use list_buckets

RESPONSE STYLE:
- Start directly with the answer
- Use human-readable sizes (1.3 KB, 2.1 MB, 45 GB)
- Be conversational but informative
- Make it sound effortless and natural

EXAMPLES:
  BAD: "The analyze_bucket tool has provided information..."
  BAD: "I should summarize this information..."
  GOOD: "Here's your smallest bucket! It's 'my-tiny-bucket' with just 1.3 KB..."
  GOOD: "Looking at your buckets, the largest one is 'prod-data' with 45 GB of storage..."

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
            
            max_iterations = 8
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
                
               
                print(f" Executing {len(tool_calls)} tools...")
                tool_results = []
                successful_tools = 0
                
                for tool_use in tool_calls:
                    try:
                        print(f"   → Running {tool_use['name']}...")
                        tool_result = self._execute_tool(tool_use["name"], tool_use["input"])
                        if tool_result and "error" not in tool_result:
                            tool_results.append({
                                "toolResult": {
                                    "toolUseId": tool_use["toolUseId"],
                                    "content": [{"json": tool_result}]
                                }
                            })
                            successful_tools += 1
                            print(f"   ✅ {tool_use['name']} completed")
                        else:
                            print(f"   ❌ {tool_use['name']} returned error")
                    except Exception as e:
                        print(f"   ❌ {tool_use['name']} failed: {e}")
                        continue
                
                if not tool_results:
                    if iteration < max_iterations - 1:
                        print("⚠️  All tools failed, retrying...")
                        iteration += 1
                        continue
                    return "Analysis failed. Please check your AWS credentials and permissions."
                
                print(f"✅ {successful_tools}/{len(tool_calls)} tools completed successfully")
                
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
            
            print(f"⚠️  Query exceeded {max_iterations} steps. This might be due to:")
            print("   • Complex analysis requiring many bucket operations")
            print("   • AWS API rate limiting")
            print("   • Large number of buckets to analyze")
            return "This analysis requires extensive bucket scanning. Try asking about specific buckets or use simpler queries like 'list my buckets' first."
                    
        except Exception as e:
            logger.error(f"Enhanced chat failed: {e}")
            return "Service error. Please try again."

def main():
    print(" Enhanced Agentic S3 Analytics Assistant")
    print("Type 'quit' to exit.\n")
    
    try:
        chat = EnhancedAgenticS3Chat()
    except Exception as e:
        print(f" Failed to initialize: {e}")
        return
    
    while True:
        try:
            query = input("\n You: ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
                
            if not query:
                continue
                
            print("\n Assistant:", chat.chat(query))
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f" Error: {e}")
    
    print("\n Thank you, Goodbye!")

if __name__ == "__main__":
    main()