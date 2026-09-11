from typing import Optional

from flask import current_app


def text_length_error(text: str) -> Optional[str]:
    """
    Vérifie qu'un texte ne dépasse pas MAX_TEXT_LENGTH (config).

    Renvoie un message d'erreur (str) si le texte est trop long, sinon
    None. Ne fait rien d'autre (pas de troncature silencieuse) : on
    préfère un rejet explicite à un texte coupé à moitié sans prévenir
    l'utilisateur.
    """
    max_length = current_app.config.get("MAX_TEXT_LENGTH", 5000)
    if len(text) > max_length:
        return f"Texte trop long ({len(text)} caractères, maximum {max_length})."
    return None
