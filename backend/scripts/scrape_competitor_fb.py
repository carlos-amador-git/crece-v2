"""scrape_competitor_fb.py — Pipeline ligero competidores FB (D-1.4, 2026-05-16).

Usa browser-harness (skill local) contra Chrome del CEO con cookies FB activas.
NO requiere Apify ni Graph API. Output JSON formato compatible con endpoint
`POST /api/v1/aceptacion/competitors/ingest-monthly-snapshot`.

Estrategia (validada empíricamente + sondeo Juan @ md-research):

1. Header: `followers_count` parseando texto "X mil seguidores" del perfil.
2. Listing scroll → recolectar permalinks únicos del perfil (filtro
   `/{handle}/posts/pfbid` para evitar comment_id permalinks).
3. Por cada permalink → abrir post → leer aria-label `^(\\d+)\\s*reacc` del
   badge principal + aria-label de comments count.

NO usa NLP. NO scrape comments individuales. NO reactor extraction.

Estructura típica de invocación (interactivo desde browser-harness):
    PROFILES = [...]
    for handle in PROFILES:
        snap = scrape_profile(handle)
        ...
    # POST resultado al endpoint CRECE
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Any


# Mapping de texto relativo FB → fecha aproximada
def parse_relative_timestamp(text: str, reference: datetime | None = None) -> datetime | None:
    """Convierte '5 d', '13 sem', '2 h', '10 may' → datetime aproximado.

    Para timeframe de últimos 30 días el approximate suficiente. Devuelve UTC.
    """
    if not text:
        return None
    ref = reference or datetime.now(timezone.utc)
    t = text.strip().lower()
    # "X h" hours
    m = re.match(r"^(\d+)\s*h$", t)
    if m:
        return ref - timedelta(hours=int(m.group(1)))
    # "X min"
    m = re.match(r"^(\d+)\s*min$", t)
    if m:
        return ref - timedelta(minutes=int(m.group(1)))
    # "X d" days
    m = re.match(r"^(\d+)\s*d$", t)
    if m:
        return ref - timedelta(days=int(m.group(1)))
    # "X sem" weeks
    m = re.match(r"^(\d+)\s*sem$", t)
    if m:
        return ref - timedelta(weeks=int(m.group(1)))
    # "X mes"
    m = re.match(r"^(\d+)\s*mes$", t)
    if m:
        return ref - timedelta(days=int(m.group(1)) * 30)
    # "X año"
    m = re.match(r"^(\d+)\s*año", t)
    if m:
        return ref - timedelta(days=int(m.group(1)) * 365)
    return None


def parse_followers_text(raw: str) -> int | None:
    """'244 mil seguidores' → 244000. '1.2 M' → 1200000. '500' → 500."""
    if not raw:
        return None
    m = re.match(r"^([\d.,]+)\s*(mil|m|k)?", raw.strip().lower())
    if not m:
        return None
    num = float(m.group(1).replace(",", "."))
    unit = m.group(2)
    if unit in ("mil", "k"):
        num *= 1000
    elif unit == "m":
        num *= 1_000_000
    return int(round(num))


def parse_reactions_aria(aria: str) -> int | None:
    """'149 reacciones; consulta quién reaccionó' → 149."""
    if not aria:
        return None
    m = re.match(r"^([\d.,]+)\s*reacc", aria.strip(), re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1).replace(",", "").replace(".", ""))


def parse_comments_aria(aria: str) -> int | None:
    """'89 comentarios' → 89. None si no matchea."""
    if not aria:
        return None
    m = re.search(r"(\d[\d.,]*)\s*coment", aria.strip(), re.IGNORECASE)
    if not m:
        return None
    return int(m.group(1).replace(",", "").replace(".", ""))


# ── JS snippets inyectables ──────────────────────────────────────────

JS_GET_FOLLOWERS = """
// Buscar texto del header "X mil seguidores" o "X seguidores"
const candidates = Array.from(document.querySelectorAll('a, span, div'));
const followers_el = candidates.find(e => {
    const t = (e.innerText || '').trim();
    return /^[\\d.,]+\\s*(K|mil|M)?\\s*seguidores/i.test(t);
});
return followers_el ? followers_el.innerText.trim().split('\\n')[0] : null;
"""


def js_collect_permalinks(handle: str) -> str:
    """JS para recolectar permalinks únicos + sus timestamp text del listing actual."""
    return f"""
const handle = {json.dumps(handle)};
const anchors = Array.from(document.querySelectorAll(`a[href*="/${{handle}}/posts/pfbid"]`));
const seen = new Set();
const items = [];
for (const a of anchors) {{
    const href = a.href.split('?')[0];
    if (href.includes('comment_id')) continue;
    const m = href.match(/pfbid[a-zA-Z0-9]+/);
    if (!m) continue;
    const pfbid = m[0];
    if (seen.has(pfbid)) continue;
    seen.add(pfbid);
    items.push({{
        pfbid,
        url: href,
        timestamp_text: (a.innerText || '').trim()
    }});
}}
return JSON.stringify(items);
"""


JS_GET_POST_METADATA = """
// En página de post abierto: encontrar badge reactions del POST principal.
// El badge tiene aria-label "X reacciones; ..."  La técnica es buscar
// el aria-label en TODOS los elementos visibles y filtrar por:
// (1) el primer aria-label con regex ^\\d+\\s*reacc (orden DOM = post first)
// (2) descartar aria-labels de comments (que tienen 1-3 reacciones típicas)
const allLabels = Array.from(document.querySelectorAll('[aria-label]'))
    .map(e => e.getAttribute('aria-label'))
    .filter(x => x && x.length < 300);

