#!/usr/bin/env python3
"""Apify-driven refresh of social_posts + social_comments for piloto roster.

Plan: .context/PLAN-2026-05-07-apify-refresh.md (2026-05-07)
Window: posts/comments published_at >= 2026-04-07 (30d).
Budget cap: $4.50 USD (Apify free tier $4.94 disponible).

Idempotent UPSERT por platform_post_id / platform_comment_id.
Posts INSERT antes de comments (FK constraint).
Hard-stop si Apify usage > $4.50 antes de cada actor.

Usage:
    # Test mini (1 dirigente, 1 plataforma — barato, valida pipeline)
    python3 backend/scripts/apify_refresh_all.py --dirigente-id 8 --platform twitter

    # Sprint 1 — Ballesteros completo
    python3 backend/scripts/apify_refresh_all.py --dirigente-id 8

    # Sprint 2 — todos
    python3 backend/scripts/apify_refresh_all.py --all

    # Dry-run (no inserta, solo log)
    python3 backend/scripts/apify_refresh_all.py --dirigente-id 8 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from apify_client import ApifyClient

# ── Config ───────────────────────────────────────────────────────────

# Cargar .env del proyecto root + .env.scraping-keys de backend
PROJECT_ROOT = Path("/Users/marxchavez/Projects/crece-v2")
for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / "backend/.env.scraping-keys"]:
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

APIFY_TOKEN = os.environ["APIFY_TOKEN"]
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")  # TT comments via API interna proxyeada
DB_DSN = os.environ.get(
    "DB_DSN",
    "host=localhost port=5438 dbname=crece user=crece password=crece_dev",
)
HASH_SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")

WINDOW_DAYS = int(os.environ.get("APIFY_WINDOW_DAYS", "30"))
# Medianoche UTC del día -30: ej. now=2026-05-07 23:55 → window_start=2026-04-07 00:00.
# Sin esto los posts publicados al borde del día -30 quedan justo afuera.
_now = datetime.now(UTC)
WINDOW_START = (_now - timedelta(days=WINDOW_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
BUDGET_CAP_USD = float(os.environ.get("APIFY_BUDGET_CAP", "4.50"))

# Actores (verificados contra runs históricos del CEO 2026-04-18/30)
ACTORS = {
    "TIKTOK_POSTS_COMMENTS": "clockworks/tiktok-scraper",
    "INSTAGRAM_POSTS": "apify/instagram-post-scraper",
    "FACEBOOK_POSTS": "apify/facebook-posts-scraper",
    "FACEBOOK_COMMENTS": "apify/facebook-comments-scraper",
    "YOUTUBE_POSTS": "streamers/youtube-scraper",
    "TWITTER_POSTS": "delicious_zebu/advanced-x-twitter-profile-scraper",
}

# Caps por dirigente
MAX_POSTS_PER_PROFILE = 30  # IG/TT/YT/TW
MAX_FB_POSTS = int(os.environ.get("APIFY_MAX_FB_POSTS", "10"))  # FB es más caro, cap chico — override via env
MAX_TT_COMMENTS_PER_VIDEO = 200  # ScraperAPI free tier 1000 reqs/mes — barato
MAX_FB_COMMENTS_PER_POST = 5
MAX_YT_COMMENTS_PER_VIDEO = 50  # yt-dlp local, $0

DATA_SOURCE = "apify-refresh-2026-05-07"

# ── Logger ───────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("apify_refresh")

# ── Apify client ─────────────────────────────────────────────────────

apify = ApifyClient(APIFY_TOKEN)


def get_apify_usage_usd() -> float:
    """Consulta Apify /users/me/limits para obtener consumo del ciclo actual."""
    r = requests.get(
        f"https://api.apify.com/v2/users/me/limits?token={APIFY_TOKEN}",
        timeout=10,
    )
    r.raise_for_status()
    return float(r.json()["data"]["current"].get("monthlyUsageUsd", 0.0))


def assert_budget_ok(label: str) -> None:
    """Hard-stop si consumo Apify excede BUDGET_CAP_USD."""
    used = get_apify_usage_usd()
    log.info("Apify usage check (%s): $%.4f / $%.2f cap", label, used, BUDGET_CAP_USD)
    if used >= BUDGET_CAP_USD:
        log.error("BUDGET CAP HIT ($%.4f >= $%.2f). Aborting.", used, BUDGET_CAP_USD)
        sys.exit(2)


# ── DB helpers ───────────────────────────────────────────────────────

def db_connect():
    return psycopg2.connect(DB_DSN)


def get_dirigente_profiles(conn, dirigente_id: int | None) -> list[dict]:
    """Devuelve lista de (dirigente_id, full_name, platform, handle, profile_id)."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if dirigente_id:
        cur.execute(
            """
            SELECT d.id AS dirigente_id, d.full_name,
                   p.platform::text AS platform, p.handle, p.id AS profile_id
            FROM dirigentes d
            JOIN social_profiles p ON p.dirigente_id = d.id
            WHERE d.id = %s
            ORDER BY p.platform
            """,
            (dirigente_id,),
        )
    else:
        cur.execute(
            """
            SELECT d.id AS dirigente_id, d.full_name,
                   p.platform::text AS platform, p.handle, p.id AS profile_id
            FROM dirigentes d
            JOIN social_profiles p ON p.dirigente_id = d.id
            WHERE d.id IN (1, 2, 3, 4, 5, 6, 8)
            ORDER BY d.id, p.platform
            """,
        )
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def author_hash(platform: str, author_id: str | None, fallback: str = "") -> str:
    raw = f"{platform}:{author_id or fallback}:{HASH_SALT}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def upsert_post(conn, profile_id: int, platform: str, post: dict) -> int | None:
    """UPSERT social_posts. Devuelve social_posts.id o None si skip."""
    ppid = str(post.get("platform_post_id") or "").strip()
    if not ppid:
        return None
    pub = post.get("published_at")
    if pub and pub < WINDOW_START:
        # Fuera de ventana 30d — skip silently
        return None

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO social_posts
            (profile_id, platform_post_id, content, post_type, published_at,
             likes, comments, shares, views, engagement_rate,
             is_political, raw_data, scraped_at, clasificacion_origen)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
        ON CONFLICT (platform_post_id) DO UPDATE SET
            content = EXCLUDED.content,
            likes = EXCLUDED.likes,
            comments = EXCLUDED.comments,
            shares = EXCLUDED.shares,
            views = EXCLUDED.views,
            scraped_at = EXCLUDED.scraped_at,
            raw_data = EXCLUDED.raw_data
        RETURNING id
        """,
        (
            profile_id,
            ppid,
            (post.get("content") or "")[:5000],
            post.get("post_type") or "TEXT",
            pub,
            post.get("likes") or 0,
            post.get("comments") or 0,
            post.get("shares") or 0,
            post.get("views") or 0,
            post.get("engagement_rate") or 0.0,
            False,  # is_political — NLP layer lo decide después
            json.dumps({**(post.get("raw_data") or {}), "data_source": DATA_SOURCE}),
            datetime.now(UTC),
            "ai_suggested",
        ),
    )
    pid = cur.fetchone()[0]
    cur.close()
    return pid


def upsert_comment(conn, parent_post_id: int, platform: str, comment: dict) -> bool:
    """UPSERT social_comments. Devuelve True si insertado/actualizado."""
    pcid = str(comment.get("platform_comment_id") or "").strip()
    text = (comment.get("content") or "").strip()
    if not pcid or not text:
        return False

    pub = comment.get("published_at")
    if pub and pub < WINDOW_START:
        return False

    ah = author_hash(platform, comment.get("author_id"), fallback=pcid)
    # Sprint C: cachear handle público (no PII directa bajo LFPDPPP).
    # Actores Apify exponen `author_name` / `username` / `commenter_handle`.
    handle = (
        comment.get("commenter_handle")
        or comment.get("username")
        or comment.get("author_name")
        or None
    )
    handle = handle.strip().lstrip("@") if handle else None
    if handle and len(handle) > 255:
        handle = handle[:255]

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO social_comments
            (parent_post_id, platform_comment_id, content, author_hash,
             likes, published_at, is_reply_to_comment, data_source,
             commenter_handle)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (platform_comment_id) DO UPDATE SET
            likes = EXCLUDED.likes,
            content = EXCLUDED.content,
            commenter_handle = COALESCE(EXCLUDED.commenter_handle, social_comments.commenter_handle)
        """,
        (
            parent_post_id,
            pcid,
            text[:5000],
            ah,
            int(comment.get("likes") or 0),
            pub,
            bool(comment.get("is_reply") or False),
            DATA_SOURCE,
            handle,
        ),
    )
    cur.close()
    return True


