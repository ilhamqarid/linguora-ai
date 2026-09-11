"""
Tests de la route /rephrase (reformulation par règles).
"""


def test_rephrase_empty_text_returns_empty(client):
    resp = client.post("/rephrase", json={"text": "", "tone": "professional"})

    assert resp.status_code == 200
    assert resp.get_json()["rephrased_text"] == ""


def test_rephrase_professional_tone_replaces_tu_with_vous(client, mock_languagetool_no_errors):
    resp = client.post("/rephrase", json={
        "text": "tu es content",
        "source_lang": "standard",
        "tone": "professional",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "vous" in data["rephrased_text"].lower()
    assert "tu " not in data["rephrased_text"].lower()


def test_rephrase_friendly_tone_replaces_bonjour_with_salut(client, mock_languagetool_no_errors):
    resp = client.post("/rephrase", json={
        "text": "Bonjour, je vous informe que le colis est arrivé.",
        "source_lang": "standard",
        "tone": "friendly",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "salut" in data["rephrased_text"].lower()


def test_rephrase_neutral_tone_keeps_text_mostly_unchanged(client, mock_languagetool_no_errors):
    resp = client.post("/rephrase", json={
        "text": "Bonjour à tous.",
        "source_lang": "standard",
        "tone": "neutral",
    })

    assert resp.status_code == 200
    assert "Bonjour" in resp.get_json()["rephrased_text"]


def test_rephrase_when_languagetool_unavailable_still_works(client, mock_languagetool_unavailable):
    """Le pivot vers le français doit continuer à fonctionner même si
    LanguageTool est injoignable (juste pas de correction automatique)."""
    resp = client.post("/rephrase", json={
        "text": "tu es la",
        "source_lang": "standard",
        "tone": "professional",
    })

    assert resp.status_code == 200
    assert resp.get_json()["rephrased_text"]


def test_rephrase_internal_error_returns_generic_message_not_stack_trace(client, mock_languagetool_no_errors, monkeypatch):
    """Si rephrase_with_tone lève une exception inattendue, la route ne
    doit jamais renvoyer le message d'exception brut au client."""
    import app.routes.rewrite as rewrite_route

    def _boom(text, tone):
        raise RuntimeError("chemin secret /etc/xyz ou détail interne sensible")

    monkeypatch.setattr(rewrite_route, "rephrase_with_tone", _boom)

    resp = client.post("/rephrase", json={"text": "bonjour", "tone": "neutral"})

    assert resp.status_code == 500
    body = resp.get_json()
    assert "chemin secret" not in str(body)
    assert "RuntimeError" not in str(body)


def test_rephrase_text_too_long_is_rejected(client):
    resp = client.post("/rephrase", json={"text": "a" * 6000, "tone": "neutral"})

    assert resp.status_code == 400
