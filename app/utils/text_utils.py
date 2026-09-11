import re
import string

PUNCT = string.punctuation + "«»¿؟…"

_REPEAT_RE = re.compile(r"(.)\1{2,}")


def _collapse_repeats(word: str) -> str:
    """
    Réduit les lettres répétées 3 fois ou plus à une seule occurrence.
    Utile pour le langage informel (chat/SMS) : "mzyannn" -> "mzyan",
    "salaaam" -> "salam". Simple heuristique, pas du NLP.
    """
    return _REPEAT_RE.sub(r"\1", word)


def simple_dict_translate(text: str, mapping: dict) -> str:
    """
    Remplace chaque mot présent dans le dictionnaire par sa traduction.
    Essaie d'abord une correspondance exacte, puis -- si elle échoue --
    une correspondance après réduction des lettres répétées.
    Mot toujours inconnu => inchangé. Ponctuation en début/fin préservée.
    """
    words = text.split()
    result_words = []

    for w in words:
        if not w:
            continue

        prefix = ""
        suffix = ""

        while len(w) > 0 and w[0] in PUNCT:
            prefix += w[0]
            w = w[1:]

        while len(w) > 0 and w[-1] in PUNCT:
            suffix = w[-1] + suffix
            w = w[:-1]

        base = w.lower()
        translated = mapping.get(base)

        if translated is None:
            collapsed = _collapse_repeats(base)
            translated = mapping.get(collapsed, w)

        result_words.append(prefix + translated + suffix)

    return " ".join(result_words)
