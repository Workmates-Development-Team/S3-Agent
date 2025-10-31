from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from enhanced_agentic_chat import EnhancedAgenticS3Chat
import logging

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.WARNING)

agent = None

def get_agent():
    global agent
    if agent is None:
        agent = EnhancedAgenticS3Chat()
    return agent

@app.route("/", methods=["GET"])
def home():
    return send_from_directory('.', 'frontend.html')

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        if not data or "question" not in data:
            return jsonify({"error": "Missing question"}), 400
        
        question = data["question"].strip()
        if not question:
            return jsonify({"error": "Empty question"}), 400
        
        agent = get_agent()
        answer = agent.chat(question)
        
        return jsonify({
            "answer": answer,
            "cached_buckets": len(agent.bucket_cache)
        })
        
    except Exception as e:
        return jsonify({"error": "Service error"}), 500

@app.route("/status", methods=["GET"])
def status():
    try:
        agent = get_agent()
        return jsonify({
            "status": "ready",
            "cached_buckets": len(agent.bucket_cache)
        })
    except Exception as e:
        return jsonify({"error": "Service unavailable"}), 500

if __name__ == "__main__":
    print("Sever is Listening on port :http://localhost:5000")
    app.run(host="0.0.0.0", port=5000)
