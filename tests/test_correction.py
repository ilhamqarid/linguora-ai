"""
Tests de la route /correct (correction interactive par règles).
"""


def test_correct_empty_text_returns_empty_without_crashing(client):
    resp = client.post("/correct", json={"text": ""})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["base_text"] == ""
    assert data["errors"] == []
    assert data["languagetool_available"] is True


def test_correct_missing_text_field_does_not_crash(client):
    """Un JSON sans clé "text" du tout doit être traité comme un texte vide,
    jamais provoquer une exception (KeyError, etc.)."""
    resp = client.post("/correct", json={})

    assert resp.status_code == 200
    assert resp.get_json()["base_text"] == ""


def test_correct_non_json_body_does_not_crash(client):
    """Un corps de requête qui n'est pas du JSON valide ne doit jamais
    faire planter la route (silent=True côté Flask + valeurs par défaut)."""
    resp = client.post("/correct", data="ceci n'est pas du JSON", content_type="text/plain")

    assert resp.status_code == 200
    assert resp.get_json()["base_text"] == ""


def test_correct_when_languagetool_unavailable_still_returns_200(client, mock_languagetool_unavailable):
    """Si LanguageTool est injoignable, l'API doit répondre normalement
    avec languagetool_available=False, jamais planter avec une 500."""
    resp = client.post("/correct", json={"text": "Il fait sa demain."})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["languagetool_available"] is False
    assert data["errors"] == []
    assert data["base_text"]  # le texte pivoté/nettoyé est quand même renvoyé


def test_correct_with_no_errors_found(client, mock_languagetool_no_errors):
    resp = client.post("/correct", json={"text": "Bonjour, comment allez-vous ?"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["languagetool_available"] is True
    assert data["errors"] == []


def test_correct_returns_detailed_error_with_suggestions(client, mock_languagetool_one_error):
    """Contrat de /correct : les erreurs renvoyées contiennent une
    position exacte et des suggestions -- c'est ce qui alimente le
    panneau interactif du frontend."""
    resp = client.post("/correct", json={"text": "Il fait sa demain."})

    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["errors"]) == 1
    error = data["errors"][0]
    assert error["original"] == "sa"
    assert "ça" in error["suggestions"]
    assert "start" in error and "length" in error


def test_correct_text_too_long_is_rejected(client):
    too_long = "a" * 6000  # > MAX_TEXT_LENGTH (5000 par défaut)

    resp = client.post("/correct", json={"text": too_long})

    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_correct_text_at_exact_limit_is_accepted(client, mock_languagetool_no_errors):
    exactly_max = "a" * 5000

    resp = client.post("/correct", json={"text": exactly_max})

    assert resp.status_code == 200
