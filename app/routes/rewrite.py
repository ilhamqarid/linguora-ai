from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.services.grammar_service import to_french_for_correction
from app.services.rewrite_service import rephrase_with_tone
from app.utils.validation import text_length_error

rewrite_bp = Blueprint("rewrite", __name__)


@rewrite_bp.route("/rephrase", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_DEFAULT"])
def rephrase():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    source = data.get("source_lang", "auto")
    tone = data.get("tone", "neutral")

    if not text.strip():
        return jsonify({"rephrased_text": ""})

    length_error = text_length_error(text)
    if length_error:
        return jsonify({"error": length_error}), 400

    corrected_fr, _errors, _lt_available = to_french_for_correction(text, source)

    try:
        rephrased = rephrase_with_tone(corrected_fr, tone)
    except Exception as e:
        current_app.logger.error("Erreur reformulation: %s", e)
        return jsonify({"error": "Une erreur interne est survenue."}), 500

    return jsonify({"rephrased_text": rephrased})
