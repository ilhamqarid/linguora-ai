from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.services.grammar_service import get_correction_details
from app.utils.validation import text_length_error

correction_bp = Blueprint("correction", __name__)


@correction_bp.route("/correct", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_DEFAULT"])
def correct():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    source = data.get("source_lang", "auto")

    if not text.strip():
        return jsonify({"base_text": "", "errors": [], "languagetool_available": True})

    length_error = text_length_error(text)
    if length_error:
        return jsonify({"error": length_error}), 400

    base_text, errors, lt_available = get_correction_details(text, source)
    return jsonify({
        "base_text": base_text,
        "errors": errors,
        "languagetool_available": lt_available,
    })
