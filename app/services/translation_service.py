from deep_translator import GoogleTranslator

from app.data.dictionaries import FR_TO_DARIJA, FR_TO_AMAZIGH
from app.utils.text_utils import simple_dict_translate
from app.ai import llm_service


def translate_from_french(fr_text: str, target: str) -> tuple:
    """
    Traduit un texte français corrigé vers la langue cible.
    - 'fr'      : retourne le texte tel quel (pas de traduction nécessaire)
    - 'darija'  : IA (Groq) en priorité, mapping dictionnaire en repli
    - 'amazigh' : IA (Groq) en priorité, mapping dictionnaire en repli
    - autre     : IA (Groq) en priorité -- plus fiable que le scraping
      Google Translate, qui peut être bloqué ou instable selon les
      réseaux. Google Translate reste un repli si l'IA est indisponible.

    Renvoie (texte_traduit, utilisé_ia) pour que le frontend puisse
    afficher honnêtement quelle méthode a produit le résultat.
    """
    if target == "fr":
        return fr_text, False

    if target == "darija":
        if llm_service.is_ai_available():
            ai_result = llm_service.translate_with_ai(fr_text, target)
            if ai_result:
                return ai_result, True
        return simple_dict_translate(fr_text.lower(), FR_TO_DARIJA), False

    if target == "amazigh":
        if llm_service.is_ai_available():
            ai_result = llm_service.translate_with_ai(fr_text, target)
            if ai_result:
                return ai_result, True
        return simple_dict_translate(fr_text.lower(), FR_TO_AMAZIGH), False

    if llm_service.is_ai_available():
        ai_result = llm_service.translate_with_ai(fr_text, target)
        if ai_result:
            return ai_result, True

    try:
        return GoogleTranslator(source="fr", target=target).translate(fr_text), False
    except Exception:
        return "[Erreur de traduction] " + fr_text, False
