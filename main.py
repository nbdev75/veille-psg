"""Point d'entrée : collecte -> stockage -> génération de la page web.

Lancer : python3 main.py
Puis ouvrir docs/index.html dans le navigateur.
"""
from collections import Counter

import storage
from collector import collect_all
from build_page import build


def main() -> None:
    print("🔎 Collecte en cours...")
    fresh = collect_all()

    articles, added = storage.merge(storage.load(), fresh)
    articles = storage.prune(articles)
    storage.save(articles)

    counts = Counter(a["category"] for a in articles)
    print(f"   {len(fresh)} articles récupérés, {added} nouveaux, {len(articles)} au total (7 jours).")
    print("   " + " · ".join(f"{cat} {n}" for cat, n in counts.most_common()))

    path = build(articles)
    print(f"✅ Page mise à jour : {path}")


if __name__ == "__main__":
    main()
