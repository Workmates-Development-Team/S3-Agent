# Agentic S3 Chat Assistant

An intelligent AWS S3 analysis system that analyzes buckets on-demand based on user queries, rather than scanning all buckets upfront.

## Features

- **Fully Agentic**: Analyzes buckets only when needed based on user questions
- **Two Chat Modes**: Basic intent-based and enhanced tool-calling interfaces
- **Smart Caching**: Remembers analyzed buckets to avoid redundant API calls
- **On-Demand Analysis**: No upfront bucket scanning - discovers and analyzes as needed
- **Natural Language**: Ask questions in plain English about your S3 infrastructure

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure AWS credentials in `.env`:
```
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
MODEL_ID_CHAT=amazon.nova-micro-v1:0
```

## Usage

### Interactive CLI
```bash
# Basic agentic chat
python agentic_chat.py

# Enhanced chat with tool calling
python enhanced_agentic_chat.py
```

### API Server
```bash
# Start the server
python agentic_server.py

# Test endpoints
python test_agentic.py interactive
```

### API Endpoints

- `POST /chat` - Basic agentic chat
- `POST /enhanced-chat` - Enhanced chat with tool calling
- `GET /status` - System status and bucket list
- `POST /clear-cache` - Clear analysis cache

### Example Queries

The system intelligently determines what data it needs:

```
"How many buckets do I have?" 
→ Lists buckets without analyzing them

"Which bucket uses the most storage?"
→ Analyzes all buckets to compare sizes

"Tell me about my-specific-bucket"
→ Analyzes only that bucket

"Show me buckets with 'prod' in the name"
→ Searches bucket names, analyzes if needed
```

## Architecture

### Agentic Behavior
- **Intent Detection**: Determines what the user wants to know
- **Selective Analysis**: Only analyzes buckets relevant to the query
- **Smart Caching**: Remembers previous analyses
- **Tool Integration**: Enhanced mode uses LLM tool calling

### Components
- `agentic_chat.py` - Basic intent-based agentic interface
- `enhanced_agentic_chat.py` - Tool-calling enhanced interface
- `agentic_server.py` - Flask API server
- `graph.py` - LangGraph workflow for bucket analysis
- Individual nodes for auth, permissions, inspection, and reporting

## Benefits Over Traditional Approach

1. **No Upfront Scanning**: Doesn't list/analyze all buckets on startup
2. **Faster Responses**: Only processes relevant data
3. **Cost Efficient**: Fewer unnecessary API calls
4. **Scalable**: Works with accounts having hundreds of buckets
5. **User-Focused**: Answers specific questions efficiently

## Legacy Interface

The original non-agentic interface is still available in `main.py` for comparison.
