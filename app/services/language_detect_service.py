from app.data.dictionaries import DARIJA_FR, AMAZIGH_FR
from app.utils.text_utils import PUNCT

# Mots-outils français très courants, utilisés seulement pour distinguer
# "probablement du français" de "aucun signal reconnu" (texte vide, bruit,
# ou une langue non supportée). Ce n'est PAS un détecteur de langue général.
FRENCH_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "je", "tu", "il",
    "elle", "nous", "vous", "ils", "elles", "et", "est", "es", "suis",
    "sont", "que", "qui", "pour", "avec", "dans", "sur", "ne", "pas",
    "au", "aux", "ce", "cette", "mon", "ma", "mes", "ton", "ta", "tes",
    "son", "sa", "ses", "à", "en", "on", "se", "plus", "bien",
}


def detect_source_lang(text: str) -> tuple:
    """
    Détection heuristique (PAS un modèle ML) de la langue d'entrée.

    Renvoie un tuple (label, confidence) :
    - label : 'darija' | 'amazigh' | 'french' | 'standard'
      ('standard' = aucun signal clair, on suppose français par défaut)
    - confidence : 'Élevée' | 'Moyenne' | 'Faible'

    Règles, dans l'ordre :
    1. Caractères Tifinagh présents      -> amazigh, confiance élevée
    2. Caractères arabes présents        -> darija (convention produit),
       confiance élevée
    3. Sinon, on compte les mots reconnus dans nos dictionnaires
       Darija / Amazigh (écriture latine) et les mots-outils français.

    Cette détection peut se tromper sur des phrases courtes, mixtes ou
    ambiguës -- voir README > Limitations.
    """
    if not text or not text.strip():
        return "standard", "Faible"

    if any("\u2D30" <= ch <= "\u2D7F" for ch in text):
        return "amazigh", "Élevée"

    if any("\u0600" <= ch <= "\u06FF" for ch in text):
        return "darija", "Élevée"

    tokens = [w.strip(PUNCT).lower() for w in text.split() if w.strip(PUNCT)]
    if not tokens:
        return "standard", "Faible"

    darija_matches = sum(1 for t in tokens if t in DARIJA_FR)
    amazigh_matches = sum(1 for t in tokens if t in AMAZIGH_FR)
    french_matches = sum(1 for t in tokens if t in FRENCH_STOPWORDS)

    if darija_matches == 0 and amazigh_matches == 0:
        french_ratio = french_matches / len(tokens)
        if french_ratio >= 0.5:
            return "french", "Élevée"
        if french_ratio >= 0.2:
            return "french", "Moyenne"
        return "standard", "Faible"

    if darija_matches >= amazigh_matches:
        ratio = darija_matches / len(tokens)
        confidence = "Élevée" if ratio >= 0.5 else "Moyenne" if ratio >= 0.25 else "Faible"
        return "darija", confidence

    ratio = amazigh_matches / len(tokens)
    confidence = "Élevée" if ratio >= 0.5 else "Moyenne" if ratio >= 0.25 else "Faible"
    return "amazigh", confidence
