"""Configuration de la veille PSG : sources, niveaux de fiabilité, catégories."""
from urllib.parse import quote_plus

# --- Recherche Google News (flux RSS gratuit, sans clé API) -----------------
# "when:1d" = uniquement les articles des dernières 24 h (évite les vieilles infos)
GOOGLE_NEWS_QUERIES = [
    "PSG",
    '"Paris Saint-Germain"',
    "PSG mercato",
    "PSG blessure OR infirmerie OR forfait",
    "PSG composition OR compo",
    "Luis Enrique PSG",
    "Al-Khelaïfi OR \"Luis Campos\" PSG",
    "PSG \"Parc des Princes\" OR stade OR LFP",
    "PSG site:psg.fr",
    "PSG site:lequipe.fr",
    "PSG site:leparisien.fr",
    "PSG site:rmcsport.bfmtv.com",
    "PSG site:footmercato.net",
]


def google_news_url(query: str) -> str:
    q = quote_plus(f"{query} when:1d")
    return f"https://news.google.com/rss/search?q={q}&hl=fr&gl=FR&ceid=FR:fr"


FEEDS = [google_news_url(q) for q in GOOGLE_NEWS_QUERIES]

# --- Niveaux de fiabilité par domaine ---------------------------------------
# 0 = officiel, 1 = très fiable, 2 = fiable à recouper, 3 = rumeur (défaut)
SOURCE_TIERS = {
    "psg.fr": 0,
    "ligue1.com": 0,
    "lfp.fr": 0,
    "uefa.com": 0,
    "lequipe.fr": 1,
    "leparisien.fr": 1,
    "rmcsport.bfmtv.com": 1,
    "bfmtv.com": 1,
    "francetvinfo.fr": 1,
    "lemonde.fr": 1,
    "footmercato.net": 2,
    "culturepsg.com": 2,
    "skysports.com": 2,
    "marca.com": 2,
    "as.com": 2,
    "goal.com": 2,
    "eurosport.fr": 2,
    "sofoot.com": 2,
    "20minutes.fr": 2,
    "ouest-france.fr": 2,
    "lefigaro.fr": 1,
    "francebleu.fr": 2,
    "ici.fr": 2,
}
DEFAULT_TIER = 3

# Sites ignorés complètement (spam, faux articles générés, paris sportifs...)
BLOCKED_DOMAINS = [
    "horticulture-abadie-pyrenees.com",
    "betmines.com",
    "billetterie.psg.fr",   # billets
    "store.psg.fr",         # boutique
    "shop.psg.fr",
]

TIER_LABELS = {0: "Officiel", 1: "Très fiable", 2: "À recouper", 3: "Rumeur"}

# --- Filtre de pertinence ---------------------------------------------------
# Un article est gardé SEULEMENT si son titre contient au moins un de ces mots.
# 👉 Complète la liste avec tout l'effectif et le staff du PSG.
RELEVANCE_KEYWORDS = [
    "psg", "paris saint-germain", "paris saint germain", "paris sg", "paris-sg", "parisien",
    "luis enrique", "luis campos", "al-khelaïfi", "khelaifi", "parc des princes",
    "camp des loges", "titis",
    # Joueurs (à compléter / mettre à jour à chaque mercato)
    "dembélé", "marquinhos", "doué", "hakimi", "nuno mendes", "vitinha",
    "joão neves", "joao neves", "kvaratskhelia", "kvara", "mayulu", "pacho",
    "zaïre-emery", "zaire-emery", "chevalier", "ferran torres", "fabian ruiz",
    "barcola", "safonov", "beraldo", "lee kang-in", "gonçalo ramos",
]

# Un article est rejeté si son titre contient un de ces mots.
EXCLUDE_KEYWORDS = [
    "pronostic", "cotes", "meilleurs paris", "handball", "basket",
    "le parisien week-end", "idées de sorties",
    # boutique / billetterie du club
    "billet à l'unité", "tout public", "maillot", "t-shirt", "short d'entraînement",
    "flocage", "sweat", "online store",
]

# --- Catégories (pré-classement gratuit par mots-clés) ----------------------
# L'ordre compte : la première catégorie qui matche gagne.
CATEGORIES = {
    "Infirmerie": [
        "bless", "infirmerie", "forfait", "suspendu", "suspension", "lésion",
        "entorse", "ligament", "rechute", "retour", "retours", "touché à",
        "incertain", "opéré", "opération", "apte", "aptes", "absent",
        "reprend l'entraînement", "reprise", "nouvelles de", "rétabli",
    ],
    "Mercato": [
        "mercato", "transfert", "prolong", "prêt", "recrue", "recrut", "signe ",
        "signature", "offre", "piste", "cible", "viseur", "intérêt", "départ",
        "arrivée", "officialise", "visite médicale", "contrat", "clause",
        "millions d'euros", "m€", "blind", "verrouill", "avenir", "priorité de",
        "coup à ne pas manquer", "agent",
    ],
    "Déclarations": [
        "conférence", "conf de presse", "déclar", "confie", "confidences",
        "explique", "estime", "affirme", "réagit", "réaction", "«", '"', "“",
        "interview", "exclu", "raconte", "lance", "prévient", "évoque",
        "rassure", "félicite", "hommage", "éloges", "a tranché", "se méfie",
        "s'attaque", "optimiste", "parle", "annonce pour", "révèle",
    ],
    "Matchs": [
        "compo", "composition", "titulaire", "groupe", "convoqu", "score",
        "victoire", "défaite", "nul", "résumé", "notes", "but", "buts",
        "calendrier", "à quelle heure", "sur quelle chaîne", "diffusion",
        "ligue des champions", "ligue 1", "coupe de france", " vs ", "face à",
        "contre", "équipe annoncée", "équipe parisienne annoncée", "arbitre",
        "guichets fermés", "déplacement", "match", "affiche", "leader",
        "entraînement", "réception", "scalp", "coup dur",
    ],
    "Institutionnel": [
        "stade", "parc des princes", "finance", "budget", "qsi", "qatar",
        "al-khelaïfi", "khelaifi", "mairie", "ville de paris", "hidalgo", "lfp",
        "droits tv", "dncg", "actionnaire", "chiffre d'affaires", "sponsor",
        "supporters", "ministère", "préfecture", "interdits", "salaire", "gagné",
    ],
}
DEFAULT_CATEGORY = "Autre"

# On ignore tout ce qui a plus de X heures (sécurité anti-vieilles infos)
MAX_AGE_HOURS = 36

DATA_PATH = "data/articles.json"   # base de données (simple fichier JSON)
PAGE_PATH = "docs/index.html"      # page web générée
KEEP_DAYS = 7                      # on garde 7 jours d'historique sur la page

# --- IA (Claude Haiku) ------------------------------------------------------
STORIES_PATH = "data/stories.json" # infos regroupées et résumées par l'IA
AI_MODEL = "claude-haiku-5-5"
AI_BATCH_SIZE = 60                 # titres envoyés par appel
AI_MAX_BATCHES = 5                 # max d'appels par passage (sécurité coût)
AI_CONTEXT_HOURS = 48              # infos récentes données à l'IA pour rattacher les suites