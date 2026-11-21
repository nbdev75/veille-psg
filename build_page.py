"""Génère la page web docs/index.html (infos résumées par l'IA + articles bruts)."""
import json
import os
from datetime import datetime, timezone

from config import PAGE_PATH


def _prepare(articles: list[dict], stories: list[dict]) -> tuple[list, list]:
    by_key = {a["dedup_key"]: a for a in articles}
    out_stories = []
    for s in stories:
        arts = [by_key[k] for k in s.get("article_keys", []) if k in by_key]
        if not arts:
            continue
        arts.sort(key=lambda a: (a["tier"], a["published_at"]))
        out_stories.append({
            "id": s["id"], "title": s.get("title", ""), "category": s.get("category", "Autre"),
            "summary": s.get("summary", ""), "reliability": s.get("reliability", 1),
            "reason": s.get("reliability_reason", ""), "status": s.get("mercato_status", ""),
            "hook": s.get("tiktok_hook", ""), "format": s.get("tiktok_format", ""),
            "priority": bool(s.get("priority")), "created_at": s["created_at"],
            "updated_at": s["updated_at"],
            "last": s.get("last_article_at") or max(a["published_at"] for a in arts),
            "sources": [{"name": a["source_name"], "url": a["url"], "tier": a["tier"],
                         "date": a["published_at"], "title": a["title"]} for a in arts],
        })
    out_stories.sort(key=lambda s: s["last"], reverse=True)
    raw = [{"title": a["title"], "url": a["url"], "source": a["source_name"], "tier": a["tier"],
            "category": a["category"], "date": a["published_at"], "seen": a.get("first_seen", "")}
           for a in articles if not a.get("ignored")]
    raw.sort(key=lambda a: a["date"], reverse=True)
    return out_stories, raw


TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<meta name="apple-mobile-web-app-title" content="Veille PSG">
<title>Veille PSG</title>
<style>
  :root {
    --navy: #0b2545; --navy-2: #13315c; --red: #da291c;
    --bg: #f3f5f9; --card: #ffffff; --text: #14213d; --muted: #6b7a90; --line: #e3e8f0; --soft: #f6f8fc;
    --c-Mercato: #7c3aed; --c-Infirmerie: #dc2626; --c-Matchs: #059669;
    --c-Déclarations: #2563eb; --c-Institutionnel: #d97706; --c-Autre: #64748b;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0a0f1c; --card: #121a2b; --text: #e6ebf5; --muted: #8b97ad; --line: #1f2a40; --soft: #0f1726; }
  }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
         background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; }
  header { background: linear-gradient(135deg, var(--navy), var(--navy-2)); color: #fff;
           padding: 16px 16px 12px; position: sticky; top: 0; z-index: 10; box-shadow: 0 2px 12px rgba(0,0,0,.25); }
  .top { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; max-width: 860px; margin: 0 auto; }
  h1 { margin: 0; font-size: 20px; } h1 span { color: var(--red); }
  .updated { font-size: 12px; opacity: .8; }
  .tabs { display: flex; gap: 6px; overflow-x: auto; max-width: 860px; margin: 12px auto 0; scrollbar-width: none; }
  .tabs::-webkit-scrollbar { display: none; }
  .tab { flex: none; border: 1px solid rgba(255,255,255,.25); background: transparent; color: #fff;
         padding: 7px 12px; border-radius: 999px; font-size: 13px; cursor: pointer; white-space: nowrap; }
  .tab b { font-weight: 600; opacity: .7; margin-left: 4px; }
  .tab.active { background: #fff; color: var(--navy); border-color: #fff; }
  .tab.active b { opacity: 1; color: var(--red); }
  main { max-width: 860px; margin: 0 auto; padding: 12px 12px 60px; }
  .filters { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 6px; }
  .search { flex: 1 1 220px; padding: 9px 12px; border-radius: 10px; border: 1px solid var(--line);
            background: var(--card); color: var(--text); font-size: 14px; }
  .chip { border: 1px solid var(--line); background: var(--card); color: var(--muted);
          padding: 6px 10px; border-radius: 999px; font-size: 12px; cursor: pointer; }
  .chip.on { color: #fff; border-color: transparent; }
  .r5 { background: #047857 !important; } .r4 { background: #2563eb !important; }
  .r3 { background: #d97706 !important; } .r2, .r1 { background: #6b7280 !important; }
  .notice { background: #fff7e6; color: #8a5a00; border: 1px solid #f5d48a; border-radius: 10px; padding: 10px 12px; font-size: 13px; margin: 8px 0; }
  .section { font-size: 12px; text-transform: uppercase; letter-spacing: .8px; color: var(--muted); margin: 18px 4px 8px; font-weight: 700; }
  .section.prio { color: var(--red); }
  .card { background: var(--card); border-radius: 14px; padding: 14px; margin-bottom: 10px;
          border-left: 4px solid var(--c-Autre); box-shadow: 0 1px 2px rgba(0,0,0,.05); }
  .meta { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: 11.5px; color: var(--muted); margin-bottom: 7px; }
  .tag { font-weight: 700; text-transform: uppercase; letter-spacing: .4px; font-size: 10.5px; }
  .pill { padding: 2px 8px; border-radius: 6px; color: #fff; font-weight: 700; font-size: 10.5px; }
  .status { padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 10.5px;
            background: rgba(124,58,237,.12); color: #7c3aed; }
  .new { background: var(--red); color: #fff; padding: 2px 7px; border-radius: 6px; font-weight: 700; font-size: 10.5px; }
  .upd { background: #f59e0b; color: #fff; padding: 2px 7px; border-radius: 6px; font-weight: 700; font-size: 10.5px; }
  h3 { margin: 0 0 6px; font-size: 16.5px; line-height: 1.3; }
  .summary { margin: 0 0 10px; font-size: 14.5px; line-height: 1.5; }
  .tiktok { background: var(--soft); border-radius: 10px; padding: 9px 11px; font-size: 13.5px; line-height: 1.4; margin-bottom: 8px; }
  .tiktok .fmt { display: inline-block; margin-top: 4px; font-size: 11.5px; color: var(--muted); font-weight: 600; }
  details { font-size: 13px; }
  summary { cursor: pointer; color: var(--muted); font-weight: 600; padding: 4px 0; list-style: none; }
  summary::-webkit-details-marker { display: none; }
  summary::before { content: "▸ "; } details[open] summary::before { content: "▾ "; }
  .reason { color: var(--muted); font-style: italic; margin: 6px 0; }
  .src { display: block; text-decoration: none; color: inherit; padding: 7px 0; border-top: 1px solid var(--line); }
  .src small { color: var(--muted); }
  .t0 { background: #047857; } .t1 { background: #2563eb; } .t2 { background: #d97706; } .t3 { background: #6b7280; }
  .raw { display: block; text-decoration: none; color: inherit; background: var(--card); border-radius: 12px;
         padding: 11px 14px; margin-bottom: 8px; border-left: 4px solid var(--c-Autre); }
  .raw .title { font-size: 14.5px; line-height: 1.35; }
  .empty { text-align: center; color: var(--muted); padding: 40px 0; }
</style>
</head>
<body>
<header>
  <div class="top"><h1>Veille <span>PSG</span></h1><div class="updated" id="updated"></div></div>
  <nav class="tabs" id="tabs"></nav>
</header>
<main>
  <div class="filters">
    <input class="search" id="search" type="search" placeholder="Rechercher un joueur, un sujet…">
    <span id="chips"></span>
  </div>
  <div id="list"></div>
</main>
<script>
const STORIES = __STORIES__;
const RAW = __RAW__;
const GENERATED_AT = "__GENERATED__";
const CATS = ["Mercato", "Infirmerie", "Matchs", "Déclarations", "Institutionnel", "Autre"];
const TIER = {0: "Officiel", 1: "Très fiable", 2: "À recouper", 3: "Rumeur"};
const TZ = "Europe/Paris";
const AI_ON = STORIES.length > 0;

let lastVisit = null;
try { lastVisit = localStorage.getItem("veille_psg_last_visit");
      localStorage.setItem("veille_psg_last_visit", new Date().toISOString()); } catch (e) {}

const state = { tab: AI_ON ? "Tout" : "Articles bruts", rel: new Set([1,2,3,4,5]), q: "" };

const norm = s => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const esc = s => (s || "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const dayKey = iso => new Date(iso).toLocaleDateString("fr-CA", {timeZone: TZ});
function dayLabel(k) {
  if (k === dayKey(new Date().toISOString())) return "Aujourd'hui";
  if (k === dayKey(new Date(Date.now() - 864e5).toISOString())) return "Hier";
  return new Date(k + "T12:00:00").toLocaleDateString("fr-FR", {weekday: "long", day: "numeric", month: "long"});
}
const hour = iso => new Date(iso).toLocaleTimeString("fr-FR", {timeZone: TZ, hour: "2-digit", minute: "2-digit"});
function ago(iso) {
  const m = Math.round((Date.now() - new Date(iso)) / 60000);
  if (m < 1) return "à l'instant"; if (m < 60) return `il y a ${m} min`;
  const h = Math.round(m / 60); return h < 24 ? `il y a ${h} h` : `il y a ${Math.round(h / 24)} j`;
}
const catColor = c => `var(--c-${c})`;

// ---------- filtres ----------
function storyMatch(s, ignoreTab) {
  const q = norm(state.q);
  return (ignoreTab || state.tab === "Tout" || s.category === state.tab) && state.rel.has(s.reliability) &&
    (!q || norm(s.title + " " + s.summary + " " + s.sources.map(x => x.name + " " + x.title).join(" ")).includes(q));
}
function rawMatch(a) {
  const q = norm(state.q);
  return !q || norm(a.title + " " + a.source).includes(q);
}

// ---------- rendu ----------
function renderTabs() {
  const base = STORIES.filter(s => storyMatch(s, true));
  const tabs = AI_ON ? ["Tout", ...CATS, "Articles bruts"] : ["Articles bruts"];
  document.getElementById("tabs").innerHTML = tabs.map(t => {
    const n = t === "Tout" ? base.length : t === "Articles bruts" ? RAW.filter(rawMatch).length
            : base.filter(s => s.category === t).length;
    return `<button class="tab ${t === state.tab ? "active" : ""}" data-tab="${t}">${t}<b>${n}</b></button>`;
  }).join("");
}

function renderChips() {
  const chips = [[5, "5/5"], [4, "4/5"], [3, "3/5"], [2, "≤ 2/5"]];
  document.getElementById("chips").innerHTML = state.tab === "Articles bruts" ? "" : chips.map(([r, l]) => {
    const on = state.rel.has(r);
    return `<button class="chip ${on ? "on r" + r : ""}" data-rel="${r}">${l}</button>`;
  }).join(" ");
}

function storyCard(s) {
  const isNew = lastVisit && s.created_at > lastVisit;
  const isUpd = !isNew && lastVisit && s.updated_at > lastVisit;
  const names = [...new Set(s.sources.map(x => x.name))];
  const srcLabel = names.slice(0, 2).join(", ") + (names.length > 2 ? ` +${names.length - 2}` : "");
  return `<article class="card" style="border-left-color:${catColor(s.category)}">
    <div class="meta">
      ${isNew ? '<span class="new">NOUVEAU</span>' : ""}${isUpd ? '<span class="upd">MIS À JOUR</span>' : ""}
      <span class="tag" style="color:${catColor(s.category)}">${s.category}</span>
      <span class="pill r${s.reliability}">Fiabilité ${s.reliability}/5</span>
      ${s.status ? `<span class="status">${esc(s.status)}</span>` : ""}
      <span>${ago(s.last)}</span>
    </div>
    <h3>${esc(s.title)}</h3>
    <p class="summary">${esc(s.summary)}</p>
    ${s.hook ? `<div class="tiktok">🎬 <b>Angle TikTok :</b> ${esc(s.hook)}<br><span class="fmt">Format : ${esc(s.format)}</span></div>` : ""}
    <details>
      <summary>📰 ${names.length} source${names.length > 1 ? "s" : ""} · ${esc(srcLabel)}</summary>
      ${s.reason ? `<div class="reason">Pourquoi ${s.reliability}/5 : ${esc(s.reason)}</div>` : ""}
      ${s.sources.map(x => `<a class="src" href="${esc(x.url)}" target="_blank" rel="noopener">
        <span class="pill t${x.tier}">${TIER[x.tier]}</span> <b>${esc(x.name)}</b> <small>· ${hour(x.date)}</small><br>${esc(x.title)}</a>`).join("")}
    </details>
  </article>`;
}

function renderStories() {
  const items = STORIES.filter(s => storyMatch(s, false));
  if (!items.length) return `<div class="empty">Aucune info pour ces filtres.</div>`;
  let html = "";
  const since = new Date(Date.now() - 24 * 3600e3).toISOString();
  const prio = state.tab === "Tout" ? items.filter(s => s.priority && s.last > since).slice(0, 5) : [];
  if (prio.length) html += `<div class="section prio">🚨 À traiter en priorité</div>` + prio.map(storyCard).join("");
  const prioIds = new Set(prio.map(s => s.id));
  let current = "";
  for (const s of items) {
    if (prioIds.has(s.id)) continue;
    const k = dayKey(s.last);
    if (k !== current) { current = k; html += `<div class="section">${dayLabel(k)}</div>`; }
    html += storyCard(s);
  }
  return html;
}

function renderRaw() {
  const items = RAW.filter(rawMatch);
  let html = AI_ON ? "" : `<div class="notice">Analyse IA inactive : ajoute la clé ANTHROPIC_API_KEY pour avoir les infos résumées.</div>`;
  if (!items.length) return html + `<div class="empty">Aucun article.</div>`;
  let current = "";
  for (const a of items) {
    const k = dayKey(a.date);
    if (k !== current) { current = k; html += `<div class="section">${dayLabel(k)}</div>`; }
    const isNew = lastVisit && a.seen > lastVisit;
    html += `<a class="raw" style="border-left-color:${catColor(a.category)}" href="${esc(a.url)}" target="_blank" rel="noopener">
      <div class="meta">${isNew ? '<span class="new">NOUVEAU</span>' : ""}
        <span class="tag" style="color:${catColor(a.category)}">${a.category}</span>
        <span class="pill t${a.tier}">${TIER[a.tier]}</span><span>${esc(a.source)} · ${hour(a.date)}</span></div>
      <div class="title">${esc(a.title)}</div></a>`;
  }
  return html;
}

function render() {
  renderTabs(); renderChips();
  document.getElementById("list").innerHTML = state.tab === "Articles bruts" ? renderRaw() : renderStories();
}

document.getElementById("tabs").addEventListener("click", e => {
  const b = e.target.closest(".tab"); if (!b) return;
  state.tab = b.dataset.tab; render(); window.scrollTo({top: 0});
});
document.getElementById("chips").addEventListener("click", e => {
  const b = e.target.closest(".chip"); if (!b) return;
  const r = Number(b.dataset.rel), group = r === 2 ? [1, 2] : [r];
  group.forEach(x => state.rel.has(x) ? state.rel.delete(x) : state.rel.add(x));
  render();
});
document.getElementById("search").addEventListener("input", e => { state.q = e.target.value; render(); });

const upd = () => document.getElementById("updated").textContent = "Mis à jour " + ago(GENERATED_AT);
upd(); setInterval(upd, 60000);
render();
setTimeout(() => location.reload(), 15 * 60000);
</script>
</body>
</html>
"""


def _js(data) -> str:
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def build(articles: list[dict], stories: list[dict]) -> str:
    out_stories, raw = _prepare(articles, stories)
    html = (TEMPLATE.replace("__STORIES__", _js(out_stories))
                    .replace("__RAW__", _js(raw))
                    .replace("__GENERATED__", datetime.now(timezone.utc).isoformat()))
    os.makedirs(os.path.dirname(PAGE_PATH), exist_ok=True)
    with open(PAGE_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    return PAGE_PATH