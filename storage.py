"""Stockage des articles dans un simple fichier JSON (lisible et versionnable)."""
import json
import os
from datetime import datetime, timezone, timedelta

from config import DATA_PATH, KEEP_DAYS


def load() -> list[dict]:
    if not os.path.exists(DATA_PATH):
        return []
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def merge(existing: list[dict], new: list[dict]) -> tuple[list[dict], int]:
    """Ajoute les nouveaux articles (anti-doublons). Retourne (liste, nb_ajoutés)."""
    seen = {a["dedup_key"] for a in existing}
    added = 0
    for art in new:
        if art["dedup_key"] in seen:
            continue
        art["first_seen"] = art["fetched_at"]
        existing.append(art)
        seen.add(art["dedup_key"])
        added += 1
    return existing, added


def prune(articles: list[dict]) -> list[dict]:
    """Supprime les articles plus vieux que KEEP_DAYS."""
    limit = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    return [a for a in articles if a["published_at"] >= limit]


def save(articles: list[dict]) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    articles.sort(key=lambda a: a["published_at"], reverse=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=1)
