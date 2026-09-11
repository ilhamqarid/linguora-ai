from flask import Blueprint, jsonify, request

from app.services.language_detect_service import detect_source_lang
from app.utils.validation import text_length_error

detect_bp = Blueprint("detect", __name__)

LABELS_FR = {
    "darija": "Darija",
    "amazigh": "Amazigh (Tifinagh)",
    "french": "Français",
    "standard": "Français (supposé)",
}


@detect_bp.route("/detect-language", methods=["POST"])
def detect_language():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text.strip():
        return jsonify({"language": None, "language_label": None, "confidence": None})

    length_error = text_length_error(text)
    if length_error:
        return jsonify({"error": length_error}), 400

    label, confidence = detect_source_lang(text)
    return jsonify({
        "language": label,
        "language_label": LABELS_FR.get(label, label),
        "confidence": confidence,
    })
