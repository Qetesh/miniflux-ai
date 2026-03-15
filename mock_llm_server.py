"""Minimal OpenAI-compatible mock LLM server for development testing."""
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    user_msg = ""
    for m in data.get("messages", []):
        if m["role"] == "user":
            user_msg = m["content"][:100]
            break
    return jsonify({
        "id": "mock-001",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"[Mock AI Summary] This is a mock summary for development testing."
            },
            "finish_reason": "stop"
        }],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    })

@app.route('/v1/models', methods=['GET'])
def list_models():
    return jsonify({
        "data": [{"id": "mock-model", "object": "model"}]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=11434)
