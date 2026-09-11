import os
import uuid

from flask import current_app
from PIL import Image
from werkzeug.utils import secure_filename
import pytesseract


def _is_allowed(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["UPLOAD_ALLOWED_EXTENSIONS"]


def extract_text_from_image(file_storage) -> str:
    """
    Sauvegarde temporairement l'image uploadée, extrait le texte via
    Tesseract, puis supprime le fichier temporaire.

    Améliorations vs. version originale :
    - extension vérifiée (whitelist)
    - nom de fichier assaini (secure_filename) + préfixe unique (uuid)
      pour éviter les collisions entre requêtes concurrentes
    - le fichier temporaire est toujours supprimé, même en cas d'erreur
    """
    if not file_storage or not file_storage.filename:
        raise ValueError("Aucune image fournie.")

    if not _is_allowed(file_storage.filename):
        raise ValueError("Format d'image non supporté.")

    upload_dir = current_app.config["UPLOAD_TMP_DIR"]
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(file_storage.filename)
    tmp_name = f"{uuid.uuid4().hex}_{safe_name}"
    tmp_path = os.path.join(upload_dir, tmp_name)

    file_storage.save(tmp_path)

    try:
        text = pytesseract.image_to_string(
            Image.open(tmp_path),
            lang="fra+eng",
            config="--oem 3 --psm 6",
        )
    except Exception as e:
        current_app.logger.error("OCR error: %s", e)
        text = ""
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return text
