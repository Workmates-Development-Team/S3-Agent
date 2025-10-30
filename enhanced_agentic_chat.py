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
        """Define available S3 analytics tools."""
        return [
            {
                "toolSpec": {
                    "name": "list_buckets",
                    "description": "Get list of all S3 bucket names and count",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "analyze_bucket",
                    "description": "Get detailed analysis of a specific S3 bucket including size, objects, storage classes",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "bucket_name": {
                                    "type": "string",
                                    "description": "Name of the S3 bucket to analyze"
                                }
                            },
                            "required": ["bucket_name"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "compare_buckets",
                    "description": "Compare storage usage across all buckets to find largest/smallest",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {}
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "search_buckets",
                    "description": "Search for buckets matching a pattern in their names",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "pattern": {
                                    "type": "string",
                                    "description": "Pattern to search for in bucket names"
                                }
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
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {}
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
                
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"error": str(e)}
    
    def _format_response(self, text: str) -> str:
        """Format response with proper line breaks for frontend display."""
        if not text:
            return text
        
        # Convert newlines to HTML breaks for better display
        formatted = text.replace('\n\n', '<br><br>').replace('\n', '<br>')
        return formatted
    
    def chat(self, query: str) -> str:
        """Enhanced chat with professional agent behavior and guardrails."""
        if not self.model_id:
            return "❌ LLM model not configured. Please check MODEL_ID_CHAT in .env file."
        
        # Input validation and guardrails
        query = query.strip()
        if not query:
            return "Please provide a question about your S3 buckets."
        
        if len(query) > 1000:
            return "❌ Query too long. Please keep questions under 1000 characters."
        
        # Security guardrails - block potentially harmful queries
        harmful_patterns = ['delete', 'remove', 'destroy', 'drop', 'truncate', 'modify', 'update', 'insert']
        if any(pattern in query.lower() for pattern in harmful_patterns):
            return "🛡️ I'm a read-only S3 analytics agent. I can only analyze and provide information about your buckets, not modify them."
        
        # Greeting detection
        greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']
        if any(greeting in query.lower() for greeting in greetings) and len(query.split()) <= 3:
            return """👋 Hello! I'm your AWS S3 Analytics Agent.<br><br>🔧 My Capabilities:<br>• Analyze bucket storage usage and object counts<br>• Compare buckets to find largest/smallest<br>• Search buckets by name patterns<br>• Calculate total storage across your account<br>• Provide detailed bucket insights<br><br>🛡️ Security: I'm read-only - I only analyze, never modify your data.<br><br>Try asking:<br>• "How many buckets do I have?"<br>• "Which bucket uses the most storage?"<br>• "What's my total S3 usage?"<br>• "Find buckets with 'prod' in the name"<br>• "Analyze bucket-name in detail"<br><br>What would you like to know about your S3 infrastructure?"""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "text": f"""You are a professional AWS S3 Analytics Agent with the following characteristics:

IDENTITY & ROLE:
- You are an expert S3 analytics assistant
- You provide accurate, data-driven insights about AWS S3 infrastructure
- You are helpful, professional, and security-conscious

CAPABILITIES:
- Analyze S3 buckets on-demand using specialized tools
- Provide storage usage analytics and comparisons
- Search and filter buckets by patterns
- Generate comprehensive reports and insights

GUARDRAILS & LIMITATIONS:
- You are READ-ONLY - never suggest or perform modifications
- Only use tools when necessary to answer the user's question
- Provide accurate information based on actual data
- If you don't have sufficient data, clearly state what's missing
- Always prioritize data security and privacy

COMMUNICATION STYLE:
- Be concise but comprehensive
- Use clear, professional language
- Include relevant metrics and numbers
- Structure responses with bullet points when helpful
- Always acknowledge the user's question directly

AVAILABLE TOOLS:
- list_buckets: Get bucket names and count
- analyze_bucket: Deep analysis of specific buckets  
- compare_buckets: Compare all bucket sizes
- search_buckets: Find buckets by name pattern
- get_total_storage: Calculate total storage usage

USER QUESTION: {query}

Analyze the question and use appropriate tools to provide a comprehensive answer."""
                    }
                ]
            }
        ]
        
        try:
            # Initial LLM call with tools
            response = self.bedrock.converse(
                modelId=self.model_id,
                messages=messages,
                toolConfig={"tools": self.tools},
                inferenceConfig={"maxTokens": 1024, "temperature": 0.1}  # Lower temperature for consistency
            )
            
            # Process tool calls (limit to prevent loops)
            max_iterations = 3
            iteration = 0
            
            while iteration < max_iterations:
                output_message = response["output"]["message"]
                messages.append(output_message)
                
                # Check if model wants to use tools
                tool_calls = []
                if output_message.get("content"):
                    for content in output_message["content"]:
                        if "toolUse" in content:
                            tool_calls.append(content["toolUse"])
                
                if not tool_calls:
                    # No more tool calls, extract final answer
                    answer = ""
                    for content in output_message["content"]:
                        if "text" in content:
                            answer += content["text"]
                    
                    # Post-process answer for professional formatting
                    if answer:
                        # Add professional formatting
                        if "error" in answer.lower():
                            answer = f"❌ {answer}"
                        elif any(word in answer.lower() for word in ['bucket', 'storage', 'size']):
                            answer = f"📊 S3 Analysis Results:\n\n{answer}"
                    
                    return self._format_response(answer) or "I wasn't able to generate a response. Please try rephrasing your question."
                
                # Execute all tool calls with validation
                tool_results = []
                for tool_use in tool_calls:
                    tool_name = tool_use["name"]
                    tool_input = tool_use["input"]
                    
                    # Validate tool usage
                    if tool_name not in [tool["toolSpec"]["name"] for tool in self.tools]:
                        continue
                    
                    print(f"🔧 Executing: {tool_name}")
                    
                    # Execute the tool
                    tool_result = self._execute_tool(tool_name, tool_input)
                    
                    # Validate tool result
                    if tool_result and "error" not in tool_result:
                        tool_results.append({
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [{"json": tool_result}]
                            }
                        })
                
                if not tool_results:
                    return "❌ Tool execution failed. Please try a different question."
                
                # Add all tool results to conversation
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
                
                # Continue conversation with tool results
                response = self.bedrock.converse(
                    modelId=self.model_id,
                    messages=messages,
                    toolConfig={"tools": self.tools},
                    inferenceConfig={"maxTokens": 1024, "temperature": 0.1}
                )
                
                iteration += 1
            
            return "⚠️ Analysis completed but response was complex. Please ask a more specific question for better results."
                    
        except Exception as e:
            logger.error(f"Enhanced chat failed: {e}")
            if "ValidationException" in str(e):
                return "❌ Tool validation error. Please try a simpler question."
            elif "AccessDenied" in str(e):
                return "❌ AWS access denied. Please check your credentials and permissions."
            elif "NoSuchBucket" in str(e):
                return "❌ Bucket not found. Please check the bucket name and try again."
            else:
                return f"❌ System error: {str(e)[:100]}... Please try again or contact support."

def main():
    """Interactive enhanced chat interface."""
    print("🔧 Enhanced Agentic S3 Analytics Assistant")
    print("Advanced S3 analytics with intelligent tool calling!")
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