// React label del POST: el primero con número grande, o el primero por orden DOM
const react_labels = allLabels.filter(l => /^[\\d.,]+\\s*reacc/i.test(l.trim()));
const comment_labels = allLabels.filter(l => /^[\\d.,]+\\s*coment/i.test(l.trim()));
const share_labels = allLabels.filter(l => /^[\\d.,]+\\s*(veces?\\s+compart|compart)/i.test(l.trim()));

// Title page contiene el texto del post típicamente
const title_match = (document.title || '').match(/^\\S+\\s+\\(\\d+\\)\\s+(.+?)\\s+-\\s+[^-]+\\s+\\|\\s+Facebook/);
const post_text_from_title = title_match ? title_match[1] : null;

return JSON.stringify({
    react_labels_all: react_labels.slice(0, 5),
    comment_labels_all: comment_labels.slice(0, 5),
    share_labels_all: share_labels.slice(0, 5),
    post_text_from_title,
    title_full: document.title
});
"""


# ── Helpers de scraping (a invocar desde browser-harness session) ──

def scrape_profile(
    handle: str,
    new_tab,
    wait_for_load,
    js,
    capture_screenshot,
    *,
    max_scroll_iters: int = 12,
    scroll_step_px: int = 1200,
    scroll_wait_s: float = 2.5,
    post_open_wait_s: float = 3.0,
    days_back: int = 30,
) -> dict[str, Any]:
    """Scrape un perfil FB completo. Devuelve dict listo para JSON.

    Args:
        handle: handle del perfil FB (ej "IvetteMoranDeMurat").
        new_tab/wait_for_load/js/capture_screenshot: helpers de browser-harness.
        max_scroll_iters: iteraciones de scroll para recolectar permalinks.
        days_back: timeframe (típico 30 para "último mes").
    """
    result: dict[str, Any] = {
        "handle": handle,
        "platform": "FACEBOOK",
        "scraped_at_iso": datetime.now(timezone.utc).isoformat(),
        "followers_count": None,
        "followers_text_raw": None,
        "posts": [],
        "errors": [],
    }

    # 1. Navegar al perfil
    profile_url = f"https://www.facebook.com/{handle}"
    new_tab(profile_url)
    wait_for_load()
    time.sleep(2)

    # 2. Followers count del header
    followers_raw = js(JS_GET_FOLLOWERS)
    if followers_raw:
        result["followers_text_raw"] = followers_raw
        result["followers_count"] = parse_followers_text(followers_raw)

    # 3. Scroll + recolectar permalinks únicos
    js("window.scrollTo(0, 0)")
    time.sleep(1.5)
    permalinks: dict[str, dict] = {}
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    for i in range(max_scroll_iters):
        raw = js(js_collect_permalinks(handle))
        items = json.loads(raw) if raw else []
        for item in items:
            pfbid = item["pfbid"]
            if pfbid in permalinks:
                continue
            ts = parse_relative_timestamp(item["timestamp_text"])
            permalinks[pfbid] = {
                "pfbid": pfbid,
                "url": item["url"],
                "timestamp_text": item["timestamp_text"],
                "published_at": ts.isoformat() if ts else None,
                "in_window": ts is not None and ts >= cutoff,
            }
        js(f"window.scrollBy(0, {scroll_step_px})")
        time.sleep(scroll_wait_s)

    posts_in_window = [p for p in permalinks.values() if p["in_window"]]
    result["posts_collected_total"] = len(permalinks)
    result["posts_in_window"] = len(posts_in_window)

    # 4. Para cada post in_window: abrir + extraer counts
    for post_info in posts_in_window:
        try:
            new_tab(post_info["url"])
            wait_for_load()
            time.sleep(post_open_wait_s)
            meta_raw = js(JS_GET_POST_METADATA)
            meta = json.loads(meta_raw) if meta_raw else {}

            react_labels = meta.get("react_labels_all", [])
            comment_labels = meta.get("comment_labels_all", [])
            share_labels = meta.get("share_labels_all", [])

            reactions = parse_reactions_aria(react_labels[0]) if react_labels else 0
            comments = parse_comments_aria(comment_labels[0]) if comment_labels else 0
            shares = parse_comments_aria(share_labels[0]) if share_labels else 0

            result["posts"].append({
                "platform_post_id": post_info["pfbid"],
                "post_url": post_info["url"],
                "content": meta.get("post_text_from_title"),
                "published_at": post_info["published_at"],
                "reactions": reactions or 0,
                "comments_count": comments or 0,
                "shares": shares or 0,
            })
        except Exception as exc:
            result["errors"].append({
                "pfbid": post_info["pfbid"],
                "error": str(exc)[:200],
            })

    return result


# ── Configuración de competidores ──────────────────────────────────

# Handles cargados manualmente — los 7 perfiles activos en competitor_profiles
# Fuente: SELECT profile_handle, platform FROM competitor_profiles WHERE platform='FACEBOOK' AND is_active=TRUE
COMPETITOR_HANDLES_FB = [
    "IvetteMoranDeMurat",      # Saymi (Oaxaca)
    "susanaharpiturribarria",  # Saymi (Oaxaca)
    # 5 originales CDMX migrados commit 824b828 — handles a verificar antes de scrape:
    # "BatresMartin", "Taboada", "Harfuch", "Brugada", "TaboadaAlcalde"
]


def build_ingest_payload(snapshots: list[dict], month_start_iso: str) -> dict:
    """Empaqueta snapshots para POST /competitors/ingest-monthly-snapshot."""
    profiles = []
    for snap in snapshots:
        profiles.append({
            "handle": snap["handle"],
            "platform": snap["platform"],
            "followers_count": snap.get("followers_count"),
            "month_start": month_start_iso,
            "posts": snap.get("posts", []),
        })
    return {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "profiles": profiles,
    }
