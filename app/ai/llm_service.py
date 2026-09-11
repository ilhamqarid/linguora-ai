import re
import requests
from flask import current_app

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


def is_ai_available() -> bool:
    """L'IA n'est considérée disponible que si une clé API est configurée."""
    return bool(current_app.config.get("GROQ_API_KEY"))


def _call_groq(messages: list, max_tokens: int = 220, temperature: float = 0.3):
    """
    Appelle l'API Groq (chat completions, format compatible OpenAI).

    Renvoie le texte de la réponse, ou None si l'IA n'est pas configurée
    ou si l'appel échoue pour n'importe quelle raison (réseau, clé
    invalide, quota dépassé, timeout...). Ne lève JAMAIS d'exception --
    le fallback est toujours géré par l'appelant, jamais par un crash.
    """
    api_key = current_app.config.get("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.post(
            GROQ_CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": current_app.config.get("GROQ_MODEL", "openai/gpt-oss-120b"),
                "messages": messages,
                # gpt-oss est un modèle "reasoning" : sans ce réglage, il peut
                # consommer tout le budget de tokens à "réfléchir" en interne
                # et renvoyer un content vide (finish_reason="length").
                "reasoning_effort": "low",
                # Marge de sécurité au-dessus du besoin réel, pour laisser de
                # la place à un peu de raisonnement sans tronquer la réponse.
                "max_tokens": max_tokens + 150,
                "temperature": temperature,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            current_app.logger.warning(
                "Groq AI a renvoyé une réponse vide (finish_reason=%s)",
                data["choices"][0].get("finish_reason"),
            )
            return None
        return content
    except Exception as e:
        current_app.logger.warning("Groq AI indisponible: %s", e)
        return None


def explain_correction(original: str, suggestion: str, sentence: str):
    """
    Demande à l'IA une explication courte et pédagogique d'une correction
    grammaticale, dans le contexte de la phrase complète.

    Renvoie None si l'IA est indisponible -- le frontend doit alors
    garder l'explication technique de LanguageTool plutôt que d'afficher
    un vide ou une erreur.
    """
    prompt = (
        "Tu es un professeur de français bienveillant. En UNE phrase "
        "courte et simple, explique pourquoi on remplace le mot fautif "
        "par la correction proposée, dans le contexte de la phrase "
        "donnée. N'invente pas d'autre correction, explique uniquement "
        "celle donnée. Réponds uniquement par l'explication, sans "
        "introduction ni formule de politesse.\n\n"
        f"Phrase : {sentence}\n"
        f"Mot fautif : {original}\n"
        f"Correction proposée : {suggestion}"
    )
    return _call_groq([{"role": "user", "content": prompt}], max_tokens=120)


def rewrite_with_context(text: str, tone: str):
    """
    Reformulation contextuelle via IA -- contrairement à
    rewrite_service.rephrase_with_tone (remplacements de mots-clés),
    l'IA comprend le sens de la phrase et peut la reformuler
    correctement (conjugaisons, accords...).

    Renvoie None si l'IA est indisponible -- l'appelant doit alors
    proposer un repli vers la reformulation par règles.
    """
    tone_descriptions = {
        "professional": "un ton professionnel et vouvoyé",
        "friendly": "un ton amical et décontracté",
        "neutral": "un ton neutre, en gardant le style d'origine",
    }
    tone_desc = tone_descriptions.get(tone, tone_descriptions["neutral"])

    prompt = (
        f"Reformule le texte suivant avec {tone_desc}, en français. "
        "Garde exactement le même sens, ne rajoute aucune information "
        "qui n'est pas dans le texte d'origine. Réponds uniquement avec "
        "le texte reformulé, sans guillemets ni commentaire.\n\n"
        f"Texte : {text}"
    )
    return _call_groq(
        [{"role": "user", "content": prompt}], max_tokens=300, temperature=0.4
    )


def correct_with_context(text: str):
    """
    Correction orthographique et grammaticale contextuelle via IA --
    contrairement au pipeline LanguageTool (qui propose des candidats
    par distance d'édition sans toujours deviner l'intention), l'IA
    comprend le sens de la phrase. Utile typiquement pour une faute de
    frappe qui donne un autre mot valide ("VUX" -> LanguageTool hésite
    entre plusieurs mots, l'IA comprend qu'on veut dire "veux").

    Préserve la langue d'origine (français, darija, amazigh) : ne
    traduit jamais, corrige uniquement.

    Renvoie None si l'IA est indisponible -- l'appelant doit alors
    proposer un repli vers la correction par règles (LanguageTool).
    """
    prompt = (
        "Tu es un correcteur orthographique et grammatical. Corrige les "
        "fautes d'orthographe, de grammaire et de conjugaison du texte "
        "suivant, en gardant EXACTEMENT le même sens et la MÊME langue "
        "(si le texte est en darija ou en amazigh, corrige-le dans sa "
        "langue d'origine, ne le traduis surtout pas en français). "
        "Réponds uniquement avec le texte corrigé, sans explication, "
        "sans guillemets, sans commentaire.\n\n"
        f"Texte : {text}"
    )
    return _call_groq([{"role": "user", "content": prompt}], max_tokens=300, temperature=0.1)


# Noms lisibles pour quelques codes de langue courants, utilisés dans le
# prompt de traduction (une IA traduit mieux avec un nom clair qu'avec
# un code ISO brut).
_LANGUAGE_NAMES = {
    "en": "anglais",
    "es": "espagnol",
    "de": "allemand",
    "it": "italien",
    "pt": "portugais",
    "ar": "arabe",
    "nl": "néerlandais",
    "ru": "russe",
    "zh-CN": "chinois",
    "ja": "japonais",
}


# Table de translittération de l'alphabet latin berbère standard
# (orthographe IRCAM/Kabyle courante) vers le Tifinagh (Unicode Neo-Tifinagh).
# Triée pour tester les digraphes/trigraphes AVANT les lettres simples,
# afin de ne pas les casser (ex : "gh" doit matcher avant "g" seul).
_LATIN_BERBER_TO_TIFINAGH = [
    ("kw", "ⴽⵯ"), ("gw", "ⴳⵯ"),
    ("gh", "ⵖ"), ("kh", "ⵅ"), ("ch", "ⵛ"), ("sh", "ⵛ"), ("dj", "ⴵ"),
    ("ɣ", "ⵖ"), ("ɛ", "ⵄ"), ("ḥ", "ⵃ"), ("ḍ", "ⴹ"), ("ṣ", "ⵚ"), ("ṭ", "ⵟ"),
    ("ẓ", "ⵥ"), ("ε", "ⵄ"),
    ("a", "ⴰ"), ("b", "ⴱ"), ("c", "ⵛ"), ("d", "ⴷ"), ("e", "ⴻ"), ("f", "ⴼ"),
    ("g", "ⴳ"), ("h", "ⵀ"), ("i", "ⵉ"), ("j", "ⵊ"), ("k", "ⴽ"), ("l", "ⵍ"),
    ("m", "ⵎ"), ("n", "ⵏ"), ("q", "ⵇ"), ("r", "ⵔ"), ("s", "ⵙ"), ("t", "ⵜ"),
    ("u", "ⵓ"), ("v", "ⵠ"), ("w", "ⵡ"), ("x", "ⵅ"), ("y", "ⵢ"), ("z", "ⵣ"),
]


def _latin_berber_to_tifinagh(latin_text: str) -> str:
    """
    Translittère de façon déterministe un texte en alphabet latin
    berbère vers le Tifinagh, caractère par caractère (en testant les
    digraphes en premier). Les espaces, la ponctuation et les caractères
    non reconnus sont laissés tels quels.

    Contrairement à demander directement du Tifinagh à un LLM (qui
    invente souvent des glyphes incohérents), cette approche garantit
    un résultat toujours composé de vrais caractères Tifinagh valides.
    """
    text = latin_text.lower().strip()
    result = []
    i = 0
    while i < len(text):
        matched = False
        for latin, tifinagh in _LATIN_BERBER_TO_TIFINAGH:
            if text.startswith(latin, i):
                result.append(tifinagh)
                i += len(latin)
                matched = True
                break
        if not matched:
            result.append(text[i])  # espace, ponctuation, chiffre, etc.
            i += 1
    return re.sub(r" +", " ", "".join(result)).strip()


def _contains_tifinagh(text: str) -> bool:
    """
    Détecte si un texte contient déjà des caractères Tifinagh (bloc
    Unicode U+2D30-U+2D7F), signe que le modèle a ignoré la consigne de
    répondre en alphabet latin.
    """
    return any("\u2d30" <= ch <= "\u2d7f" for ch in text)


def translate_with_ai(text: str, target_lang: str):
    """
    Traduit un texte français vers une langue cible via l'IA, à la place
    d'un service de traduction externe (ex : scraping Google Translate,
    qui peut être bloqué ou instable selon les réseaux).

    'darija' et 'amazigh' ont des prompts dédiés (script et registre
    particuliers) plutôt que le prompt générique par nom de langue.

    Renvoie None si l'IA est indisponible ou si l'appel échoue -- l'appelant
    doit alors proposer un repli (ex : dictionnaire rule-based ou message
    d'erreur explicite, plutôt qu'un texte silencieusement faux).
    """
    if target_lang == "amazigh":
        # Demander directement du Tifinagh au modèle produit souvent des
        # glyphes incohérents (le tamazight en Tifinagh est très peu
        # représenté dans les données d'entraînement). On demande plutôt
        # une traduction en alphabet latin berbère standard -- bien mieux
        # couvert (Kabyle Wikipédia, presse, etc.) -- puis on translittère
        # nous-mêmes vers le Tifinagh avec une table de correspondance
        # fixe, ce qui garantit des caractères valides.
        prompt = (
            "Traduis le texte français suivant en tamazight (berbère), "
            "écrit UNIQUEMENT en alphabet latin standard (ex : 'azul', "
            "'tanemmirt', avec 'ɣ' pour gh, 'ɛ' pour la pharyngale, 'ḥ' "
            "si besoin). N'utilise JAMAIS de caractères Tifinagh "
            "(ⴰⵣⵓⵍ, ⵜ, ⵎ...) dans ta réponse, même partiellement -- "
            "uniquement des lettres latines. Garde le même sens, "
            "registre naturel. Réponds uniquement avec le texte traduit "
            "en latin, sans guillemets, sans explication.\n\n"
            f"Texte : {text}"
        )
        latin_result = _call_groq(
            [{"role": "user", "content": prompt}], max_tokens=300, temperature=0.1
        )
        if not latin_result:
            return None

        if _contains_tifinagh(latin_result):
            # Le modèle a ignoré la consigne et répondu directement en
            # Tifinagh (risque d'hallucination) -- on retente une seule
            # fois avec un rappel encore plus explicite avant d'abandonner.
            retry_prompt = (
                prompt
                + "\n\nATTENTION : ta réponse précédente contenait des "
                "caractères Tifinagh, ce qui est INTERDIT. Réécris la "
                "traduction en alphabet LATIN UNIQUEMENT, lettre par "
                "lettre (a, b, c... pas ⴰ, ⴱ, ⵛ...)."
            )
            latin_result = _call_groq(
                [{"role": "user", "content": retry_prompt}],
                max_tokens=300,
                temperature=0.1,
            )
            if not latin_result or _contains_tifinagh(latin_result):
                return None  # repli sur le dictionnaire côté appelant

        return _latin_berber_to_tifinagh(latin_result)

    if target_lang == "darija":
        prompt = (
            "Traduis le texte français suivant en darija marocain "
            "(arabe dialectal marocain), écrit en lettres latines "
            "(transcription phonétique courante, ex : 'bghit nmchi', "
            "pas en alphabet arabe). Garde le même sens et un registre "
            "naturel et parlé. Réponds uniquement avec le texte traduit, "
            "sans guillemets, sans explication.\n\n"
            f"Texte : {text}"
        )
        return _call_groq([{"role": "user", "content": prompt}], max_tokens=300, temperature=0.3)

    lang_name = _LANGUAGE_NAMES.get(target_lang, target_lang)
    prompt = (
        f"Traduis le texte suivant du français vers le {lang_name}. "
        "Garde exactement le même sens et le même registre. Réponds "
        "uniquement avec le texte traduit, sans guillemets, sans "
        "explication, sans commentaire.\n\n"
        f"Texte : {text}"
    )
    return _call_groq(
        [{"role": "user", "content": prompt}], max_tokens=300, temperature=0.2
    )


def translate_to_french(text: str, source_lang: str):
    """
    Traduit vers le français depuis le darija ou l'amazigh (écriture
    arabe, tifinagh ou latine -- toutes prises en charge par l'IA,
    contrairement au dictionnaire rule-based qui ne connaît que la
    transcription latine).

    Utilisé comme pivot avant correction/traduction/reformulation quand
    le texte d'entrée n'est pas déjà en français. Renvoie None si l'IA
    est indisponible ou échoue -- l'appelant doit alors proposer un
    repli (dictionnaire rule-based, ou texte inchangé).
    """
    if source_lang == "darija":
        prompt = (
            "Traduis le texte suivant, écrit en darija marocain (arabe "
            "dialectal marocain, en alphabet arabe OU en lettres "
            "latines), vers le français standard. Garde le même sens et "
            "le même registre. Réponds uniquement avec la traduction "
            "en français, sans guillemets, sans explication.\n\n"
            f"Texte : {text}"
        )
    elif source_lang == "amazigh":
        prompt = (
            "Traduis le texte suivant, écrit en tamazight (berbère, en "
            "alphabet Tifinagh OU en lettres latines), vers le français "
            "standard. Garde le même sens. Réponds uniquement avec la "
            "traduction en français, sans guillemets, sans explication.\n\n"
            f"Texte : {text}"
        )
    else:
        return None

    return _call_groq(
        [{"role": "user", "content": prompt}], max_tokens=300, temperature=0.2
    )
