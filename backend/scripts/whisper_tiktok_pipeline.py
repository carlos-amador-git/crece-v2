#!/usr/bin/env python3
"""
Whisper pipeline for TikTok/FB/IG posts without text content.

1. Query DB for posts with empty content
2. Download audio via yt-dlp
3. Transcribe via whisper-cli (ggml-small.bin)
4. Update social_posts.content with transcription
5. Run pysentimiento NLP on new text

Usage:
    python backend/scripts/whisper_tiktok_pipeline.py [--limit N] [--dry-run]
"""
import argparse
import os
import re
import subprocess
from pathlib import Path

import psycopg2

DB_URL = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://crece:crece_dev@localhost:5438/crece",
)

WHISPER_CLI = "/opt/homebrew/bin/whisper-cli"
WHISPER_MODEL = os.path.expanduser("~/.local/share/whisper-models/ggml-small.bin")
YT_DLP = "/opt/homebrew/bin/yt-dlp"
FFMPEG = "/opt/homebrew/bin/ffmpeg"

WORK_DIR = Path("/tmp/crece-whisper")


def get_posts_without_text(conn, limit=None, platform=None):
    """Get posts with no content that we can try to transcribe."""
    cur = conn.cursor()
    query = """
        SELECT p.id, p.platform_post_id, sp.handle, sp.platform
        FROM social_posts p
        JOIN social_profiles sp ON p.profile_id = sp.id
        WHERE (p.content IS NULL OR p.content = '')
    """
    params = []
    if platform:
        query += " AND sp.platform = %s"
        params.append(platform)
    query += " ORDER BY sp.platform, p.id"
    if limit:
        query += f" LIMIT {int(limit)}"
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def build_url(platform, handle, post_id):
    """Reconstruct video URL from platform + handle + post_id."""
    handle_clean = handle.lstrip("@")
    if platform == "TIKTOK":
        return f"https://www.tiktok.com/@{handle_clean}/video/{post_id}"
    elif platform == "INSTAGRAM":
        return f"https://www.instagram.com/reel/{post_id}/"
    elif platform == "FACEBOOK":
        return f"https://www.facebook.com/{handle_clean}/videos/{post_id}/"
    return None


