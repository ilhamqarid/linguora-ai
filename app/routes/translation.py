from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.services.grammar_service import to_french_for_correction
from app.services.translation_service import translate_from_french
from app.utils.validation import text_length_error

translation_bp = Blueprint("translation", __name__)


@translation_bp.route("/translate", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_DEFAULT"])
def translate():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    target = data.get("target_lang", "fr")
    source = data.get("source_lang", "auto")

    if not text.strip():
        return jsonify({"translated_text": ""})

    length_error = text_length_error(text)
    if length_error:
        return jsonify({"error": length_error}), 400

    fr_text, _errors, _lt_available = to_french_for_correction(text, source)
    translated, used_ai = translate_from_french(fr_text, target)
    return jsonify({"translated_text": translated, "used_ai": used_ai})
