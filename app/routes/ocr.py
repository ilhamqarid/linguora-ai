from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.services.ocr_service import extract_text_from_image

ocr_bp = Blueprint("ocr", __name__)


@ocr_bp.route("/ocr", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_OCR"])
def ocr():
    image = request.files.get("image")

    if not image:
        return jsonify({"error": "No image provided"}), 400

    try:
        text = extract_text_from_image(image)
    except ValueError as e:
        # Ex: extension non autorisée -> message clair, pas de stack trace
        return jsonify({"error": str(e)}), 400

    return jsonify({"text": text})
