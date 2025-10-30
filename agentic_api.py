from flask import Flask, request, jsonify
from agentic_chat import AgenticS3Chat
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Global chat instance
chat_agent = None

def get_chat_agent():
    global chat_agent
    if chat_agent is None:
        try:
            chat_agent = AgenticS3Chat()
        except Exception as e:
            raise Exception(f"Failed to initialize S3 chat agent: {e}")
    return chat_agent

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Missing 'question' field"}), 400
        
        question = data["question"].strip()
        if not question:
            return jsonify({"error": "Question cannot be empty"}), 400
        
        agent = get_chat_agent()
        answer = agent.chat(question)
        
        return jsonify({
            "answer": answer,
            "cached_buckets": len(agent.bucket_cache)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/status", methods=["GET"])
def status():
    try:
        agent = get_chat_agent()
        return jsonify({
            "status": "ready",
            "cached_buckets": len(agent.bucket_cache),
            "bucket_names": agent._get_bucket_list()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/clear-cache", methods=["POST"])
def clear_cache():
    try:
        agent = get_chat_agent()
        agent.bucket_cache.clear()
        return jsonify({"message": "Cache cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
