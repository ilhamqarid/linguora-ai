# Service IA — LocalHelp AI (Guidly)

Microservice Python/FastAPI qui réalise les Étapes A (Intent Detection) et
B (Entity Extraction) du pipeline IA décrit en section 13 du prompt maître.

## Installation

```bash
cd ai-service
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

## Lancement

```bash
uvicorn main:app --reload --port 8000
```

Le service tourne sur `http://localhost:8000`. Documentation interactive
auto-générée disponible sur `http://localhost:8000/docs` (Swagger UI) —
pratique pour tester `/analyze` directement sans passer par le frontend.

## Tester manuellement

```bash
curl -X POST http://localhost:8000/analyze -H "Content-Type: application/json" -d "{\"text\": \"bghit passport\"}"
```

## Lancer le dataset de test (accuracy)

```bash
python test_intents.py
```

## Important

Ce service ne touche JAMAIS à MySQL. Il comprend le texte, c'est tout.
C'est le backend Spring Boot (`AiController` → `AiService`) qui va
chercher la vraie procédure en base à partir de l'`intent_code` renvoyé
ici — jamais l'inverse (section 14 du prompt maître).

Pour ajouter une nouvelle procédure au NLU : ajoute son `intent_code` et
ses mots-clés (FR/AR/Darija) dans `intents.py`. Sans ça, l'IA ne pourra
jamais la détecter, même si elle existe en base.
