"""
Base de connaissance des intentions.

Principe fondamental du projet (section 4 du prompt maître) : l'IA ne doit
JAMAIS inventer une procédure. Cette liste doit rester synchronisée avec les
`intent_code` réellement présents dans la table `procedures` du backend.
Si tu ajoutes une nouvelle procédure en base, ajoute son intent_code ici
avec ses mots-clés, sinon elle ne sera jamais détectée par le NLU.

Structure : chaque intention a une liste de mots-clés/expressions en
français, arabe (darija latinisé compris) qui, lorsqu'ils apparaissent dans
la phrase de l'utilisateur, augmentent le score de cette intention.
"""

INTENTS = {
    "passport_application": {
        "label": "Demande de passeport",
        "keywords": [
            # Français
            "passeport", "passport", "refaire mon passeport", "nouveau passeport",
            # Arabe (écriture arabe)
            "جواز السفر", "جواز سفر", "باسبور",
            # Darija latinisée
            "passport", "bghit passport", "sanaa passport", "jawaz safar",
        ],
    },
    "cnie_first_application": {
        "label": "Carte Nationale d'Identité Électronique",
        "keywords": [
            "carte d'identité", "carte nationale", "cnie", "carte didentite",
            "بطاقة التعريف الوطنية", "البطاقة الوطنية",
            "carte nationale dl identite", "bitaqa",
        ],
    },
    "business_creation_sarl_au": {
        "label": "Création d'entreprise",
        "keywords": [
            "créer une entreprise", "créer mon entreprise", "création d'entreprise",
            "société", "sarl", "auto-entrepreneur", "monter une société",
            "شركة", "تأسيس شركة", "مقاولتي",
            "dir chariqa", "nhawel chi charika", "mochrou3",
        ],
    },
    "university_registration": {
        "label": "Inscription universitaire",
        "keywords": [
            "université", "inscription université", "m'inscrire à l'université",
            "faculté", "bac", "baccalauréat", "étudiant",
            "الجامعة", "التسجيل بالجامعة", "طالب جديد",
            "nsjel", "nsjel fl jami3a", "talib jdid", "sjel fljami3a",
        ],
    },
    "vehicle_registration": {
        "label": "Carte grise",
        "keywords": [
            "carte grise", "immatriculer", "immatriculation", "nouveau véhicule",
            "acheter une voiture", "voiture",
            "البطاقة الرمادية", "تسجيل السيارة",
            "carte grisa", "tsjil dyal tomobil", "chrit tomobil",
        ],
    },
    "birth_certificate_request": {
        "label": "Acte de naissance",
        "keywords": [
            "acte de naissance", "extrait de naissance", "copie d'acte de naissance",
            "شهادة الازدياد", "عقد الازدياد",
            "chahada dyal lwilada", "acte naissance", "wilada",
        ],
    },
    "criminal_record_request": {
        "label": "Casier judiciaire",
        "keywords": [
            "casier judiciaire", "extrait de casier", "bulletin n3", "bulletin numero 3",
            "السجل العدلي",
            "sijil el 3adli", "sijil adli",
        ],
    },
    "driving_license_application": {
        "label": "Permis de conduire",
        "keywords": [
            "permis de conduire", "passer le permis", "permis conduire",
            "رخصة السياقة",
            "njib permis", "permis dyal souk",
        ],
    },
    "anapec_registration": {
        "label": "Inscription ANAPEC",
        "keywords": [
            "anapec", "inscription anapec", "chercheur d'emploi", "recherche d'emploi",
            "trouver un emploi", "trouver du travail",
            "الأنابيك", "الوكالة الوطنية لإنعاش الشغل",
            "bghit nkhdem", "n9elleb 3la khedma",
        ],
    },
    "cnss_first_affiliation": {
        "label": "Affiliation CNSS",
        "keywords": [
            "cnss", "affiliation cnss", "sécurité sociale", "securite sociale",
            "الضمان الاجتماعي",
            "immatriculation cnss", "ndir cnss",
        ],
    },
}

# Seuils de confiance (section 28 du prompt maître)
THRESHOLD_DIRECT = 0.85       # confiance >= 0.85 -> proposer directement
THRESHOLD_SUGGEST = 0.60      # 0.60 <= confiance < 0.85 -> proposer 2-3 options
# en dessous de 0.60 -> demander une clarification / hors périmètre
