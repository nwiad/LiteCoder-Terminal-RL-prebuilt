from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return jsonify({"status": "ok"})


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


@app.route("/echo", methods=["POST"])
def echo():
    body = request.get_json(force=True)
    return jsonify({"echo": body})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
