# new_folder/main.py
from s3_query_agent import S3QueryAgent
from s3_manager_agent import S3ManagerAgent
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

app = Flask(__name__)


@app.route("/chat", methods=["POST"])
def chat():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logger = logging.getLogger("s3-agent.main")

    manager = S3ManagerAgent()
    bucket_reports = manager.analyze_all_buckets()

    query_agent = S3QueryAgent(bucket_reports)

    # get user question from POST JSON body
    data = request.get_json()
    question = data.get("question", "")

    if not question:
        return jsonify({"error": "Missing 'question' field"}), 400

    try:
        answer = query_agent.ask(question)
        return jsonify({"answer": answer})
    except Exception as e:
        logger.exception("Error while handling user query")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
