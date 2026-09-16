"""
Cœur du NLU : Étapes A et B du prompt maître (Intent Detection + Entity Extraction).

Approche volontairement simple (section 40 - règle de simplicité) :
un matching par mots-clés normalisés, sans dépendance ML lourde. C'est
suffisant pour un MVP avec un nombre limité de procédures (section 25),
déterministe, et 100% explicable (pas de boîte noire) — ce qui colle
avec le principe "ne jamais halluciner" du projet (section 4).

Si le projet grandit, cette fonction peut être remplacée par un appel à un
LLM (section 16 : "LLM API ou modèle open-source selon les contraintes")
sans changer le contrat de l'endpoint /analyze.
"""

import re
import unicodedata
from difflib import SequenceMatcher

from intents import INTENTS, THRESHOLD_DIRECT, THRESHOLD_SUGGEST

# Mots qui, s'ils apparaissent, indiquent une "première demande"
FIRST_TIME_MARKERS = ["première", "premiere", "nouveau", "nouvelle", "jamais eu", "jdid"]
# Mots qui indiquent un renouvellement
RENEWAL_MARKERS = ["renouveler", "renouvellement", "refaire", "expiré", "expire", "jdd"]

ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06FF]")

# Mots-clés d'un seul mot, courants dans la langue de tous les jours, qui
# apparaissent souvent SANS rapport avec la démarche administrative visée
# (ex: "société" dans "Société Générale recrute", "voiture" dans "ma voiture
# est en panne"). Un match sur un seul de ces mots ne doit jamais suffire,
# à lui seul, à dépasser THRESHOLD_SUGGEST : on baisse son score plancher
# au lieu de le retirer purement, pour qu'il reste un signal utile SI un
# autre mot-clé de la même intention matche aussi (le meilleur des deux
# scores est gardé par le max() de l'appelant).
GENERIC_SINGLE_WORDS = {"societe", "voiture", "etudiant"}


def normalize(text: str) -> str:
    """Minuscule, sans accents, espaces normalisés."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"\s+", " ", text)
    return text


def detect_language(raw_text: str) -> str:
    """Détection grossière : écriture arabe -> 'arabic'. Sinon on ne peut pas
    distinguer fiablement français / darija latinisée sans modèle dédié,
    donc on renvoie 'french_or_darija' et on laisse le matching par mots-clés
    faire le travail (les deux lexiques sont fusionnés dans INTENTS)."""
    if ARABIC_SCRIPT_RE.search(raw_text):
        return "ar"
    return "fr"


def _keyword_score(normalized_text: str, keywords: list[str]) -> float:
    """Score = meilleur match parmi les mots-clés, combinant présence exacte
    (substring) et similarité approximative (tolère les fautes de frappe,
    section 32 du prompt maître).

    Correction (voir revue de code) : l'ancienne formule donnait un score
    plancher de 0.75 à N'IMPORTE QUEL mot-clé dès qu'il apparaissait en
    sous-chaîne, même un mot isolé très courant ("société", "voiture",
    "étudiant"). Résultat : "Société Générale recrute" ou "ma voiture est
    en panne" étaient classés à tort comme une démarche administrative
    avec 0.80 de confiance. On garde le score fort pour les expressions
    multi-mots (spécifiques par nature) et pour les mots uniques mais rares
    (acronymes comme "cnss", "anapec"...), et on baisse le score des mots
    uniques identifiés comme génériques (GENERIC_SINGLE_WORDS)."""
    best = 0.0
    for kw in keywords:
        kw_norm = normalize(kw)
        if kw_norm in normalized_text:
            word_count = len(kw_norm.split())
            if word_count >= 2:
                # Expression multi-mots : signal fort, quasiment jamais un faux positif.
                score = min(1.0, 0.80 + 0.03 * word_count)
            elif kw_norm in GENERIC_SINGLE_WORDS:
                # Mot unique mais courant/ambigu hors contexte : signal faible
                # à lui seul (reste sous THRESHOLD_SUGGEST).
                score = 0.45
            else:
                # Mot unique et spécifique (acronyme, terme métier rare) :
                # score fort, proportionnel à sa longueur.
                score = min(1.0, 0.75 + 0.05 * word_count)
            best = max(best, score)
        else:
            # Similarité approximative (fautes d'orthographe)
            ratio = SequenceMatcher(None, kw_norm, normalized_text).ratio()
            # On ne prend en compte la similarité globale que pour des textes courts
            # sinon un mot-clé de 5 lettres noyé dans une longue phrase pénalise à tort
            for word in normalized_text.split():
                word_ratio = SequenceMatcher(None, kw_norm, word).ratio()
                best = max(best, word_ratio * 0.7)
            best = max(best, ratio * 0.5)
    return min(best, 1.0)


def detect_intent(raw_text: str) -> dict:
    """Retourne l'intention la plus probable + son score de confiance,
    ainsi que les 2-3 meilleures alternatives (pour la zone de confiance
    intermédiaire, section 28)."""
    normalized = normalize(raw_text)
    scores = []
    for intent_code, data in INTENTS.items():
        score = _keyword_score(normalized, data["keywords"])
        scores.append({"intent": intent_code, "label": data["label"], "confidence": round(score, 2)})

    scores.sort(key=lambda x: x["confidence"], reverse=True)
    top = scores[0] if scores else {"intent": None, "label": None, "confidence": 0.0}

    return {
        "top": top,
        "alternatives": scores[1:3],
        "all_scores": scores,
    }


def extract_entities(raw_text: str) -> dict:
    """Étape B : extraction d'entités simples (section 6 et 13-B)."""
    normalized = normalize(raw_text)
    entities = {}

    if any(m in normalized for m in FIRST_TIME_MARKERS):
        entities["request_type"] = "first_time"
    elif any(m in normalized for m in RENEWAL_MARKERS):
        entities["request_type"] = "renewal"

    age_match = re.search(r"\b(\d{1,2})\s*ans?\b", normalized)
    if age_match:
        entities["age"] = int(age_match.group(1))

    return entities


def analyze(raw_text: str) -> dict:
    """Point d'entrée principal : combine langue + intention + entités,
    puis applique les seuils de confiance (section 28) pour décider de
    l'action : réponse directe / suggestions / clarification."""
    language = detect_language(raw_text)
    intent_result = detect_intent(raw_text)
    entities = extract_entities(raw_text)

    top = intent_result["top"]
    confidence = top["confidence"]

    if confidence >= THRESHOLD_DIRECT:
        action = "direct"
    elif confidence >= THRESHOLD_SUGGEST:
        action = "suggest"
    else:
        action = "clarify"

    return {
        "input": raw_text,
        "language": language,
        "intent": top["intent"],
        "intent_label": top["label"],
        "confidence": confidence,
        "action": action,
        "alternatives": intent_result["alternatives"],
        "entities": entities,
    }