def download_audio(url, out_dir):
    """Download audio from video URL using yt-dlp. Returns path to audio file."""
    out_template = str(out_dir / "audio.%(ext)s")
    cmd = [
        YT_DLP,
        "-x",  # extract audio
        "--audio-format", "mp3",
        "--audio-quality", "5",  # medium quality, faster
        "-o", out_template,
        "--no-playlist",
        "--socket-timeout", "30",
        "--retries", "2",
        url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return None, result.stderr[:200]

        # Find the output file
        for f in out_dir.iterdir():
            if f.suffix in (".mp3", ".m4a", ".wav", ".opus", ".webm"):
                return f, None
        return None, "No audio file found after download"
    except subprocess.TimeoutExpired:
        return None, "Download timed out (120s)"
    except Exception as e:
        return None, str(e)


def convert_to_wav(audio_path, out_dir):
    """Convert audio to 16kHz mono WAV for whisper."""
    wav_path = out_dir / "audio.wav"
    cmd = [
        FFMPEG, "-y", "-i", str(audio_path),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
        str(wav_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return None
    return wav_path


def transcribe(wav_path):
    """Transcribe WAV using whisper-cli. Returns text."""
    cmd = [
        WHISPER_CLI,
        "-m", WHISPER_MODEL,
        "-l", "es",  # Spanish
        "--no-timestamps",
        "-f", str(wav_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return None, result.stderr[:200]

        text = result.stdout.strip()
        # Clean whisper artifacts
        text = re.sub(r'\[.*?\]', '', text)  # Remove [MUSIC], [BLANK_AUDIO] etc
        text = re.sub(r'\(.*?\)', '', text)  # Remove (inaudible) etc
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) < 5:
            return None, "Transcription too short (likely no speech)"
        return text, None
    except subprocess.TimeoutExpired:
        return None, "Whisper timed out (300s)"
    except Exception as e:
        return None, str(e)


def update_post_content(conn, post_id, content):
    """Update social_posts.content with transcription."""
    cur = conn.cursor()
    cur.execute(
        """UPDATE social_posts
           SET content = %s,
               raw_data = COALESCE(raw_data, '{}'::jsonb) || '{"transcribed": true}'::jsonb
           WHERE id = %s""",
        (content, post_id),
    )
    conn.commit()
    cur.close()


def mark_needs_ocr(conn, post_id):
    """Mark a post as needing OCR (no speech detected by whisper)."""
    cur = conn.cursor()
    cur.execute(
        """UPDATE social_posts
           SET raw_data = COALESCE(raw_data, '{}'::jsonb) || '{"needs_ocr": true, "whisper_tried": true}'::jsonb
           WHERE id = %s""",
        (post_id,),
    )
    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser(description="Whisper pipeline for posts without text")
    parser.add_argument("--limit", type=int, help="Max posts to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't update DB")
    parser.add_argument("--platform", choices=["TIKTOK", "FACEBOOK", "INSTAGRAM"], help="Filter by platform")
    args = parser.parse_args()

    WORK_DIR.mkdir(exist_ok=True)

    conn = psycopg2.connect(DB_URL)
    posts = get_posts_without_text(conn, args.limit, args.platform)

    print(f"Found {len(posts)} posts without text")
    if not posts:
        return

    stats = {"success": 0, "download_fail": 0, "transcribe_fail": 0, "no_speech": 0}
    no_speech_ids = []

    for i, (post_id, platform_post_id, handle, platform) in enumerate(posts):
        url = build_url(platform, handle, platform_post_id)
        if not url:
            print(f"  [{i+1}/{len(posts)}] #{post_id} — Can't build URL for {platform}")
            continue

        print(f"  [{i+1}/{len(posts)}] #{post_id} {platform} {handle} — ", end="", flush=True)

        # Create temp dir for this post
        post_dir = WORK_DIR / str(post_id)
        post_dir.mkdir(exist_ok=True)

        # Clean previous files
        for f in post_dir.iterdir():
            f.unlink()

        # Download
        audio_path, err = download_audio(url, post_dir)
        if not audio_path:
            print(f"download fail: {err}")
            stats["download_fail"] += 1
            continue

        # Convert to WAV
        wav_path = convert_to_wav(audio_path, post_dir)
        if not wav_path:
            print("ffmpeg convert fail")
            stats["download_fail"] += 1
            continue

        # Transcribe
        text, err = transcribe(wav_path)
        if not text:
            print(f"no speech: {err}")
            stats["no_speech"] += 1
            no_speech_ids.append(post_id)
            # Mark as needs_ocr in DB
            if not args.dry_run:
                mark_needs_ocr(conn, post_id)
            continue

        print(f"OK ({len(text)} chars): {text[:80]}...")
        stats["success"] += 1

        if not args.dry_run:
            update_post_content(conn, post_id, text)

        # Cleanup audio files to save disk
        for f in post_dir.iterdir():
            f.unlink()

    conn.close()

    print("\n=== Results ===")
    print(f"  Success:        {stats['success']}")
    print(f"  Download fail:  {stats['download_fail']}")
    print(f"  No speech:      {stats['no_speech']}")
    print(f"  Total:          {len(posts)}")

    if no_speech_ids:
        print(f"\n  No-speech post IDs (candidates for OCR): {no_speech_ids[:20]}{'...' if len(no_speech_ids) > 20 else ''}")

    if stats["success"] > 0 and not args.dry_run:
        print(f"\n{stats['success']} posts updated with transcriptions.")
        print("Run NLP sentiment analysis next:")
        print("  docker exec crece-backend python -m app.nlp.batch_sentiment --empty-only")


if __name__ == "__main__":
    main()
