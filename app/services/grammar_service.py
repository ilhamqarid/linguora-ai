import re

import requests
from flask import current_app

from app.data.dictionaries import DARIJA_FR, AMAZIGH_FR
from app.services.language_detect_service import detect_source_lang
from app.utils.text_utils import simple_dict_translate


def check_with_languagetool(text: str, lang_code: str = "fr"):
    """
    Interroge LanguageTool et renvoie la liste brute des 'matches'.

    Renvoie None si le serveur est injoignable (distinct d'une liste
    vide, qui signifie "LanguageTool a répondu, aucune erreur trouvée").
    Jamais d'exception qui remonte à la route.
    """
    url = current_app.config["LANGUAGETOOL_URL"]
    try:
        resp = requests.post(
            url,
            data={"text": text, "language": lang_code},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        current_app.logger.warning("LanguageTool indisponible: %s", e)
        return None

    return data.get("matches", [])


def apply_matches(text: str, matches: list) -> str:
    """Applique la 1ère suggestion de chaque match, du dernier au premier."""
    corrected = text
    for m in sorted(matches, key=lambda x: x["offset"], reverse=True):
        replacements = m.get("replacements", [])
        if not replacements:
            continue
        start = m["offset"]
        length = m["length"]
        replacement = replacements[0]["value"]
        corrected = corrected[:start] + replacement + corrected[start + length:]
    return corrected


def matches_to_errors(text: str, matches: list) -> list:
    """
    Transforme les 'matches' LanguageTool en une liste détaillée pour le
    frontend : position exacte, texte fautif, TOUTES les suggestions
    (jusqu'à 5) et l'explication. Contrairement à l'ancienne version,
    on ne choisit plus la suggestion à la place de l'utilisateur --
    c'est lui qui décide laquelle appliquer (ou aucune).
    """
    errors = []
    for m in matches:
        start = m["offset"]
        length = m["length"]
        replacements = m.get("replacements", [])[:5]
        errors.append({
            "start": start,
            "length": length,
            "original": text[start:start + length],
            "suggestions": [r["value"] for r in replacements],
            "message": m.get("message", ""),
        })
    return errors


def tidy_french(text: str) -> str:
    """Nettoyage FR léger : espaces, ponctuation, majuscule en début de phrase."""
    if not text:
        return text

    t = re.sub(r"\s+", " ", text.strip())
    t = re.sub(r"\s*([,.!?;:])\s*", r"\1 ", t)
    t = re.sub(r"\s+", " ", t)

    parts = re.split(r"([.!?…])", t)
    result = []
    for i in range(0, len(parts), 2):
        sentence = parts[i].strip()
        if not sentence:
            continue
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        sentence = sentence[0].upper() + sentence[1:]
        result.append(sentence + punct)

    return " ".join(result)


def _pivot_to_french(text: str, source: str) -> str:
    """
    Ramène un texte vers le français, quelle que soit sa langue/écriture
    d'origine. IA en priorité (comprend le darija/amazigh écrits en
    arabe, tifinagh OU latin), dictionnaire rule-based en repli (ne
    connaît que la transcription latine, ex : "bghit" -> "je veux").
    """
    if source not in ("darija", "amazigh"):
        return text

    from app.ai import llm_service  # import local : évite un cycle d'import

    if llm_service.is_ai_available():
        ai_fr = llm_service.translate_to_french(text, source)
        if ai_fr:
            return ai_fr

    dictionary = DARIJA_FR if source == "darija" else AMAZIGH_FR
    return simple_dict_translate(text, dictionary)


def to_french_for_correction(text: str, source: str = "auto") -> tuple:
    """
    Pivot vers le français pour correction :
    - Darija/Amazigh : IA en priorité (toute écriture), dictionnaire en
      repli (transcription latine uniquement)
    - Standard/French : on suppose déjà FR
    Puis nettoyage + correction LanguageTool (1ère suggestion appliquée
    automatiquement). Utilisé par /translate et /rephrase, qui ont
    besoin d'un texte français "final" sans interaction utilisateur.

    Renvoie (texte_corrige, erreurs, languagetool_disponible).
    """
    if source == "auto":
        source, _confidence = detect_source_lang(text)

    base_fr = _pivot_to_french(text, source)
    base_fr = tidy_french(base_fr)

    matches = check_with_languagetool(base_fr, "fr")

    if matches is None:
        return base_fr, [], False

    corrected = apply_matches(base_fr, matches)
    errors = matches_to_errors(base_fr, matches)

    return corrected, errors, True


def get_correction_details(text: str, source: str = "auto") -> tuple:
    """
    Comme to_french_for_correction, mais NE corrige PAS automatiquement :
    renvoie le texte pivoté/nettoyé tel quel + la liste détaillée des
    erreurs (avec position exacte et toutes les suggestions), pour que
    l'utilisateur choisisse lui-même quoi appliquer.

    Utilisé par la route /correct (interface interactive).

    Renvoie (texte_de_base, erreurs_detaillees, languagetool_disponible).
    """
    if source == "auto":
        source, _confidence = detect_source_lang(text)

    base_fr = _pivot_to_french(text, source)
    base_fr = tidy_french(base_fr)

    matches = check_with_languagetool(base_fr, "fr")

    if matches is None:
        return base_fr, [], False

    errors = matches_to_errors(base_fr, matches)
    return base_fr, errors, True
