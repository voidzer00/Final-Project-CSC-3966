"""
server.py — RiskGuard remote analysis server.
Run this on your PC. Your Android app will POST SMS text to it
and receive a risk analysis result as JSON.

Start with:
    python server.py

By default listens on 0.0.0.0:5000 (all interfaces).
Port-forward TCP 5000 on your router to this machine's local IP.
"""

from flask import Flask, request, jsonify
from risk_analyzer import RiskAnalyzer

app = Flask(__name__)
analyzer = RiskAnalyzer()

#When you're testing this, make sure to run server.py while running the flask server. Read readme.md for more details.
API_SECRET = "1123581321"


@app.route("/analyze", methods=["POST"])
def analyze():
    # Check shared secret if enabled
    if API_SECRET:
        token = request.headers.get("X-API-Key", "")
        if token != API_SECRET:
            return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' field in JSON body"}), 400

    sms_text = str(data["text"]).strip()
    if not sms_text:
        return jsonify({"error": "Empty text"}), 400

    result = analyzer.analyze(sms_text)
    return jsonify(result)


@app.route("/ping", methods=["GET"])
def ping():
    """Health check — lets the app verify the server is reachable."""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("=" * 52)
    print("  RiskGuard Remote Analysis Server")
    print("  Listening on http://0.0.0.0:5000")
    print(f"  API secret: {'SET' if API_SECRET else 'DISABLED'}")
    print("=" * 52)
    # debug=False is important for internet-facing servers
    app.run(host="0.0.0.0", port=5000, debug=False)
