"""Génère la page web docs/index.html à partir des articles."""
import json
import os
from datetime import datetime, timezone

from config import PAGE_PATH

TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Veille PSG</title>
<style>
  :root {
    --navy: #0b2545; --navy-2: #13315c; --red: #da291c;
    --bg: #f3f5f9; --card: #ffffff; --text: #14213d; --muted: #6b7a90; --line: #e3e8f0;
    --c-mercato: #7c3aed; --c-infirmerie: #dc2626; --c-matchs: #059669;
    --c-declarations: #2563eb; --c-institutionnel: #d97706; --c-autre: #64748b;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0a0f1c; --card: #121a2b; --text: #e6ebf5; --muted: #8b97ad; --line: #1f2a40; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
  header { background: linear-gradient(135deg, var(--navy), var(--navy-2)); color: #fff;
           padding: 18px 16px 14px; position: sticky; top: 0; z-index: 10;
           box-shadow: 0 2px 12px rgba(0,0,0,.25); }
  .top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
         max-width: 860px; margin: 0 auto; }
  h1 { margin: 0; font-size: 20px; letter-spacing: .3px; }
  h1 span { color: var(--red); }
  .updated { font-size: 12px; opacity: .8; }
  .tabs { display: flex; gap: 6px; overflow-x: auto; max-width: 860px; margin: 12px auto 0;
          scrollbar-width: none; padding-bottom: 2px; }
  .tabs::-webkit-scrollbar { display: none; }
  .tab { flex: none; border: 1px solid rgba(255,255,255,.25); background: transparent; color: #fff;
         padding: 7px 12px; border-radius: 999px; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .tab b { font-weight: 600; opacity: .7; margin-left: 4px; }
  .tab.active { background: #fff; color: var(--navy); border-color: #fff; }
  .tab.active b { opacity: 1; color: var(--red); }
  main { max-width: 860px; margin: 0 auto; padding: 12px 12px 60px; }
  .filters { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 10px; }
  .search { flex: 1 1 200px; padding: 9px 12px; border-radius: 10px; border: 1px solid var(--line);
            background: var(--card); color: var(--text); font-size: 14px; }
  .chip { border: 1px solid var(--line); background: var(--card); color: var(--muted);
          padding: 6px 10px; border-radius: 999px; font-size: 12px; cursor: pointer; }
  .chip.on { color: #fff; border-color: transparent; }
  .chip.on[data-tier="0"] { background: #047857; } .chip.on[data-tier="1"] { background: #2563eb; }
  .chip.on[data-tier="2"] { background: #d97706; } .chip.on[data-tier="3"] { background: #6b7280; }
  .day { font-size: 12px; text-transform: uppercase; letter-spacing: .8px; color: var(--muted);
         margin: 18px 4px 8px; font-weight: 600; }
  .card { display: block; text-decoration: none; color: inherit; background: var(--card);
          border-radius: 12px; padding: 12px 14px; margin-bottom: 8px; border-left: 4px solid var(--c-autre);
          box-shadow: 0 1px 2px rgba(0,0,0,.05); transition: transform .08s; }
  .card:active { transform: scale(.99); }
  .card[data-cat="Mercato"] { border-left-color: var(--c-mercato); }
  .card[data-cat="Infirmerie"] { border-left-color: var(--c-infirmerie); }
  .card[data-cat="Matchs"] { border-left-color: var(--c-matchs); }
  .card[data-cat="Déclarations"] { border-left-color: var(--c-declarations); }
  .card[data-cat="Institutionnel"] { border-left-color: var(--c-institutionnel); }
  .meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: 11.5px; color: var(--muted); margin-bottom: 5px; }
  .tag { font-weight: 600; text-transform: uppercase; letter-spacing: .4px; font-size: 10.5px; }
  .tag[data-cat="Mercato"] { color: var(--c-mercato); } .tag[data-cat="Infirmerie"] { color: var(--c-infirmerie); }
  .tag[data-cat="Matchs"] { color: var(--c-matchs); } .tag[data-cat="Déclarations"] { color: var(--c-declarations); }
  .tag[data-cat="Institutionnel"] { color: var(--c-institutionnel); } .tag[data-cat="Autre"] { color: var(--c-autre); }
  .tier { padding: 2px 7px; border-radius: 6px; color: #fff; font-weight: 600; font-size: 10.5px; }
  .tier[data-tier="0"] { background: #047857; } .tier[data-tier="1"] { background: #2563eb; }
  .tier[data-tier="2"] { background: #d97706; } .tier[data-tier="3"] { background: #6b7280; }
  .new { background: var(--red); color: #fff; padding: 2px 7px; border-radius: 6px; font-weight: 700; font-size: 10.5px; }
  .title { font-size: 15px; line-height: 1.35; font-weight: 500; }
  .empty { text-align: center; color: var(--muted); padding: 40px 0; }
</style>
</head>
<body>
<header>
  <div class="top">
    <h1>Veille <span>PSG</span></h1>
    <div class="updated" id="updated"></div>
  </div>
  <nav class="tabs" id="tabs"></nav>
</header>
<main>
  <div class="filters">
    <input class="search" id="search" type="search" placeholder="Rechercher un joueur, un club…">
    <button class="chip on" data-tier="0">Officiel</button>
    <button class="chip on" data-tier="1">Très fiable</button>
    <button class="chip on" data-tier="2">À recouper</button>
    <button class="chip on" data-tier="3">Rumeur</button>
  </div>
  <div id="list"></div>
</main>
<script>
const ARTICLES = __DATA__;
const GENERATED_AT = "__GENERATED__";
const CATS = ["Tout", "Mercato", "Infirmerie", "Matchs", "Déclarations", "Institutionnel", "Autre"];
const TIERS = {0: "Officiel", 1: "Très fiable", 2: "À recouper", 3: "Rumeur"};
const TZ = "Europe/Paris";

// "Nouveau" = apparu depuis ta dernière visite (mémorisé dans ce navigateur)
let lastVisit = null;
try {
  lastVisit = localStorage.getItem("veille_psg_last_visit");
  localStorage.setItem("veille_psg_last_visit", new Date().toISOString());
} catch (e) {}

const state = { cat: "Tout", tiers: new Set([0, 1, 2, 3]), q: "" };

function norm(s) { return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, ""); }
function esc(s) { return s.replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
function dayKey(iso) { return new Date(iso).toLocaleDateString("fr-CA", {timeZone: TZ}); }
function dayLabel(key) {
  const today = dayKey(new Date().toISOString());
  const yest = dayKey(new Date(Date.now() - 864e5).toISOString());
  if (key === today) return "Aujourd'hui";
  if (key === yest) return "Hier";
  return new Date(key + "T12:00:00").toLocaleDateString("fr-FR", {weekday: "long", day: "numeric", month: "long"});
}
function hour(iso) { return new Date(iso).toLocaleTimeString("fr-FR", {timeZone: TZ, hour: "2-digit", minute: "2-digit"}); }
function ago(iso) {
  const m = Math.round((Date.now() - new Date(iso)) / 60000);
  if (m < 1) return "à l'instant";
  if (m < 60) return `il y a ${m} min`;
  const h = Math.round(m / 60);
  return h < 24 ? `il y a ${h} h` : `il y a ${Math.round(h / 24)} j`;
}

function filtered(ignoreCat) {
  const q = norm(state.q);
  return ARTICLES.filter(a =>
    (ignoreCat || state.cat === "Tout" || a.category === state.cat) &&
    state.tiers.has(a.tier) &&
    (!q || norm(a.title + " " + a.source_name).includes(q)));
}

function renderTabs() {
  const base = filtered(true);
  document.getElementById("tabs").innerHTML = CATS.map(c => {
    const n = c === "Tout" ? base.length : base.filter(a => a.category === c).length;
    return `<button class="tab ${c === state.cat ? "active" : ""}" data-cat="${c}">${c}<b>${n}</b></button>`;
  }).join("");
}

function renderList() {
  const items = filtered(false);
  const list = document.getElementById("list");
  if (!items.length) { list.innerHTML = `<div class="empty">Aucune info pour ces filtres.</div>`; return; }
  let html = "", current = "";
  for (const a of items) {
    const k = dayKey(a.published_at);
    if (k !== current) { current = k; html += `<div class="day">${dayLabel(k)}</div>`; }
    const isNew = lastVisit && a.first_seen > lastVisit;
    html += `<a class="card" data-cat="${a.category}" href="${esc(a.url)}" target="_blank" rel="noopener">
      <div class="meta">
        ${isNew ? '<span class="new">NOUVEAU</span>' : ""}
        <span class="tag" data-cat="${a.category}">${a.category}</span>
        <span class="tier" data-tier="${a.tier}">${TIERS[a.tier]}</span>
        <span>${esc(a.source_name)} · ${hour(a.published_at)}</span>
      </div>
      <div class="title">${esc(a.title)}</div>
    </a>`;
  }
  list.innerHTML = html;
}

function render() { renderTabs(); renderList(); }

document.getElementById("tabs").addEventListener("click", e => {
  const b = e.target.closest(".tab"); if (!b) return;
  state.cat = b.dataset.cat; render(); window.scrollTo({top: 0});
});
document.querySelectorAll(".chip").forEach(chip => chip.addEventListener("click", () => {
  const t = Number(chip.dataset.tier);
  state.tiers.has(t) ? state.tiers.delete(t) : state.tiers.add(t);
  chip.classList.toggle("on"); render();
}));
document.getElementById("search").addEventListener("input", e => { state.q = e.target.value; render(); });

function updatedLabel() { document.getElementById("updated").textContent = "Mis à jour " + ago(GENERATED_AT); }
updatedLabel(); setInterval(updatedLabel, 60000);
render();
// Recharge la page toutes les 15 min si elle reste ouverte
setTimeout(() => location.reload(), 15 * 60000);
</script>
</body>
</html>
"""


def build(articles: list[dict]) -> str:
    data = json.dumps(articles, ensure_ascii=False).replace("</", "<\\/")
    generated = datetime.now(timezone.utc).isoformat()
    html = TEMPLATE.replace("__DATA__", data).replace("__GENERATED__", generated)
    os.makedirs(os.path.dirname(PAGE_PATH), exist_ok=True)
    with open(PAGE_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    return PAGE_PATH
