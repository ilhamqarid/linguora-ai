# Linguora

**Écrire. Traduire. Comprendre. Communiquer.**

Linguora est un assistant linguistique web pour le français et le darija/amazigh marocains : correction orthographique et grammaticale, traduction, reformulation, OCR et dictée vocale — le tout avec une IA en renfort (Groq) qui se replie automatiquement sur des méthodes par règles si elle est indisponible.

## Fonctionnalités

- **Correction** — orthographe et grammaire via [LanguageTool](https://languagetool.org/), avec sélection interactive des corrections à appliquer. L'IA (Groq) est utilisée en priorité quand disponible pour une correction plus contextuelle (comprend le sens, pas seulement la distance d'édition).
- **Traduction** — vers plusieurs langues (anglais, espagnol, arabe, darija, amazigh...). L'IA traduit en priorité ; repli sur [deep-translator](https://github.com/nidhaloff/deep-translator) (Google Translate) ou sur un dictionnaire rule-based pour le darija/amazigh si l'IA est indisponible.
- **Darija & Amazigh** — détection automatique de la langue d'entrée (écriture arabe, tifinagh ou latine). Pivot vers le français via IA (comprend les trois écritures) avec repli sur un dictionnaire rule-based (transcription latine uniquement). Pour l'amazigh, la traduction passe par un alphabet latin berbère intermédiaire puis une translittération déterministe vers le Tifinagh, afin de toujours produire des caractères valides.
- **Reformulation** — plusieurs tons (neutre, professionnel, amical), par IA en priorité, repli par règles.
- **OCR** — import d'image, extraction de texte via [Tesseract](https://github.com/tesseract-ocr/tesseract).
- **Dictée vocale** — via l'API Web Speech du navigateur.

Dans tous les cas où l'IA est indisponible (clé absente, quota dépassé, erreur réseau), l'application ne plante jamais : elle bascule silencieusement sur son pipeline par règles.

## Stack technique

| Composant | Techno |
|---|---|
| Backend | Flask (Python), pattern application factory |
| Correction grammaticale | LanguageTool (moteur externe) |
| IA (optionnelle) | [Groq](https://console.groq.com) — `openai/gpt-oss-120b` |
| Traduction de repli | deep-translator (Google Translate) |
| OCR | Tesseract via pytesseract |
| Voix | Web Speech API (navigateur) |
| Rate limiting | Flask-Limiter |
| Tests | pytest |
| Frontend | HTML / CSS / JS vanilla |

## Installation

```bash
git clone <url-de-ce-repo>
cd linguora-ai
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Copie `.env.example` vers `.env` et renseigne au minimum ta clé Groq (gratuite, sans carte bancaire, sur [console.groq.com](https://console.groq.com/keys)) :

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # macOS / Linux
```

```
GROQ_API_KEY=ta_cle_ici
GROQ_MODEL=openai/gpt-oss-120b
```

**L'IA est optionnelle** : si `GROQ_API_KEY` est vide, l'application fonctionne quand même intégralement, avec un repli automatique sur les méthodes par règles.

Lance l'application :

```bash
python run.py
```

Puis ouvre [http://127.0.0.1:5000](http://127.0.0.1:5000).

## Tests automatisés

```bash
pytest
```

54 tests couvrent chaque route (`/correct`, `/translate`, `/rephrase`, `/detect-language`, `/ocr`, `/api/ai/*`) :
- comportement sur texte vide / manquant / mal formé (jamais de crash)
- repli propre quand un service externe (LanguageTool, Groq) est indisponible
- validation de sécurité (longueur de texte, extensions de fichiers, rate limiting, non-fuite d'erreurs internes)

Aucun test ne dépend d'un vrai serveur LanguageTool ni d'une vraie clé Groq : tous les appels externes sont mockés (`unittest.mock` / `monkeypatch`), pour un résultat reproductible sur n'importe quelle machine, sans configuration préalable.

## Sécurité

Mesures en place :

- **Rate limiting** (Flask-Limiter) : limites par défaut 60 requêtes/minute, réduites à 20/minute pour les routes IA (Groq) et 10/minute pour l'OCR, afin de protéger le quota Groq et le CPU contre un usage abusif (spam de boutons, script automatisé). Configurable via `.env` (`RATELIMIT_*`).
- **Gestion d'erreurs centralisée** : toute exception (prévue ou non) renvoie un message JSON générique au client ; le détail complet (message, stack trace) part uniquement dans les logs serveur, jamais dans la réponse HTTP.
- **Validation de taille des entrées** : texte limité à `MAX_TEXT_LENGTH` (5000 caractères par défaut), appliquée avant tout appel à LanguageTool/Groq. Upload d'image limité par `MAX_UPLOAD_MB` (5 Mo par défaut) et restreint à une liste blanche d'extensions.
- **Upload de fichiers sécurisé** : nom de fichier assaini (`secure_filename`) + préfixe unique (`uuid`), suppression garantie du fichier temporaire même en cas d'erreur.
- **Secrets** : clé API et clé secrète Flask exclusivement via variables d'environnement (`.env`, jamais commité — voir `.gitignore`), jamais codées en dur.
- **Mode debug désactivé par défaut** : le débogueur Werkzeug (`FLASK_DEBUG=true`) permettrait l'exécution de code arbitraire depuis le navigateur en cas d'erreur non gérée — il n'est jamais activé sans un choix explicite en développement local.

Limites connues (pas d'audit de sécurité formel/tiers) :
- Le stockage du rate limiting (`memory://` par défaut) n'est pas partagé entre plusieurs workers/process — suffisant pour un usage mono-process, insuffisant pour un vrai déploiement multi-workers (prévoir Redis via `RATELIMIT_STORAGE_URI`).
- Pas de protection CSRF explicite (l'app n'utilise pas de sessions/cookies d'authentification à ce stade, donc le risque est limité, mais à revoir si une authentification est ajoutée).
- Pas de scan de vulnérabilités de dépendances automatisé (`pip-audit` ou équivalent) intégré au projet.

## Structure du projet

```
linguora-ai/
├── app/
│   ├── ai/                  # Intégration Groq (correction, traduction, reformulation contextuelles)
│   ├── data/                # Dictionnaires FR <-> Darija/Amazigh
│   ├── routes/               # Endpoints Flask (/correct, /translate, /rephrase, /ocr, /detect-language...)
│   ├── services/              # Logique métier (grammaire, traduction, détection de langue, OCR...)
│   ├── utils/                 # Fonctions utilitaires (texte, validation)
│   └── config.py
├── static/                  # CSS / JS
├── templates/                # HTML (Jinja2)
├── tests/                    # Suite pytest
├── .env.example
├── requirements.txt
└── run.py
```

## Limitations connues

Par souci d'honnêteté produit, quelques limites assumées à ce stade :

- **Traduction amazigh** : l'IA connaît bien la grammaire générale du tamazight mais son vocabulaire n'est pas toujours fiable (langue peu représentée dans les données d'entraînement des modèles actuels). Le résultat doit être considéré comme une aide, pas une traduction certifiée.
- **Pas de contexte de traduction** (registre général / professionnel / académique / familier) — prévu, pas encore implémenté.
- **Pas d'indicateur de qualité du texte** (score visuel) — prévu, pas encore implémenté.
- **Pas d'historique des opérations** — prévu, pas encore implémenté.
- **OCR et dictée vocale** remplissent le champ texte mais ne sont pas encore intégrés à un flux plus élaboré (relecture automatique, corrections suggérées à la volée, etc.).

## Licence

Projet personnel / académique.
