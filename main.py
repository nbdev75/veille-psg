"""Point d'entrée : collecte -> analyse IA -> stockage -> page web.

Lancer : python3 main.py
Puis ouvrir docs/index.html dans le navigateur.
"""
from collections import Counter

import storage
from ai import analyze
from collector import collect_all
from build_page import build


def main() -> None:
    print("🔎 Collecte en cours...")
    fresh = collect_all()

    articles, added = storage.merge(storage.load(), fresh)
    articles = storage.prune(articles)
    print(f"   {len(fresh)} articles récupérés, {added} nouveaux, {len(articles)} au total (7 jours).")

    print("🤖 Analyse IA...")
    stories = analyze(articles)          # regroupe, résume, note, angle TikTok
    storage.save(articles)

    counts = Counter(s["category"] for s in stories)
    print(f"   {len(stories)} infos : " + " · ".join(f"{c} {n}" for c, n in counts.most_common()))

    path = build(articles, stories)
    print(f"✅ Page mise à jour : {path}")


if __name__ == "__main__":
    main()