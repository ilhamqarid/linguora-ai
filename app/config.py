import os


class Config:
    """
    Configuration centralisée de Linguora AI.
    Toutes les valeurs sensibles ou dépendantes de la machine viennent
    de variables d'environnement (voir .env.example) au lieu d'être
    codées en dur dans le code source.
    """

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # URL du serveur LanguageTool local (ou distant).
    LANGUAGETOOL_URL = os.environ.get(
        "LANGUAGETOOL_URL", "http://localhost:8081/v2/check"
    )

    # Chemin vers l'exécutable Tesseract.
    # Sur Windows par ex. : C:\Program Files\Tesseract-OCR\tesseract.exe
    # Laisser vide sur Linux/Mac si tesseract est déjà dans le PATH.
    TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "")

    # Upload OCR : taille max (Mo) et extensions autorisées.
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    UPLOAD_ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}

    # Dossier temporaire pour les images uploadées avant OCR.
    UPLOAD_TMP_DIR = os.environ.get("UPLOAD_TMP_DIR", "uploads_tmp")

    # Couche IA (optionnelle) : Groq.
    # Si GROQ_API_KEY est vide, les fonctionnalités IA se replient
    # automatiquement sur un comportement rule-based existant -- jamais
    # de plantage, jamais de dépendance obligatoire à un service payant.
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    # --- Sécurité ---

    # Longueur max acceptée pour un texte envoyé aux routes de
    # correction/traduction/reformulation. Protège contre l'abus (texte
    # énorme envoyé volontairement) et les appels IA/LanguageTool
    # inutilement coûteux -- sans ça, rien n'empêche d'envoyer un texte
    # de plusieurs Mo à chaque clic.
    MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "5000"))

    # Rate limiting : protège le quota Groq (gratuit mais limité) et le
    # CPU consommé par l'OCR/LanguageTool contre un usage abusif (spam de
    # boutons, script qui boucle sur l'API...). Désactivable via
    # RATELIMIT_ENABLED=false (utile en tests automatisés), à garder
    # activé en production.
    #
    # Limite : le stockage par défaut ("memory://") vit en mémoire du
    # process Flask -- il repart à zéro à chaque redémarrage et n'est
    # PAS partagé entre plusieurs workers/process (ex: gunicorn -w 4).
    # Suffisant pour un usage mono-process (dev, petit projet) ; pour une
    # vraie mise en production multi-workers, configurer
    # RATELIMIT_STORAGE_URI vers un Redis partagé.
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() != "false"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = os.environ.get("RATELIMIT_DEFAULT", "60 per minute")
    # Limite plus stricte pour les routes coûteuses (appels Groq, OCR).
    RATELIMIT_AI = os.environ.get("RATELIMIT_AI", "20 per minute")
    RATELIMIT_OCR = os.environ.get("RATELIMIT_OCR", "10 per minute")


class TestConfig(Config):
    """
    Configuration utilisée par la suite de tests (voir tests/conftest.py).

    - TESTING=True : Flask laisse ses handlers d'erreur gérer les
      exceptions au lieu de les repropager (comportement identique à la
      production, contrairement au mode debug qui affiche la stack
      trace au client).
    - Rate limiting désactivé par défaut : les tests fonctionnels
      envoient volontairement de nombreuses requêtes, un test dédié
      (test_security.py) le réactive spécifiquement avec une limite
      basse pour vérifier qu'il fonctionne.
    - GROQ_API_KEY vide par défaut : les tests ne doivent jamais taper
      sur le vrai réseau/quota Groq ; les tests qui veulent simuler
      "IA disponible" mockent directement les fonctions de llm_service.
    """

    TESTING = True
    # Flask force PROPAGATE_EXCEPTIONS=True par défaut quand TESTING=True,
    # ce qui court-circuiterait nos gestionnaires d'erreur (l'exception
    # remonterait brute au client de test). On le désactive explicitement
    # pour que les tests vérifient le VRAI comportement de production
    # (réponse JSON générique, jamais de stack trace).
    PROPAGATE_EXCEPTIONS = False
    RATELIMIT_ENABLED = False
    GROQ_API_KEY = ""
    UPLOAD_TMP_DIR = "uploads_tmp_test"