# ── Date parsing (robusto contra formatos de varios actores) ─────────

def parse_date(value) -> datetime | None:
    """Acepta ISO 8601, UNIX timestamp (int/float/str), 'YYYY-MM-DD HH:MM:SS', None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(int(value), tz=UTC)
        except (ValueError, OSError):
            return None
    if isinstance(value, str):
        v = value.strip()
        # ISO 8601 Apify estándar: "2026-04-29T18:03:33.000Z"
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except ValueError:
            pass
        # UNIX timestamp como string
        try:
            return datetime.fromtimestamp(int(float(v)), tz=UTC)
        except (ValueError, OSError):
            pass
    return None


# ── Normalizers (raw Apify item → schema BD) ──────────────────────────

def _strip_at(handle: str) -> str:
    return handle.lstrip("@").strip()


def normalize_twitter_post(raw: dict) -> dict:
    """delicious_zebu/advanced-x-twitter-profile-scraper output.

    Keys reales del actor (verificado run 3LgDxF8NeXWc1g4h6 2026-05-07):
        tweetId, fullText, createdAt (str "YYYY-MM-DD HH:MM:SS+00:00"),
        likeCount, replyCount, repostCount, viewCount, tweetUrl.
    """
    views_raw = raw.get("viewCount", 0)
    try:
        views = int(views_raw) if views_raw not in (None, "") else 0
    except (TypeError, ValueError):
        views = 0
    return {
        "platform_post_id": str(raw.get("tweetId") or raw.get("id") or ""),
        "content": raw.get("fullText") or raw.get("text") or "",
        "post_type": "TEXT",
        "published_at": parse_date(raw.get("createdAt") or raw.get("created_at")),
        "likes": int(raw.get("likeCount") or 0),
        "comments": int(raw.get("replyCount") or 0),
        "shares": int(raw.get("repostCount") or 0),
        "views": views,
        "raw_data": {
            "tweetUrl": raw.get("tweetUrl"),
            "authorHandle": raw.get("authorHandle"),
        },
    }


def normalize_instagram_post(raw: dict) -> tuple[dict, list[dict]]:
    """apify/instagram-post-scraper output. Devuelve (post, [comments])."""
    post = {
        "platform_post_id": str(raw.get("id") or raw.get("shortCode") or ""),
        "content": raw.get("caption") or "",
        "post_type": (raw.get("type") or "Image").upper().replace("SIDECAR", "CAROUSEL"),
        "published_at": parse_date(raw.get("timestamp")),
        "likes": int(raw.get("likesCount") or 0),
        "comments": int(raw.get("commentsCount") or 0),
        "shares": 0,
        "views": int(raw.get("videoPlayCount") or raw.get("videoViewCount") or 0),
        "raw_data": {k: raw.get(k) for k in ("id", "shortCode", "url", "type")},
    }
    if post["post_type"] not in ("TEXT", "IMAGE", "VIDEO", "REEL", "STORY", "CAROUSEL"):
        post["post_type"] = "IMAGE"

    comments_raw = raw.get("latestComments") or []
    comments = []
    for c in comments_raw:
        comments.append({
            "platform_comment_id": str(c.get("id") or ""),
            "content": c.get("text") or "",
            "author_id": c.get("ownerUsername") or c.get("ownerId"),
            "likes": int(c.get("likesCount") or 0),
            "published_at": parse_date(c.get("timestamp")),
            "is_reply": False,
        })
    return post, comments


def normalize_facebook_post(raw: dict) -> dict:
    """apify/facebook-posts-scraper output."""
    likes = int(raw.get("likes") or 0)
    return {
        "platform_post_id": str(raw.get("postId") or ""),
        "content": raw.get("text") or "",
        "post_type": "VIDEO" if (raw.get("media") and any("video" in str(m).lower() for m in raw.get("media", []))) else "TEXT",
        "published_at": parse_date(raw.get("time") or raw.get("timestamp")),
        "likes": likes,
        "comments": int(raw.get("comments") or 0),
        "shares": int(raw.get("shares") or 0),
        "views": 0,
        "raw_data": {k: raw.get(k) for k in ("postId", "url", "facebookUrl", "topLevelUrl")},
    }


def normalize_facebook_comment(raw: dict, parent_pcid: str) -> dict:
    """apify/facebook-comments-scraper output."""
    return {
        "platform_comment_id": str(raw.get("commentId") or raw.get("id") or ""),
        "content": raw.get("text") or "",
        "author_id": (raw.get("profileId") or raw.get("profileUrl") or
                       (raw.get("user") or {}).get("id")),
        "likes": int(raw.get("likesCount") or raw.get("likes") or 0),
        "published_at": parse_date(raw.get("date") or raw.get("publishedTime")),
        "is_reply": bool(raw.get("commentId") and raw.get("parentId")),
    }


def normalize_tiktok_post(raw: dict) -> dict:
    """clockworks/tiktok-scraper output. Comments vienen en dataset auxiliar
    cuyo URL está en raw['commentsDatasetUrl'] (mismo dataset para todos los
    posts del run; se descarga una sola vez en refresh_tiktok).
    """
    return {
        "platform_post_id": str(raw.get("id") or ""),
        "content": raw.get("text") or "",
        "post_type": "VIDEO",
        "published_at": parse_date(raw.get("createTimeISO") or raw.get("createTime")),
        "likes": int(raw.get("diggCount") or 0),
        "comments": int(raw.get("commentCount") or 0),
        "shares": int(raw.get("shareCount") or 0),
        "views": int(raw.get("playCount") or 0),
        "raw_data": {
            "id": raw.get("id"),
            "webVideoUrl": raw.get("webVideoUrl"),
            "authorMeta": raw.get("authorMeta"),
        },
    }


def normalize_tiktok_comment(raw: dict) -> dict:
    """clockworks/tiktok-scraper comment (dataset auxiliar)."""
    return {
        "platform_comment_id": str(raw.get("cid") or ""),
        "content": raw.get("text") or "",
        "author_id": raw.get("uniqueId") or raw.get("uid"),
        "likes": int(raw.get("diggCount") or 0),
        "published_at": parse_date(raw.get("createTimeISO") or raw.get("createTime")),
        "is_reply": bool(raw.get("repliesToId")),
        "video_url": raw.get("videoWebUrl") or "",
    }


def normalize_youtube_post(raw: dict) -> dict:
    """streamers/youtube-scraper output."""
    return {
        "platform_post_id": str(raw.get("id") or ""),
        "content": (raw.get("title") or "") + ("\n\n" + (raw.get("text") or raw.get("description") or "")
                                                  if raw.get("text") or raw.get("description") else ""),
        "post_type": "VIDEO",
        "published_at": parse_date(raw.get("date") or raw.get("publishedTime")),
        "likes": int(raw.get("likes") or 0),
        "comments": int(raw.get("commentsCount") or raw.get("commentCount") or 0),
        "shares": 0,
        "views": int(raw.get("viewCount") or 0),
        "raw_data": {k: raw.get(k) for k in ("id", "url", "channelName")},
    }


# ── Refreshers por plataforma ───────────────────────────────────────

def refresh_twitter(conn, profile: dict, dry_run: bool) -> dict:
    """delicious_zebu/advanced-x-twitter-profile-scraper."""
    handle = _strip_at(profile["handle"])
    url = f"https://x.com/{handle}"
    log.info("[TW] %s — running %s", handle, ACTORS["TWITTER_POSTS"])

    run_input = {
        "accountUrls": [url],
        "startDate": WINDOW_START.strftime("%Y-%m-%d"),
        "endDate": datetime.now(UTC).strftime("%Y-%m-%d"),
        "splitMode": "day",
        "language": "es",
        "maxCollections": MAX_POSTS_PER_PROFILE,
    }
    run = apify.actor(ACTORS["TWITTER_POSTS"]).call(run_input=run_input, timeout_secs=300)
    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("[TW] %s — got %d items, run cost=$%.4f", handle, len(items), run.get("usageTotalUsd", 0.0))

    n_posts = 0
    for raw in items:
        post = normalize_twitter_post(raw)
        if not post["platform_post_id"] or not post["published_at"]:
            continue
        if dry_run:
            n_posts += 1
            continue
        if upsert_post(conn, profile["profile_id"], "TWITTER", post):
            n_posts += 1
    if not dry_run:
        conn.commit()
    return {"plat": "TW", "items_apify": len(items), "posts": n_posts, "comments": 0,
            "cost": run.get("usageTotalUsd", 0.0)}


def refresh_instagram(conn, profile: dict, dry_run: bool) -> dict:
    """apify/instagram-post-scraper (trae latestComments en mismo run)."""
    handle = _strip_at(profile["handle"])
    log.info("[IG] %s — running %s", handle, ACTORS["INSTAGRAM_POSTS"])

    run_input = {
        "username": [handle],
        "resultsLimit": MAX_POSTS_PER_PROFILE,
        "skipPinnedPosts": False,
        "dataDetailLevel": "detailedData",
    }
    run = apify.actor(ACTORS["INSTAGRAM_POSTS"]).call(run_input=run_input, timeout_secs=300)
    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("[IG] %s — got %d items, run cost=$%.4f", handle, len(items), run.get("usageTotalUsd", 0.0))

    n_posts = n_comments = 0
    for raw in items:
        post, comments = normalize_instagram_post(raw)
        if not post["platform_post_id"] or not post["published_at"]:
            continue
        if dry_run:
            n_posts += 1
            n_comments += len(comments)
            continue
        pid = upsert_post(conn, profile["profile_id"], "INSTAGRAM", post)
        if not pid:
            continue
        n_posts += 1
        for c in comments:
            if upsert_comment(conn, pid, "INSTAGRAM", c):
                n_comments += 1
    if not dry_run:
        conn.commit()
    return {"plat": "IG", "items_apify": len(items), "posts": n_posts, "comments": n_comments,
            "cost": run.get("usageTotalUsd", 0.0)}


def refresh_facebook(conn, profile: dict, dry_run: bool) -> dict:
    """Dos runs: facebook-posts-scraper + facebook-comments-scraper."""
    handle = profile["handle"]  # FB es case-sensitive, no strip
    fb_url = f"https://www.facebook.com/{handle}"
    log.info("[FB] %s — running facebook-posts-scraper", handle)

    posts_input = {
        "startUrls": [{"url": fb_url}],
        "resultsLimit": MAX_FB_POSTS,
        "captionText": False,
    }
    posts_run = apify.actor(ACTORS["FACEBOOK_POSTS"]).call(run_input=posts_input, timeout_secs=300)
    posts_items = list(apify.dataset(posts_run["defaultDatasetId"]).iterate_items())
    log.info("[FB] %s — got %d posts, cost=$%.4f", handle, len(posts_items),
             posts_run.get("usageTotalUsd", 0.0))

    n_posts = 0
    post_id_map: dict[str, int] = {}  # platform_post_id → social_posts.id
    post_url_map: dict[str, str] = {}  # platform_post_id → fb post URL
    for raw in posts_items:
        post = normalize_facebook_post(raw)
        if not post["platform_post_id"] or not post["published_at"]:
            continue
        if dry_run:
            n_posts += 1
            post_url_map[post["platform_post_id"]] = (raw.get("url") or raw.get("topLevelUrl") or "")
            continue
        pid = upsert_post(conn, profile["profile_id"], "FACEBOOK", post)
        if pid:
            n_posts += 1
            post_id_map[post["platform_post_id"]] = pid
            post_url_map[post["platform_post_id"]] = (raw.get("url") or raw.get("topLevelUrl") or "")
    if not dry_run:
        conn.commit()

    cost = posts_run.get("usageTotalUsd", 0.0)
    n_comments = 0
    if post_url_map:
        log.info("[FB] %s — running facebook-comments-scraper for %d posts",
                 handle, len(post_url_map))
        urls = [u for u in post_url_map.values() if u]
        if urls:
            comments_input = {
                "startUrls": [{"url": u} for u in urls],
                "resultsLimit": MAX_FB_COMMENTS_PER_POST,
                "includeNestedComments": False,
                "viewOption": "RANKED_UNFILTERED",
            }
            comments_run = apify.actor(ACTORS["FACEBOOK_COMMENTS"]).call(
                run_input=comments_input, timeout_secs=300
            )
            comments_items = list(apify.dataset(comments_run["defaultDatasetId"]).iterate_items())
            cost += comments_run.get("usageTotalUsd", 0.0)
            log.info("[FB] %s — got %d comments, cost=$%.4f", handle, len(comments_items),
                     comments_run.get("usageTotalUsd", 0.0))

            # Build url → social_posts.id lookup. Match por URL canónica del post
            # (inputUrl del comment = url del post-scraper).
            url_to_pid: dict[str, int] = {}
            for ppid, url in post_url_map.items():
                pid_val = post_id_map.get(ppid) if not dry_run else 1
                if url and pid_val:
                    url_to_pid[url] = pid_val
                    url_to_pid[url.rstrip("/")] = pid_val

            for raw in comments_items:
                # FB comments scraper devuelve inputUrl = URL del post (igual al
                # `url` del post-scraper), o facebookUrl como fallback.
                purl = (raw.get("inputUrl") or raw.get("facebookUrl") or "").strip()
                pid = url_to_pid.get(purl) or url_to_pid.get(purl.rstrip("/"))
                if not pid:
                    continue
                c = normalize_facebook_comment(raw, "")
                if dry_run:
                    n_comments += 1
                    continue
                if upsert_comment(conn, pid, "FACEBOOK", c):
                    n_comments += 1
            if not dry_run:
                conn.commit()

    return {"plat": "FB", "items_apify": len(posts_items), "posts": n_posts,
            "comments": n_comments, "cost": cost}


def refresh_tiktok(conn, profile: dict, dry_run: bool) -> dict:
    """TT split: clockworks/tiktok-scraper para POSTS (Apify, lista videos) +
    ScraperAPI proxy a tiktok.com/api/comment/list/ para COMMENTS ($0 free tier).

    Reemplaza el patrón previo que usaba dataset auxiliar de Apify (frágil:
    requería match por videoWebUrl, costo extra por commentsPerPost). El flujo
    ScraperAPI ya estaba probado en Sprint B 2026-04-14 (commit 2660807).
    """
    handle = _strip_at(profile["handle"])
    log.info("[TT] %s — running %s (posts only, comments via ScraperAPI)",
             handle, ACTORS["TIKTOK_POSTS_COMMENTS"])

    run_input = {
        "profiles": [handle],
        "resultsPerPage": MAX_POSTS_PER_PROFILE,
        "shouldDownloadCovers": False,
        "shouldDownloadVideos": False,
        "shouldDownloadSubtitles": False,
        "profileScrapeSections": ["videos"],
        "profileSorting": "latest",
        "excludePinnedPosts": False,
        "maxProfilesPerQuery": 10,
        "scrapeRelatedVideos": False,
        "shouldDownloadSlideshowImages": False,
        # NO commentsPerPost — los comments los trae ScraperAPI separado
    }
    run = apify.actor(ACTORS["TIKTOK_POSTS_COMMENTS"]).call(run_input=run_input, timeout_secs=600)
    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    apify_cost = run.get("usageTotalUsd", 0.0)
    log.info("[TT] %s — got %d items, apify_cost=$%.4f", handle, len(items), apify_cost)

    # 1. UPSERT posts y construir aweme_id → social_posts.id map
    n_posts = 0
    aweme_to_pid: dict[str, int] = {}
    for raw in items:
        post = normalize_tiktok_post(raw)
        if not post["platform_post_id"] or not post["published_at"]:
            continue
        if dry_run:
            n_posts += 1
            aweme_to_pid[post["platform_post_id"]] = 1
            continue
        pid = upsert_post(conn, profile["profile_id"], "TIKTOK", post)
        if pid:
            n_posts += 1
            aweme_to_pid[post["platform_post_id"]] = pid
    if not dry_run:
        conn.commit()

    # 2. Comments via ScraperAPI (sin costo Apify, $0 si SCRAPERAPI_KEY válida)
    n_comments = 0
    if not SCRAPERAPI_KEY:
        log.warning("[TT] %s — SCRAPERAPI_KEY ausente, skip comments", handle)
    elif not aweme_to_pid:
        log.info("[TT] %s — sin posts en ventana, skip comments", handle)
    else:
        log.info("[TT] %s — fetching comments via ScraperAPI for %d videos",
                 handle, len(aweme_to_pid))
        for aweme_id, parent_pid in aweme_to_pid.items():
            try:
                raw_comments = _scraperapi_tt_fetch_all(aweme_id)
            except Exception as e:
                log.warning("[TT] %s aweme=%s ScraperAPI error: %s", handle, aweme_id, e)
                continue
            for raw in raw_comments:
                c = _normalize_tt_comment_from_api(raw)
                if dry_run:
                    n_comments += 1
                    continue
                if upsert_comment(conn, parent_pid, "TIKTOK", c):
                    n_comments += 1
        if not dry_run:
            conn.commit()

    return {"plat": "TT", "items_apify": len(items), "posts": n_posts, "comments": n_comments,
            "cost": apify_cost}


# ── ScraperAPI helpers (TT comments) ────────────────────────────────

def _scraperapi_tt_fetch_page(aweme_id: str, cursor: int) -> dict | None:
    """Una página de comments. Endpoint interno TT proxyeado por ScraperAPI."""
    import urllib.parse as _u
    api_url = (
        "https://www.tiktok.com/api/comment/list/"
        f"?aweme_id={aweme_id}&cursor={cursor}&count=20&aid=1988"
    )
    proxied = (
        "https://api.scraperapi.com/"
        f"?api_key={SCRAPERAPI_KEY}&url={_u.quote(api_url, safe='')}"
    )
    r = requests.get(proxied, timeout=90)
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except ValueError:
        return None


def _scraperapi_tt_fetch_all(aweme_id: str) -> list[dict]:
    """Pagina cursor++20 hasta has_more=0 o cap MAX_TT_COMMENTS_PER_VIDEO."""
    import time as _t
    collected: list[dict] = []
    cursor = 0
    while len(collected) < MAX_TT_COMMENTS_PER_VIDEO:
        page = _scraperapi_tt_fetch_page(aweme_id, cursor)
        if not page:
            break
        items = page.get("comments") or []
        if not items:
            break
        collected.extend(items)
        if page.get("has_more") != 1:
            break
        next_cursor = page.get("cursor")
        if not isinstance(next_cursor, int) or next_cursor <= cursor:
            break
        cursor = next_cursor
        _t.sleep(1.0)  # ser amables con rate limit
    return collected[:MAX_TT_COMMENTS_PER_VIDEO]


def _normalize_tt_comment_from_api(raw: dict) -> dict:
    """Item del endpoint /api/comment/list/ TT (estructura nativa)."""
    ts = raw.get("create_time")
    pub = datetime.fromtimestamp(int(ts), tz=UTC) if isinstance(ts, int) and ts > 0 else None
    user = raw.get("user") or {}
    return {
        "platform_comment_id": str(raw.get("cid") or ""),
        "content": (raw.get("text") or "").strip(),
        "author_id": user.get("uid") or user.get("unique_id"),
        "likes": int(raw.get("digg_count") or 0),
        "published_at": pub,
        "is_reply": bool(raw.get("reply_id")) and raw.get("reply_id") != "0",
    }


def refresh_youtube(conn, profile: dict, dry_run: bool) -> dict:
    """streamers/youtube-scraper para posts + yt-dlp local para comments."""
    handle = profile["handle"]
    yt_url = f"https://www.youtube.com/@{handle}" if not handle.startswith("@") else f"https://www.youtube.com/{handle}"
    log.info("[YT] %s — running %s", handle, ACTORS["YOUTUBE_POSTS"])

    run_input = {
        "startUrls": [{"url": yt_url}],
        "maxResults": MAX_POSTS_PER_PROFILE,
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    }
    run = apify.actor(ACTORS["YOUTUBE_POSTS"]).call(run_input=run_input, timeout_secs=600)
    items = list(apify.dataset(run["defaultDatasetId"]).iterate_items())
    log.info("[YT] %s — got %d items, cost=$%.4f", handle, len(items), run.get("usageTotalUsd", 0.0))

    n_posts = 0
    post_id_video_map: dict[int, str] = {}  # social_posts.id → video_id
    for raw in items:
        post = normalize_youtube_post(raw)
        if not post["platform_post_id"] or not post["published_at"]:
            continue
        if dry_run:
            n_posts += 1
            continue
        pid = upsert_post(conn, profile["profile_id"], "YOUTUBE", post)
        if pid:
            n_posts += 1
            post_id_video_map[pid] = post["platform_post_id"]
    if not dry_run:
        conn.commit()

    # YT comments via yt-dlp local ($0)
    n_comments = 0
    if not dry_run and post_id_video_map:
        log.info("[YT] %s — fetching comments via yt-dlp for %d videos",
                 handle, len(post_id_video_map))
        n_comments = fetch_yt_comments_local(conn, post_id_video_map)

    return {"plat": "YT", "items_apify": len(items), "posts": n_posts, "comments": n_comments,
            "cost": run.get("usageTotalUsd", 0.0)}


def fetch_yt_comments_local(conn, post_id_video_map: dict[int, str]) -> int:
    """Usa yt-dlp local (--write-comments) para traer comments YT. $0 costo."""
    ytdlp = shutil.which("yt-dlp")
    if not ytdlp:
        log.warning("yt-dlp no encontrado en PATH — skip YT comments")
        return 0

    n = 0
    for parent_post_id, video_id in post_id_video_map.items():
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            r = subprocess.run(
                [
                    ytdlp,
                    "--skip-download", "--write-comments", "--no-write-info-json",
                    "--dump-single-json", "--no-warnings",
                    "--extractor-args", f"youtube:max_comments={MAX_YT_COMMENTS_PER_VIDEO};comment_sort=top",
                    url,
                ],
                capture_output=True, text=True, timeout=180,
            )
            if r.returncode != 0:
                log.warning("yt-dlp failed for %s: %s", video_id, r.stderr[-200:])
                continue
            info = json.loads(r.stdout)
            for c in (info.get("comments") or []):
                ts = c.get("timestamp")
                pub = parse_date(ts) if ts else None
                comment = {
                    "platform_comment_id": str(c.get("id") or ""),
                    "content": c.get("text") or "",
                    "author_id": c.get("author_id") or c.get("author"),
                    "likes": int(c.get("like_count") or 0),
                    "published_at": pub,
                    "is_reply": bool(c.get("parent") and c.get("parent") != "root"),
                }
                if upsert_comment(conn, parent_post_id, "YOUTUBE", comment):
                    n += 1
        except subprocess.TimeoutExpired:
            log.warning("yt-dlp timeout for %s", video_id)
        except Exception as e:
            log.warning("yt-dlp error for %s: %s", video_id, e)
    conn.commit()
    return n


# ── Main orchestrator ────────────────────────────────────────────────

PLATFORM_HANDLERS = {
    "TWITTER": refresh_twitter,
    "INSTAGRAM": refresh_instagram,
    "FACEBOOK": refresh_facebook,
    "TIKTOK": refresh_tiktok,
    "YOUTUBE": refresh_youtube,
}

PLATFORM_ALIAS = {
    "twitter": "TWITTER", "tw": "TWITTER", "x": "TWITTER",
    "instagram": "INSTAGRAM", "ig": "INSTAGRAM",
    "facebook": "FACEBOOK", "fb": "FACEBOOK",
    "tiktok": "TIKTOK", "tt": "TIKTOK",
    "youtube": "YOUTUBE", "yt": "YOUTUBE",
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dirigente-id", type=int, default=None)
    p.add_argument("--all", action="store_true")
    p.add_argument("--platform", default=None, help="twitter/instagram/facebook/tiktok/youtube")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if not args.dirigente_id and not args.all:
        log.error("--dirigente-id N o --all requerido")
        return 1

    platform_filter = None
    if args.platform:
        platform_filter = PLATFORM_ALIAS.get(args.platform.lower())
        if not platform_filter:
            log.error("platform inválido: %s", args.platform)
            return 1

    conn = db_connect()

    profiles = get_dirigente_profiles(conn, args.dirigente_id if not args.all else None)
    if platform_filter:
        profiles = [p for p in profiles if p["platform"] == platform_filter]

    if not profiles:
        log.error("0 profiles match")
        return 1

    log.info("=" * 70)
    log.info("Apify refresh — %d profiles, dry_run=%s, window=%s",
             len(profiles), args.dry_run, WINDOW_START.strftime("%Y-%m-%d"))
    log.info("=" * 70)

    if not args.dry_run:
        assert_budget_ok("start")

    results = []
    for prof in profiles:
        # Hard-stop antes de cada plataforma
        if not args.dry_run:
            assert_budget_ok(f"before {prof['full_name']} {prof['platform']}")

        handler = PLATFORM_HANDLERS.get(prof["platform"])
        if not handler:
            log.warning("Sin handler para %s, skip", prof["platform"])
            continue

        log.info("--- %s [%s] handle=%s ---",
                 prof["full_name"], prof["platform"], prof["handle"])
        try:
            res = handler(conn, prof, args.dry_run)
            res["dirigente"] = prof["full_name"]
            results.append(res)
            log.info("  → %s posts=%d comments=%d cost=$%.4f",
                     res["plat"], res["posts"], res["comments"], res["cost"])
        except Exception as e:
            log.exception("FAIL %s %s: %s", prof["full_name"], prof["platform"], e)
            results.append({
                "dirigente": prof["full_name"], "plat": prof["platform"],
                "posts": 0, "comments": 0, "cost": 0.0, "error": str(e)[:200],
            })

    # Reporte final
    total_cost = sum(r["cost"] for r in results)
    total_posts = sum(r["posts"] for r in results)
    total_comments = sum(r["comments"] for r in results)
    log.info("=" * 70)
    log.info("REPORT")
    for r in results:
        err = f" ERROR={r['error']}" if r.get("error") else ""
        log.info("  %s [%s] posts=%d comments=%d cost=$%.4f%s",
                 r["dirigente"], r["plat"], r["posts"], r["comments"], r["cost"], err)
    log.info("-" * 70)
    log.info("TOTAL: posts=%d comments=%d cost=$%.4f", total_posts, total_comments, total_cost)
    log.info("=" * 70)

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
