"""Collecte des articles PSG depuis les flux RSS + pré-classement."""
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import feedparser
import requests

from config import (FEEDS, SOURCE_TIERS, DEFAULT_TIER, CATEGORIES,
                    DEFAULT_CATEGORY, MAX_AGE_HOURS, BLOCKED_DOMAINS,
                    RELEVANCE_KEYWORDS, EXCLUDE_KEYWORDS)

HEADERS = {"User-Agent": "Mozilla/5.0 (veille-psg)"}


# --- Outils -----------------------------------------------------------------
def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")


def dedup_key(title: str) -> str:
    t = strip_accents(title.lower())
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return re.sub(r"\s+", " ", t).strip()[:90]


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def tier_of(domain: str) -> int:
    # correspondance la plus longue d'abord (rmcsport.bfmtv.com avant bfmtv.com)
    for known in sorted(SOURCE_TIERS, key=len, reverse=True):
        if domain == known or domain.endswith("." + known):
            return SOURCE_TIERS[known]
    return DEFAULT_TIER


def contains_any(title: str, keywords: list[str]) -> bool:
    text = " " + title.lower() + " "
    # début de mot obligatoire : "but" ne matche pas "début"
    return any(re.search(r"(?<!\w)" + re.escape(kw.lower()), text) for kw in keywords)


def is_relevant(title: str, domain: str) -> bool:
    if any(domain == d or domain.endswith("." + d) for d in BLOCKED_DOMAINS):
        return False
    if contains_any(title, EXCLUDE_KEYWORDS):
        return False
    return contains_any(title, RELEVANCE_KEYWORDS)


def categorize(title: str) -> str:
    for category, keywords in CATEGORIES.items():
        if contains_any(title, keywords):
            return category
    return DEFAULT_CATEGORY


# --- Collecte -----------------------------------------------------------------
def parse_entry(entry) -> dict | None:
    title = entry.get("title", "").strip()
    link = entry.get("link", "")
    if not title or not link:
        return None

    # Google News : la vraie source est dans entry.source
    source = entry.get("source") or {}
    source_name = source.get("title", "") if hasattr(source, "get") else ""
    source_url = source.get("href", "") if hasattr(source, "get") else ""
    domain = domain_of(source_url or link)

    # Google News ajoute " - Nom du média" à la fin du titre
    if source_name and title.endswith(" - " + source_name):
        title = title[: -len(" - " + source_name)].strip()

    if not is_relevant(title, domain):
        return None  # hors sujet (pas PSG), exclu ou site bloqué

    published = entry.get("published_parsed") or entry.get("updated_parsed")
    if not published:
        return None  # pas de date = on ne peut pas vérifier la fraîcheur
    published_dt = datetime(*published[:6], tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - published_dt > timedelta(hours=MAX_AGE_HOURS):
        return None  # trop vieux

    return {
        "dedup_key": dedup_key(title),
        "title": title,
        "url": link,
        "source_name": source_name or domain,
        "source_domain": domain,
        "tier": tier_of(domain),
        "category": categorize(title),
        "published_at": published_dt.isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def fetch_feed(url: str) -> list[dict]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  ⚠️  Flux inaccessible : {e}")
        return []
    feed = feedparser.parse(resp.content)
    return [a for a in (parse_entry(e) for e in feed.entries) if a]


def collect_all() -> list[dict]:
    articles = []
    for url in FEEDS:
        articles.extend(fetch_feed(url))
    return articles
