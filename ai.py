"""Analyse IA avec Claude Haiku : regroupe les articles par info, résume,
note la fiabilité, donne le statut mercato et un angle TikTok.

Nécessite la variable d'environnement ANTHROPIC_API_KEY.
Sans clé, l'étape est simplement sautée (la page affiche les articles bruts).
"""
import json
import os
from datetime import datetime, timezone, timedelta

from config import (AI_MODEL, AI_BATCH_SIZE, AI_MAX_BATCHES, AI_CONTEXT_HOURS,
                    STORIES_PATH, KEEP_DAYS, TIER_LABELS)

CATEGORY_NAMES = ["Mercato", "Infirmerie", "Matchs", "Déclarations", "Institutionnel", "Autre"]
MERCATO_STATUS = ["", "Rumeur", "Intérêt", "Contacts", "Offre", "Accord",
                  "Visite médicale", "Officiel", "Démenti", "Échec"]

SYSTEM_PROMPT = """Tu es l'agent de veille d'une chaîne TikTok consacrée au Paris Saint-Germain.
On te donne (1) les infos déjà connues des dernières heures et (2) une liste de NOUVEAUX titres d'articles.

Ta mission :
- Regrouper les nouveaux titres qui parlent du MÊME sujet en une seule info. Si un titre complète une info déjà connue, rattache-le à son id existant (et mets à jour son résumé si le titre apporte du nouveau).
- Écrire pour chaque info créée ou mise à jour : un titre court et clair, un résumé de 2 à 3 phrases en français, une catégorie, une note de fiabilité, un statut mercato si c'est du mercato, un angle TikTok.
- Ignorer (liste "ignored") les titres hors sujet : pas liés au PSG, publicités, billetterie, boutique, paris sportifs.

RÈGLES DE VÉRACITÉ (très important) :
- N'utilise QUE les informations présentes dans les titres fournis. N'invente aucun chiffre, nom, date ou citation.
- Si les sources se contredisent, dis-le dans le résumé.
- Attribue les infos non officielles : "selon L'Équipe…", "d'après Foot Mercato…".
- Sépare le fait confirmé de l'interprétation (ex. blessure confirmée par le club vs durée d'absence estimée par la presse).

NOTE DE FIABILITÉ (1 à 5) :
- 5 : confirmé par une source officielle (club, LFP, UEFA) ou fait public incontestable (score d'un match joué, déclaration en conférence de presse reprise partout).
- 4 : au moins une source "Très fiable" + plusieurs sources indépendantes concordantes.
- 3 : une source "Très fiable" seule, ou plusieurs sources "À recouper" concordantes.
- 2 : uniquement des sources "À recouper" isolées ou des reprises de rumeurs.
- 1 : uniquement des sources "Rumeur", titres racoleurs, aucune source primaire.
Les reprises d'une même info par des sites "Rumeur" ne comptent pas comme des sources indépendantes.

STATUT MERCATO (seulement pour la catégorie Mercato, sinon "") :
Rumeur → Intérêt → Contacts → Offre → Accord → Visite médicale → Officiel (ou Démenti / Échec).

ANGLE TIKTOK : une accroche percutante d'une phrase + un format (réaction, top 3, chrono, explication, comparaison, débat, avant/après…).
Pour une info notée 1 ou 2, l'accroche ne doit JAMAIS la présenter comme un fait (utilise "rumeur", "selon", "?").

PRIORITÉ : true seulement pour ce qui mérite une vidéo rapide : officialisation, blessure importante, compo officielle, résultat, grosse déclaration, gros dossier mercato fiable (≥3)."""

TOOL = {
    "name": "enregistrer_veille",
    "description": "Enregistre les infos regroupées et analysées.",
    "input_schema": {
        "type": "object",
        "properties": {
            "stories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "id d'une info existante à mettre à jour, ou \"\" pour une nouvelle info"},
                        "article_numbers": {"type": "array", "items": {"type": "integer"},
                                            "description": "numéros des NOUVEAUX titres rattachés à cette info"},
                        "title": {"type": "string"},
                        "category": {"type": "string", "enum": CATEGORY_NAMES},
                        "summary": {"type": "string"},
                        "reliability": {"type": "integer", "minimum": 1, "maximum": 5},
                        "reliability_reason": {"type": "string", "description": "justification courte de la note"},
                        "mercato_status": {"type": "string", "enum": MERCATO_STATUS},
                        "tiktok_hook": {"type": "string"},
                        "tiktok_format": {"type": "string"},
                        "priority": {"type": "boolean"},
                    },
                    "required": ["id", "article_numbers", "title", "category", "summary",
                                 "reliability", "reliability_reason", "mercato_status",
                                 "tiktok_hook", "tiktok_format", "priority"],
                },
            },
            "ignored": {"type": "array", "items": {"type": "integer"}},
        },
        "required": ["stories", "ignored"],
    },
}


