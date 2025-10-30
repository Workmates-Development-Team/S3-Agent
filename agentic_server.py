from flask import Flask, request, jsonify, send_from_directory
from agentic_chat import AgenticS3Chat
from enhanced_agentic_chat import EnhancedAgenticS3Chat
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Global instances
basic_agent = None
enhanced_agent = None

def get_basic_agent():
    global basic_agent
    if basic_agent is None:
        basic_agent = AgenticS3Chat()
    return basic_agent

def get_enhanced_agent():
    global enhanced_agent
    if enhanced_agent is None:
        enhanced_agent = EnhancedAgenticS3Chat()
    return enhanced_agent

@app.route("/", methods=["GET"])
def home():
    """Serve the frontend HTML file."""
    return send_from_directory('.', 'frontend.html')

@app.route("/api", methods=["GET"])
def api_info():
    """API documentation."""
    return jsonify({
        "name": "Agentic S3 Chat API",
        "description": "Intelligent S3 bucket analysis without upfront scanning",
        "endpoints": {
            "/chat": "POST - Basic agentic chat",
            "/enhanced-chat": "POST - Enhanced chat with tool calling",
            "/status": "GET - System status",
            "/clear-cache": "POST - Clear analysis cache"
        },
        "features": [
            "On-demand bucket analysis",
            "Intelligent query routing",
            "Tool-based enhanced mode",
            "Caching for performance"
        ]
    })

@app.route("/chat", methods=["POST"])
def chat():
    """Basic agentic chat endpoint."""
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Missing 'question' field"}), 400
        
        question = data["question"].strip()
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        agent = get_basic_agent()
        answer = agent.chat(question)
        
        return jsonify({
            "answer": answer,
            "mode": "basic_agentic",
            "cached_buckets": len(agent.bucket_cache)
        })
        
    except Exception as e:
        logging.error(f"Basic chat error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/enhanced-chat", methods=["POST"])
def enhanced_chat():
    """Enhanced agentic chat with tool calling."""
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Missing 'question' field"}), 400
        
        question = data["question"].strip()
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        agent = get_enhanced_agent()
        answer = agent.chat(question)
        
        return jsonify({
            "answer": answer,
            "mode": "enhanced_agentic",
            "cached_buckets": len(agent.bucket_cache)
        })
        
    except Exception as e:
        logging.error(f"Enhanced chat error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    """Get system status."""
    try:
        basic = get_basic_agent()
        
        # Try to get enhanced agent, but don't fail if it doesn't work
        enhanced_info = {"cached_buckets": 0, "available_tools": 0}
        try:
            enhanced = get_enhanced_agent()
            enhanced_info = {
                "cached_buckets": len(enhanced.bucket_cache),
                "available_tools": len(enhanced.tools)
            }
        except Exception as e:
            logging.warning(f"Enhanced agent not available: {e}")
        
        return jsonify({
            "status": "ready",
            "basic_agent": {
                "cached_buckets": len(basic.bucket_cache)
            },
            "enhanced_agent": enhanced_info,
            "bucket_names": basic._get_bucket_list()
        })
    except Exception as e:
        logging.error(f"Status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    """Clear bucket analysis cache."""
    try:
        data = request.get_json() or {}
        agent_type = data.get("agent", "all")
        
        if agent_type in ["basic", "all"]:
            basic = get_basic_agent()
            basic.bucket_cache.clear()
            
        if agent_type in ["enhanced", "all"]:
            try:
                enhanced = get_enhanced_agent()
                enhanced.bucket_cache.clear()
            except Exception as e:
                logging.warning(f"Could not clear enhanced cache: {e}")
        
        return jsonify({"message": f"Cache cleared for {agent_type} agent(s)"})
    except Exception as e:
        logging.error(f"Clear cache error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("🚀 Starting Agentic S3 Chat Server...")
    print("📱 Frontend available at: http://localhost:5000")
    print("🔧 API endpoints at: http://localhost:5000/api")
    app.run(host="0.0.0.0", port=5000, debug=True)
