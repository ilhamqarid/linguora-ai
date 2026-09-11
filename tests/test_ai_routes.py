"""
Tests des routes /api/ai/* (correction, explication, reformulation
contextuelles). L'IA (Groq) n'est JAMAIS réellement appelée dans ces
tests : is_ai_available() et les fonctions de llm_service sont mockées,
pour un comportement 100% déterministe et sans dépendance réseau.

Note d'implémentation : app/routes/ai.py fait
`from app.ai.llm_service import is_ai_available, ...` (import direct de
noms), donc on monkeypatch `app.routes.ai.is_ai_available` -- patcher
`app.ai.llm_service.is_ai_available` n'aurait aucun effet ici, puisque
la route a déjà sa propre référence locale vers la fonction d'origine.
"""

import app.routes.ai as ai_route


def test_ai_correct_empty_text_returns_empty(client):
    resp = client.post("/api/ai/correct", json={"text": ""})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["corrected_text"] == ""
    assert data["used_ai"] is False


def test_ai_correct_uses_ai_when_available(client, monkeypatch):
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: True)
    monkeypatch.setattr(ai_route, "correct_with_context", lambda text: "JE VEUX MANGER")

    resp = client.post("/api/ai/correct", json={"text": "JE VUX MONGER"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is True
    assert data["corrected_text"] == "JE VEUX MANGER"


def test_ai_correct_falls_back_to_rules_when_ai_unavailable(client, monkeypatch, mock_languagetool_one_error):
    """Sans clé Groq configurée, /api/ai/correct doit retomber sur le
    pipeline LanguageTool existant plutôt que d'échouer."""
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: False)

    resp = client.post("/api/ai/correct", json={"text": "Il fait sa demain."})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is False
    assert "ça" in data["corrected_text"]


def test_ai_correct_falls_back_when_ai_call_returns_none(client, monkeypatch, mock_languagetool_no_errors):
    """L'IA est configurée mais l'appel échoue (quota, réseau...) : la
    route doit retomber sur les règles, pas planter."""
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: True)
    monkeypatch.setattr(ai_route, "correct_with_context", lambda text: None)

    resp = client.post("/api/ai/correct", json={"text": "Bonjour."})

    assert resp.status_code == 200
    assert resp.get_json()["used_ai"] is False


def test_ai_correct_text_too_long_is_rejected(client):
    resp = client.post("/api/ai/correct", json={"text": "a" * 6000})

    assert resp.status_code == 400


def test_ai_explain_without_ai_available(client, monkeypatch):
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: False)

    resp = client.post("/api/ai/explain", json={
        "original": "sa",
        "suggestion": "ça",
        "sentence": "Il fait sa demain.",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ai_available"] is False
    assert data["explanation"] is None


def test_ai_explain_with_ai_available(client, monkeypatch):
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: True)
    monkeypatch.setattr(
        ai_route, "explain_correction",
        lambda original, suggestion, sentence: "'sa' est un déterminant, 'ça' est un pronom.",
    )

    resp = client.post("/api/ai/explain", json={
        "original": "sa",
        "suggestion": "ça",
        "sentence": "Il fait sa demain.",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ai_available"] is True
    assert "pronom" in data["explanation"]


def test_ai_rewrite_empty_text(client):
    resp = client.post("/api/ai/rewrite", json={"text": "", "tone": "neutral"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["rewritten_text"] == ""
    assert data["used_ai"] is False


def test_ai_rewrite_uses_ai_when_available(client, monkeypatch):
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: True)
    monkeypatch.setattr(ai_route, "rewrite_with_context", lambda text, tone: "Texte reformulé par IA")

    resp = client.post("/api/ai/rewrite", json={"text": "Bonjour", "tone": "professional"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is True
    assert data["rewritten_text"] == "Texte reformulé par IA"


def test_ai_rewrite_falls_back_without_network_call_when_ai_unavailable(client, monkeypatch):
    """Sans clé configurée, la route ne doit PAS tenter d'appel réseau du
    tout -- juste utiliser le repli par règles immédiatement."""
    monkeypatch.setattr(ai_route, "is_ai_available", lambda: False)

    resp = client.post("/api/ai/rewrite", json={"text": "tu es content", "tone": "professional"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is False
    assert "vous" in data["rewritten_text"].lower()


def test_ai_rewrite_text_too_long_is_rejected(client):
    resp = client.post("/api/ai/rewrite", json={"text": "a" * 6000, "tone": "neutral"})

    assert resp.status_code == 400
