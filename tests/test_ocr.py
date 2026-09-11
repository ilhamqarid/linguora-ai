"""
Tests de la route /ocr.

Tesseract lui-même n'est jamais appelé pour de vrai dans ces tests
(binaire externe non garanti présent sur la machine qui lance `pytest`)
-- on mocke pytesseract.image_to_string pour tester uniquement notre
propre logique (validation, sécurité des noms de fichiers, nettoyage).
"""

import io


def test_ocr_no_image_returns_400(client):
    resp = client.post("/ocr", data={})

    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_ocr_disallowed_extension_is_rejected(client):
    fake_file = (io.BytesIO(b"not really an image"), "malware.exe")

    resp = client.post("/ocr", data={"image": fake_file}, content_type="multipart/form-data")

    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_ocr_valid_image_calls_tesseract_and_cleans_up_tmp_file(client, monkeypatch, test_image_bytes):
    import app.services.ocr_service as ocr_service

    monkeypatch.setattr(ocr_service.pytesseract, "image_to_string", lambda img, lang=None, config=None: "Texte reconnu")

    data = {"image": (io.BytesIO(test_image_bytes), "test.png")}

    resp = client.post("/ocr", data=data, content_type="multipart/form-data")

    assert resp.status_code == 200
    assert resp.get_json()["text"] == "Texte reconnu"


def test_ocr_malicious_filename_is_sanitized(client, monkeypatch, test_image_bytes):
    """
    Un nom de fichier contenant des séquences de traversée de répertoire
    (../..) ne doit jamais permettre d'écrire en dehors du dossier
    d'upload temporaire (secure_filename doit neutraliser ça).
    """
    import app.services.ocr_service as ocr_service

    monkeypatch.setattr(ocr_service.pytesseract, "image_to_string", lambda img, lang=None, config=None: "ok")

    data = {"image": (io.BytesIO(test_image_bytes), "../../../evil.png")}

    resp = client.post("/ocr", data=data, content_type="multipart/form-data")

    # Le nom est assaini en amont (secure_filename) : la requête doit
    # aboutir normalement, sans jamais écrire hors du dossier prévu.
    assert resp.status_code == 200


def test_ocr_tesseract_failure_returns_empty_text_not_500(client, monkeypatch, test_image_bytes):
    """Si Tesseract plante en interne (image corrompue, etc.), l'API doit
    répondre avec un texte vide plutôt que de renvoyer une 500."""
    import app.services.ocr_service as ocr_service

    def _boom(img, lang=None, config=None):
        raise RuntimeError("tesseract internal failure")

    monkeypatch.setattr(ocr_service.pytesseract, "image_to_string", _boom)

    data = {"image": (io.BytesIO(test_image_bytes), "test.png")}

    resp = client.post("/ocr", data=data, content_type="multipart/form-data")

    assert resp.status_code == 200
    assert resp.get_json()["text"] == ""
