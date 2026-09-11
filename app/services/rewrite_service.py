import re


def _lowercase_leading_word(text: str) -> str:
    """
    Met en minuscule le premier mot de 'text' pour l'insérer dans une
    subordonnée ("Je me permets de vous informer que <text>").

    Corrige un bug de la version originale : abaisser uniquement le
    premier CARACTÈRE cassait les phrases tapées en MAJUSCULES
    (ex: "JE VEUX MANGER" -> "jE VEUX MANGER" au lieu de "je veux manger").
    On abaisse maintenant tout le premier mot si celui-ci est un mot
    "hurlé" (tout en majuscules), sinon on garde l'ancien comportement
    (juste la première lettre) pour ne pas casser un nom propre en
    milieu de mot capitalisé normalement (ex: "Paris" reste "Paris").
    """
    if not text:
        return text

    parts = text.split(" ", 1)
    first_word = parts[0]
    rest = f" {parts[1]}" if len(parts) > 1 else ""

    if len(first_word) > 1 and first_word.isupper():
        first_word = first_word.lower()
    else:
        first_word = first_word[0].lower() + first_word[1:]

    return first_word + rest


def _apply_word_replacements(text: str, replacements: dict) -> str:
    """
    Remplace les mots-clés indépendamment de leur casse (insensible à la
    casse), en réappliquant une majuscule au remplacement si le mot
    d'origine en avait une.

    Corrige un bug de la version originale : les remplacements étaient
    sensibles à la casse, donc "Tu es content." (majuscule ajoutée par
    tidy_french) ne matchait jamais la clé "tu" et n'était jamais
    reformulé en "vous".
    """
    for old, new in replacements.items():
        pattern = re.compile(re.escape(old), re.IGNORECASE)

        def _replace(match, new=new):
            matched = match.group(0)
            if matched[:1].isupper():
                return new[:1].upper() + new[1:]
            return new

        text = pattern.sub(_replace, text)
    return text


def rephrase_with_tone(corrected_fr: str, tone: str) -> str:
    """
    Reformulation par remplacements de mots-clés (rule-based, PAS de l'IA).
    Tons supportés : 'professional', 'friendly', autre => neutre.
    """
    base = corrected_fr.strip()

    replacements_pro = {
        "tu": "vous",
        "t'": "vous ",
        "salut": "bonjour",
        "ça": "cela",
    }
    replacements_friendly = {
        "bonjour": "salut",
        "je vous informe": "je voulais te dire",
        "je souhaite vous informer": "je voulais te prévenir",
        "nous": "on",
    }

    if tone == "professional":
        intro = "Je me permets de vous informer que "
        base = _apply_word_replacements(base, replacements_pro)
    elif tone == "friendly":
        intro = "Franchement, "
        base = _apply_word_replacements(base, replacements_friendly)
    else:
        intro = ""

    if base and intro:
        # On ne rabaisse la casse que si on insère le texte dans une
        # subordonnée (intro non vide). En ton neutre, on ne touche pas
        # à la casse d'origine.
        base = _lowercase_leading_word(base)

    return intro + base
