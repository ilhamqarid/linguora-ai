"""
Tests de la route /translate.
"""


def test_translate_empty_text_returns_empty(client):
    resp = client.post("/translate", json={"text": "", "target_lang": "en"})

    assert resp.status_code == 200
    assert resp.get_json()["translated_text"] == ""


def test_translate_target_fr_returns_pivoted_text_unchanged(client, mock_languagetool_no_errors):
    """Quand la cible est le français, /translate doit renvoyer le texte
    (déjà en français, ou pivoté) sans appeler de service de traduction."""
    resp = client.post("/translate", json={
        "text": "bonjour",
        "target_lang": "fr",
        "source_lang": "standard",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is False
    assert "bonjour" in data["translated_text"].lower()


def test_translate_darija_latin_to_french_via_dictionary(client, mock_languagetool_no_errors, mock_ai_unavailable):
    """Sans IA disponible, le pivot Darija (latin) -> français doit passer
    par le dictionnaire rule-based (ex: "salam" -> "bonjour")."""
    resp = client.post("/translate", json={
        "text": "salam",
        "target_lang": "fr",
        "source_lang": "darija",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert "bonjour" in data["translated_text"].lower()


def test_translate_darija_arabic_script_falls_back_to_dictionary_when_ai_unavailable(
    client, mock_languagetool_no_errors, mock_ai_unavailable
):
    """
    Le dictionnaire ne connaît que la transcription latine. En écriture
    arabe, sans IA, le pivot ne peut PAS traduire correctement -- on
    vérifie ici que ça ne plante pas (contrat minimal), pas que le
    résultat est juste (limite connue et documentée dans le README).
    """
    resp = client.post("/translate", json={
        "text": "سلام",
        "target_lang": "fr",
        "source_lang": "darija",
    })

    assert resp.status_code == 200
    assert isinstance(resp.get_json()["translated_text"], str)


def test_translate_uses_ai_when_available(client, mock_languagetool_no_errors, mock_ai_available, monkeypatch):
    """Quand l'IA est disponible, /translate doit l'utiliser en priorité
    et le signaler via used_ai=True."""
    import app.ai.llm_service as llm_service

    monkeypatch.setattr(llm_service, "translate_with_ai", lambda text, target: "I want to eat")

    resp = client.post("/translate", json={
        "text": "je veux manger",
        "target_lang": "en",
        "source_lang": "fr",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is True
    assert data["translated_text"] == "I want to eat"


def test_translate_falls_back_when_ai_call_fails(client, mock_languagetool_no_errors, mock_ai_available, monkeypatch):
    """Si l'IA est configurée mais que l'appel échoue (renvoie None), la
    route doit retomber sur un repli plutôt que planter ou renvoyer du vide."""
    import app.ai.llm_service as llm_service
    import app.services.translation_service as translation_service

    monkeypatch.setattr(llm_service, "translate_with_ai", lambda text, target: None)
    monkeypatch.setattr(
        translation_service,
        "GoogleTranslator",
        lambda source, target: type("FakeTranslator", (), {"translate": lambda self, t: "fallback ok"})(),
    )

    resp = client.post("/translate", json={
        "text": "bonjour",
        "target_lang": "en",
        "source_lang": "fr",
    })

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["used_ai"] is False
    assert data["translated_text"] == "fallback ok"


def test_translate_text_too_long_is_rejected(client):
    resp = client.post("/translate", json={"text": "a" * 6000, "target_lang": "en"})

    assert resp.status_code == 400
