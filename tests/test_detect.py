"""
Tests de la route /detect-language.
"""


def test_detect_empty_text(client):
    resp = client.post("/detect-language", json={"text": ""})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] is None
    assert data["language_label"] is None


def test_detect_arabic_script_is_darija(client):
    resp = client.post("/detect-language", json={"text": "سلام لباس"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "darija"
    assert data["confidence"] == "Élevée"


def test_detect_tifinagh_script_is_amazigh(client):
    resp = client.post("/detect-language", json={"text": "ⴰⵣⵓⵍ"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "amazigh"
    assert data["confidence"] == "Élevée"


def test_detect_french_stopwords(client):
    resp = client.post("/detect-language", json={"text": "je suis très content de vous voir"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "french"


def test_detect_latin_darija_words(client):
    resp = client.post("/detect-language", json={"text": "salam khouya labas"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "darija"


def test_detect_unrecognized_text_defaults_to_standard(client):
    resp = client.post("/detect-language", json={"text": "xyzxyz qwerty"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["language"] == "standard"


def test_detect_text_too_long_is_rejected(client):
    resp = client.post("/detect-language", json={"text": "a" * 6000})

    assert resp.status_code == 400
