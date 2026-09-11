from dotenv import load_dotenv

load_dotenv()  # charge le fichier .env s'il existe

import os  # noqa: E402

from app import create_app  # noqa: E402  (import après load_dotenv volontaire)

app = create_app()

if __name__ == "__main__":
    # IMPORTANT (sécurité) : le débogueur Werkzeug (activé par debug=True)
    # permet l'exécution de code Python arbitraire depuis le navigateur
    # si la page d'erreur est atteinte -- jamais acceptable en dehors du
    # développement local. On lit donc FLASK_DEBUG depuis l'environnement
    # (défaut : désactivé) plutôt que de le coder en dur à True.
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode)
