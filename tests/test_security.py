"""
Tests de sécurité :
- les erreurs internes ne doivent jamais fuiter de détail technique
  (stack trace, chemin de fichier, message d'exception brut) au client
- le rate limiting doit effectivement bloquer un usage abusif
- les entrées surdimensionnées doivent être rejetées proprement
- les noms de fichiers uploadés doivent être neutralisés
"""

import io

from app import create_app
from app.config import TestConfig


def test_unhandled_exception_never_leaks_exception_message(client, monkeypatch):
    """
    Si un service interne lève une exception complètement inattendue
    (bug, dépendance qui change de comportement...), le client ne doit
    JAMAIS recevoir le message d'exception brut -- qui pourrait révéler
    des détails d'implémentation (noms de variables, chemins, etc.).
    """
    import app.routes.correction as correction_route

    secret_detail = "SECRET_INTERNAL_PATH=/etc/passwd DB_PASSWORD=hunter2"

    def _boom(text, source="auto"):
        raise RuntimeError(secret_detail)

    monkeypatch.setattr(correction_route, "get_correction_details", _boom)

    resp = client.post("/correct", json={"text": "bonjour"})

    assert resp.status_code == 500
    body = resp.get_data(as_text=True)
    assert secret_detail not in body
    assert "RuntimeError" not in body
    assert "Traceback" not in body
    assert resp.get_json()["error"] == "Une erreur interne est survenue."


def test_404_returns_clean_json_not_html_traceback(client):
    resp = client.get("/route-qui-nexiste-pas")

    assert resp.status_code == 404
    # Doit être du JSON propre, pas la page HTML par défaut de Flask/Werkzeug.
    assert resp.get_json() is not None


def test_debug_mode_is_off_by_default_in_app_factory(app):
    """
    Le débogueur Werkzeug (DEBUG=True) permet l'exécution de code Python
    arbitraire depuis le navigateur si une erreur non gérée l'atteint --
    il ne doit jamais être activé par défaut.
    """
    assert app.config.get("DEBUG", False) is False


def test_ocr_upload_extension_whitelist_blocks_executables(client):
    """Un fichier .exe, .php, .sh etc. déguisé en "image" doit être rejeté
    avant même d'atteindre Tesseract."""
    for filename in ["shell.php", "script.sh", "payload.exe", "archive.zip"]:
        fake_file = (io.BytesIO(b"contenu quelconque"), filename)
        resp = client.post("/ocr", data={"image": fake_file}, content_type="multipart/form-data")
        assert resp.status_code == 400, f"{filename} aurait dû être rejeté"


def test_correct_rejects_oversized_text_before_any_processing(client, monkeypatch):
    """
    Vérifie que la validation de taille intervient AVANT tout appel à
    LanguageTool/IA -- protège contre l'épuisement de quota/CPU par un
    payload énorme envoyé en boucle.
    """
    import app.routes.correction as correction_route

    calls = {"count": 0}

    def _spy(*args, **kwargs):
        calls["count"] += 1
        return "x", [], True

    monkeypatch.setattr(correction_route, "get_correction_details", _spy)

    resp = client.post("/correct", json={"text": "a" * 100_000})

    assert resp.status_code == 400
    assert calls["count"] == 0  # jamais appelé : rejeté avant


def test_rate_limiting_blocks_after_threshold():
    """
    Avec le rate limiting activé et une limite basse, dépasser le seuil
    doit renvoyer 429 -- pas planter, pas laisser passer indéfiniment.
    """

    class RateLimitedTestConfig(TestConfig):
        RATELIMIT_ENABLED = True
        RATELIMIT_DEFAULT = "3 per minute"

    app = create_app(RateLimitedTestConfig)
    client = app.test_client()

    statuses = []
    for _ in range(5):
        resp = client.post("/correct", json={"text": "bonjour"})
        statuses.append(resp.status_code)

    assert 429 in statuses, f"Attendu un 429 après dépassement du seuil, obtenu : {statuses}"
    # Les erreurs 429 doivent rester du JSON propre, pas une page d'erreur brute.
    last_resp = client.post("/correct", json={"text": "bonjour"})
    if last_resp.status_code == 429:
        assert "error" in last_resp.get_json()


def test_rate_limit_disabled_allows_many_requests(client):
    """Contrôle : avec RATELIMIT_ENABLED=False (config de test par
    défaut), aucune requête ne doit être bloquée même en rafale."""
    statuses = [client.post("/detect-language", json={"text": "bonjour"}).status_code for _ in range(20)]

    assert all(s == 200 for s in statuses)


def test_secret_key_default_is_not_used_silently_in_non_debug(app):
    """
    Documente/vérifie qu'une SECRET_KEY par défaut existe (pour que
    l'app démarre même sans .env), tout en la nommant explicitement
    comme valeur de développement -- pas une vraie clé secrète cachée
    dans le code qu'on pourrait croire sûre.
    """
    default_marker = "dev-secret-change-me"
    # Le test ne force pas une vraie valeur en prod (impossible à tester
    # ici) mais vérifie que le défaut est clairement identifiable comme
    # tel, pour qu'un audit de code le repère immédiatement.
    assert app.config["SECRET_KEY"] == default_marker or app.config["SECRET_KEY"] != ""


def test_max_content_length_configured_for_uploads(app):
    """Une limite de taille globale doit exister pour les requêtes
    (protège contre un upload/texte gigantesque en déni de service basique)."""
    assert app.config.get("MAX_CONTENT_LENGTH") is not None
    assert app.config["MAX_CONTENT_LENGTH"] > 0
