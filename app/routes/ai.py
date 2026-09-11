from flask import Blueprint, current_app, jsonify, request

from app import limiter
from app.ai.llm_service import (
    is_ai_available,
    explain_correction,
    rewrite_with_context,
    correct_with_context,
)
from app.services.grammar_service import get_correction_details, apply_matches
from app.services.rewrite_service import rephrase_with_tone
from app.utils.validation import text_length_error

ai_bp = Blueprint("ai", __name__)


@ai_bp.route("/api/ai/correct", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_AI"])
def ai_correct():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")

    if not text.strip():
        return jsonify({"corrected_text": "", "used_ai": False})

    length_error = text_length_error(text)
    if length_error:
        return jsonify({"error": length_error}), 400

    if is_ai_available():
        ai_result = correct_with_context(text)
        if ai_result is not None:
            return jsonify({"corrected_text": ai_result, "used_ai": True})
        # L'IA est configurée mais l'appel a échoué (réseau, quota...) : repli.

    # Repli honnête : pipeline LanguageTool existant (1ère suggestion appliquée).
    base_text, errors, lt_available = get_correction_details(text, "auto")
    if not lt_available:
        return jsonify({"corrected_text": base_text, "used_ai": False, "languagetool_available": False})

    matches = [
        {
            "offset": e["start"],
            "length": e["length"],
            "replacements": [{"value": s} for s in e["suggestions"]],
        }
        for e in errors
    ]
    corrected = apply_matches(base_text, matches)
    return jsonify({"corrected_text": corrected, "used_ai": False, "languagetool_available": True})


@ai_bp.route("/api/ai/explain", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_AI"])
def explain():
    data = request.get_json(silent=True) or {}
    original = data.get("original", "")
    suggestion = data.get("suggestion", "")
    sentence = data.get("sentence", "")

    length_error = text_length_error(sentence)
    if length_error:
        return jsonify({"error": length_error}), 400

    if not is_ai_available():
        return jsonify({"explanation": None, "ai_available": False})

    explanation = explain_correction(original, suggestion, sentence)
    return jsonify({"explanation": explanation, "ai_available": True})


@ai_bp.route("/api/ai/rewrite", methods=["POST"])
@limiter.limit(lambda: current_app.config["RATELIMIT_AI"])
def ai_rewrite():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    tone = data.get("tone", "neutral")

    if not text.strip():
        return jsonify({"rewritten_text": "", "used_ai": False})

    length_error = text_length_error(text)
    if length_error:
        return jsonify({"error": length_error}), 400

    if not is_ai_available():
        # Pas de clé configurée : repli honnête et immédiat, pas d'appel réseau.
        fallback = rephrase_with_tone(text, tone)
        return jsonify({"rewritten_text": fallback, "used_ai": False})

    ai_result = rewrite_with_context(text, tone)
    if ai_result is None:
        # Clé configurée mais l'appel a échoué (réseau, quota...) : repli.
        fallback = rephrase_with_tone(text, tone)
        return jsonify({"rewritten_text": fallback, "used_ai": False})

    return jsonify({"rewritten_text": ai_result, "used_ai": True})