# --- Stockage des infos (stories) ------------------------------------------
def load_stories() -> list[dict]:
    if not os.path.exists(STORIES_PATH):
        return []
    with open(STORIES_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_stories(stories: list[dict]) -> None:
    limit = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    stories = [s for s in stories if s["updated_at"] >= limit]
    stories.sort(key=lambda s: s["updated_at"], reverse=True)
    os.makedirs(os.path.dirname(STORIES_PATH), exist_ok=True)
    with open(STORIES_PATH, "w", encoding="utf-8") as f:
        json.dump(stories, f, ensure_ascii=False, indent=1)


# --- Appel à Claude ------------------------------------------------------------
def _paris(iso: str) -> str:
    dt = datetime.fromisoformat(iso) + timedelta(hours=1)  # approx. heure de Paris (hiver)
    return dt.strftime("%d/%m %H:%M")


def _call_claude(client, context: list[dict], batch: list[dict]) -> dict:
    known = [{
        "id": s["id"], "titre": s["title"], "categorie": s["category"],
        "resume": s["summary"], "fiabilite": s["reliability"],
        "statut_mercato": s.get("mercato_status", ""), "nb_articles": len(s["article_keys"]),
    } for s in context]
    new = [{
        "n": i, "titre": a["title"], "source": a["source_name"],
        "niveau_source": TIER_LABELS[a["tier"]], "publie": _paris(a["published_at"]),
    } for i, a in enumerate(batch)]

    user_msg = (
        f"Date et heure actuelles : {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC\n\n"
        f"INFOS DÉJÀ CONNUES :\n{json.dumps(known, ensure_ascii=False)}\n\n"
        f"NOUVEAUX TITRES :\n{json.dumps(new, ensure_ascii=False)}\n\n"
        "Chaque nouveau titre doit apparaître soit dans une info (article_numbers), soit dans ignored."
    )
    resp = client.messages.create(
        model=AI_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "enregistrer_veille"},
        messages=[{"role": "user", "content": user_msg}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            u = resp.usage
            print(f"   🤖 Haiku : {u.input_tokens} tokens lus, {u.output_tokens} écrits")
            return block.input
    raise RuntimeError("Réponse IA sans résultat structuré")


def _apply(result: dict, batch: list[dict], stories: list[dict]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    by_id = {s["id"]: s for s in stories}
    handled = set()

    for item in result.get("stories", []):
        nums = [n for n in item.get("article_numbers", []) if 0 <= n < len(batch)]
        arts = [batch[n] for n in nums]
        story = by_id.get(item.get("id") or "")
        if story is None:
            if not arts:
                continue  # nouvelle info sans article : on ignore
            story = {"id": f"s{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{len(stories)}",
                     "created_at": now, "article_keys": []}
            stories.append(story)
            by_id[story["id"]] = story
        for field in ("title", "category", "summary", "reliability", "reliability_reason",
                      "mercato_status", "tiktok_hook", "tiktok_format", "priority"):
            if field in item:
                story[field] = item[field]
        if story.get("category") != "Mercato":
            story["mercato_status"] = ""
        for a in arts:
            if a["dedup_key"] not in story["article_keys"]:
                story["article_keys"].append(a["dedup_key"])
            a["story_id"] = story["id"]
            handled.add(a["dedup_key"])
        story["updated_at"] = now
        dates = [a["published_at"] for a in arts] + [story.get("last_article_at", "")]
        story["last_article_at"] = max(dates)

    for n in result.get("ignored", []):
        if 0 <= n < len(batch):
            batch[n]["ignored"] = True
            handled.add(batch[n]["dedup_key"])

    # Articles oubliés par l'IA : marqués comme traités pour ne pas boucler
    for a in batch:
        a["ai_done"] = True


def analyze(articles: list[dict]) -> list[dict]:
    """Analyse les articles pas encore traités. Modifie `articles` en place
    (story_id / ignored / ai_done) et retourne la liste des infos à jour."""
    stories = load_stories()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("   ℹ️  Pas de clé ANTHROPIC_API_KEY : analyse IA sautée.")
        return stories

    import anthropic
    client = anthropic.Anthropic()

    pending = sorted([a for a in articles if not a.get("ai_done")], key=lambda a: a["published_at"])
    if not pending:
        print("   🤖 Rien de nouveau à analyser.")
        return stories

    for i in range(0, min(len(pending), AI_BATCH_SIZE * AI_MAX_BATCHES), AI_BATCH_SIZE):
        batch = pending[i:i + AI_BATCH_SIZE]
        limit = (datetime.now(timezone.utc) - timedelta(hours=AI_CONTEXT_HOURS)).isoformat()
        context = [s for s in stories if s["updated_at"] >= limit][:80]
        try:
            result = _call_claude(client, context, batch)
            _apply(result, batch, stories)
        except Exception as e:  # on ne bloque jamais la mise à jour de la page
            print(f"   ⚠️  Erreur IA (lot ignoré, réessayé au prochain passage) : {e}")
            break

    save_stories(stories)
    return stories