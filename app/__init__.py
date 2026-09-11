import os

import pytesseract
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from .config import Config

# Instance unique du limiteur, partagée par toute l'app. Créée sans
# `app` ici (pattern factory) puis rattachée via limiter.init_app(app)
# dans create_app -- permet aux modules de routes de faire
# `from app import limiter` sans import circulaire.
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class: type = Config) -> Flask:
    """
    Application factory. Permet de créer l'app une seule fois (run.py)
    ou plusieurs fois (tests), avec une config différente si besoin.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, "templates"),
        static_folder=os.path.join(project_root, "static"),
    )
    app.config.from_object(config_class)

    # Tesseract : on ne fixe le chemin que s'il est explicitement fourni.
    # Sinon on suppose qu'il est déjà accessible dans le PATH du système.
    if app.config.get("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = app.config["TESSERACT_CMD"]

    limiter.init_app(app)
    app.config.setdefault("RATELIMIT_STORAGE_URI", "memory://")
    app.config["RATELIMIT_ENABLED"] = app.config.get("RATELIMIT_ENABLED", True)
    if app.config["RATELIMIT_ENABLED"]:
        limiter.default_limits = [app.config.get("RATELIMIT_DEFAULT", "60 per minute")]

    _register_error_handlers(app)
    _register_blueprints(app)

    return app


def _register_error_handlers(app: Flask) -> None:
    """
    Gestion d'erreurs centralisée : le client ne voit JAMAIS de stack
    trace, de chemin de fichier ou de détail d'implémentation -- même en
    cas de bug non prévu. Le détail complet part dans les logs serveur
    (app.logger), consultables par le développeur, jamais renvoyés dans
    la réponse HTTP.
    """

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Requête invalide."}), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Ressource introuvable."}), 404

    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"error": "Fichier ou texte trop volumineux."}), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            "error": "Trop de requêtes. Merci de patienter avant de réessayer."
        }), 429

    @app.errorhandler(500)
    def internal_error(e):
        app.logger.exception("Erreur interne non gérée")
        return jsonify({"error": "Une erreur interne est survenue."}), 500

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        # Filet de sécurité final : toute exception Python non prévue
        # (bug, dépendance externe qui plante différemment que prévu...)
        # est journalisée en détail côté serveur, mais le client ne
        # reçoit qu'un message générique -- jamais le message
        # d'exception brut, qui pourrait révéler des détails
        # d'implémentation (chemins de fichiers, noms de variables,
        # requêtes SQL, clés partiellement visibles dans un traceback...).
        app.logger.exception("Exception non gérée: %s", e)
        return jsonify({"error": "Une erreur interne est survenue."}), 500


def _register_blueprints(app: Flask) -> None:
    from .routes.pages import pages_bp
    from .routes.correction import correction_bp
    from .routes.translation import translation_bp
    from .routes.rewrite import rewrite_bp
    from .routes.ocr import ocr_bp
    from .routes.detect import detect_bp
    from .routes.ai import ai_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(correction_bp)
    app.register_blueprint(translation_bp)
    app.register_blueprint(rewrite_bp)
    app.register_blueprint(ocr_bp)
    app.register_blueprint(detect_bp)
    app.register_blueprint(ai_bp)
