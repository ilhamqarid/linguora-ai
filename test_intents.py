"""
Petit dataset de test pour le NLU + mesure d'accuracy (sections 32-33).

Lancement : python3 test_intents.py
"""

from matcher import analyze

# (texte, intent_code attendu ou None si hors périmètre)
TEST_CASES = [
    ("bghit passport", "passport_application"),
    ("je veux refaire mon passeport", "passport_application"),
    ("أريد جواز السفر", "passport_application"),
    ("je voudrais faire mon premier passeport", "passport_application"),

    ("bghit njadad la carte grise", "vehicle_registration"),
    ("comment immatriculer ma nouvelle voiture", "vehicle_registration"),

    ("je veux créer mon entreprise", "business_creation_sarl_au"),
    ("bghit ndir chi charika", "business_creation_sarl_au"),

    ("je viens d'avoir mon bac, comment m'inscrire à la fac", "university_registration"),
    ("talib jdid bghit nsjel fl jami3a", "university_registration"),

    ("je veux ma carte d'identité", "cnie_first_application"),
    ("بطاقة التعريف الوطنية", "cnie_first_application"),

    ("je veux regarder un film", None),       # hors périmètre (section 32)
    ("quel temps fait-il aujourd'hui", None),  # hors périmètre
]


def run():
    correct = 0
    for text, expected in TEST_CASES:
        result = analyze(text)
        detected = result["intent"] if result["action"] != "clarify" or result["confidence"] >= 0.6 else None
        # En dessous du seuil "suggest", on considère que le système a
        # correctement reconnu qu'il ne savait pas (comportement voulu
        # pour les cas hors périmètre).
        is_correct = (detected == expected) or (expected is None and result["action"] == "clarify")
        correct += int(is_correct)
        status = "OK" if is_correct else "FAIL"
        print(f"[{status}] {text!r:55} attendu={expected!r:28} obtenu={result['intent']!r:28} conf={result['confidence']:.2f}")

    accuracy = correct / len(TEST_CASES)
    print(f"\nAccuracy: {correct}/{len(TEST_CASES)} = {accuracy:.0%}")


if __name__ == "__main__":
    run()
