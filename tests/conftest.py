"""
Fixtures partagées par toute la suite de tests.

Principes suivis dans ces tests (voir aussi chaque fichier test_*.py) :
- Aucun test ne doit dépendre d'un service externe réellement disponible
  (LanguageTool, Groq, Tesseract) : tout est mocké explicitement, pour
  que `pytest` tourne pareil sur n'importe quelle machine, sans clé API
  ni serveur LanguageTool lancé.
- On teste le comportement observable (réponse HTTP, JSON renvoyé), pas
  les détails d'implémentation internes.
"""

import io

import pytest
from PIL import Image

from app import create_app
from app.config import TestConfig


@pytest.fixture
def app():
    """Instance Flask configurée pour les tests (rate limiting désactivé,
    IA désactivée par défaut, TESTING=True)."""
    application = create_app(TestConfig)
    yield application


@pytest.fixture
def client(app):
    """Client de test Flask, pour simuler des requêtes HTTP sans serveur réel."""
    return app.test_client()


@pytest.fixture
def mock_languagetool_unavailable(monkeypatch):
    """
    Simule un serveur LanguageTool injoignable (comme si le service
    externe était éteint ou le réseau coupé). Toutes les routes doivent
    continuer à répondre normalement (repli propre), jamais planter.
    """
    import app.services.grammar_service as grammar_service

    monkeypatch.setattr(grammar_service, "check_with_languagetool", lambda text, lang="fr": None)


@pytest.fixture
def mock_languagetool_no_errors(monkeypatch):
    """Simule LanguageTool disponible mais qui ne trouve aucune erreur."""
    import app.services.grammar_service as grammar_service

    monkeypatch.setattr(grammar_service, "check_with_languagetool", lambda text, lang="fr": [])


def _lt_match(offset, length, original, suggestion, message="Faute détectée"):
    return {
        "offset": offset,
        "length": length,
        "replacements": [{"value": suggestion}],
        "message": message,
    }


@pytest.fixture
def mock_languagetool_one_error(monkeypatch):
    """
    Simule LanguageTool disponible avec UNE erreur détectée sur "sa" ->
    "ça" dans le texte "Il fait sa demain." (fixture utilisée par
    plusieurs tests qui veulent un cas de correction concret et stable).
    """
    import app.services.grammar_service as grammar_service

    match = _lt_match(offset=8, length=2, original="sa", suggestion="ça")
    monkeypatch.setattr(grammar_service, "check_with_languagetool", lambda text, lang="fr": [match])


@pytest.fixture
def mock_ai_available(monkeypatch):
    """Simule une clé Groq configurée et fonctionnelle (is_ai_available() -> True)."""
    import app.ai.llm_service as llm_service

    monkeypatch.setattr(llm_service, "is_ai_available", lambda: True)
    return llm_service


@pytest.fixture
def mock_ai_unavailable(monkeypatch):
    """Simule l'absence de clé Groq (is_ai_available() -> False)."""
    import app.ai.llm_service as llm_service

    monkeypatch.setattr(llm_service, "is_ai_available", lambda: False)
    return llm_service


@pytest.fixture
def test_image_bytes() -> bytes:
    """Crée une petite image PNG en mémoire, pour tester /ocr sans dépendre
    d'un fichier sur disque."""
    img = Image.new("RGB", (60, 20), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
