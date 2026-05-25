"""
KESHAV API — Flask wrapper for the full TANTRA pipeline

Endpoints:
    POST /analyze   — run full TANTRA chain, returns KESHAV output contract
    GET  /health    — liveness + readiness check

Run (development):
    python api.py

Run (production):
    gunicorn "api:app" --workers 4 --bind 0.0.0.0:5000

Environment variables:
    PORT            — listening port (default: 5000)
    HOST            — bind address  (default: 127.0.0.1)
    DEBUG           — enable Flask debug mode (default: false)
    MAX_CONTENT_MB  — max request body size in MB (default: 1)
"""

import logging
import os

from flask import Flask, jsonify, request

from tantra.pipeline import run_tantra_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("keshav.api")

app = Flask(__name__)

_max_mb = int(os.environ.get("MAX_CONTENT_MB", 1))
app.config["MAX_CONTENT_LENGTH"] = _max_mb * 1024 * 1024


# ── error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(413)
def request_too_large(_e):
    return jsonify({"status": "FAIL", "reason": "REQUEST_TOO_LARGE", "trace_id": ""}), 413


@app.errorhandler(405)
def method_not_allowed(_e):
    return jsonify({"status": "FAIL", "reason": "METHOD_NOT_ALLOWED", "trace_id": ""}), 405


@app.errorhandler(404)
def not_found(_e):
    return jsonify({"status": "FAIL", "reason": "NOT_FOUND", "trace_id": ""}), 404


@app.errorhandler(500)
def internal_error(_e):
    logger.exception("Unhandled internal error")
    return jsonify({"status": "FAIL", "reason": "INTERNAL_ERROR", "trace_id": ""}), 500


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    POST /analyze
    Content-Type: application/json
    Body: KESHAV input contract (trace_id + execution_id required)

    Returns 200 with TANTRA output on success.
    Returns 400 with FAIL response on invalid input.
    Returns 415 if Content-Type is not application/json.
    """
    if not request.is_json:
        return jsonify({"status": "FAIL", "reason": "UNSUPPORTED_MEDIA_TYPE", "trace_id": ""}), 415

    input_data = request.get_json(silent=True)
    if input_data is None:
        return jsonify({"status": "FAIL", "reason": "INVALID_JSON", "trace_id": ""}), 400

    trace_id = input_data.get("trace_id", "") if isinstance(input_data, dict) else ""
    logger.info("POST /analyze trace_id=%s", trace_id)

    result = run_tantra_pipeline(input_data)

    if result["status"] == "FAIL":
        logger.warning("pipeline FAIL trace_id=%s error=%s", trace_id, result.get("error"))
        return jsonify(result["keshav_output"]), 400

    logger.info("pipeline OK trace_id=%s", trace_id)
    return jsonify(result["keshav_output"]), 200


@app.route("/health", methods=["GET"])
def health():
    """GET /health — liveness + readiness check."""
    return jsonify({"status": "OK", "service": "KESHAV"}), 200


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
