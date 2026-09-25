"""
Pinterest Auto-Poster — AI Affiliate System
Generates vertical pin images (1000×1500px) and posts via Pinterest API v5.

Setup:
  1. Create Pinterest business account → developers.pinterest.com → Create App
  2. Get access token (OAuth or test token from developer portal)
  3. Create boards in Pinterest UI for each niche
  4. Get board IDs from Pinterest API: GET /v5/boards
  5. Set GitHub Secrets:
     - PINTEREST_ACCESS_TOKEN
     - PINTEREST_DEFAULT_BOARD_ID  (one board for all if no per-niche mapping)
     - PINTEREST_BOARD_IDS         (optional JSON: {"web hosting": "123", ...})

Usage:
  python pinterest_auto.py --limit 15
  python pinterest_auto.py --limit 5 --dry-run   # generate images, skip API
  python pinterest_auto.py --list-boards           # print your boards + IDs
"""
import os
import sys
import json
import time
import base64
import logging
import textwrap
import argparse
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from utils.database import get_db, init_db

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# ─── Config ───────────────────────────────────────────────────────────────────
SITE_URL = os.getenv("SITE_URL", "https://voha6898-stack.github.io/ai-affiliate-system")
SITE_NAME = os.getenv("SITE_NAME", "AIToolReviewer.com")
PINTEREST_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN", "")
DEFAULT_BOARD_ID = os.getenv("PINTEREST_DEFAULT_BOARD_ID", "")
BOARD_IDS: dict = json.loads(os.getenv("PINTEREST_BOARD_IDS", "{}"))

PINTEREST_API = "https://api.pinterest.com/v5"
PIN_W, PIN_H = 1000, 1500

# ─── Visual themes per niche ──────────────────────────────────────────────────
NICHE_THEMES = {
    "web hosting": {
        "top": (12, 28, 36), "bot": (20, 55, 68),
        "acc": (0, 212, 170), "lbl": "WEB HOSTING",
    },
    "vpn services": {
        "top": (20, 4, 44), "bot": (40, 22, 90),
        "acc": (167, 139, 250), "lbl": "VPN SERVICES",
    },
    "email marketing tools": {
        "top": (30, 12, 0), "bot": (65, 30, 0),
        "acc": (251, 146, 60), "lbl": "EMAIL MARKETING",
    },
    "ai writing tools": {
        "top": (8, 8, 24), "bot": (25, 22, 70),
        "acc": (165, 180, 252), "lbl": "AI WRITING TOOLS",
    },
    "password managers": {
        "top": (0, 22, 8), "bot": (0, 46, 20),
        "acc": (74, 222, 128), "lbl": "PASSWORD MANAGERS",
    },
    "antivirus software": {
        "top": (28, 0, 0), "bot": (55, 8, 8),
        "acc": (252, 100, 100), "lbl": "ANTIVIRUS",
    },
    "project management software": {
        "top": (0, 22, 46), "bot": (0, 44, 90),
        "acc": (96, 165, 250), "lbl": "PROJECT MANAGEMENT",
    },
    "online courses": {
        "top": (8, 22, 0), "bot": (20, 48, 0),
        "acc": (163, 230, 53), "lbl": "ONLINE COURSES",
    },
}
_DEFAULT_THEME = {
    "top": (12, 18, 38), "bot": (26, 36, 76),
    "acc": (148, 163, 220), "lbl": "AI REVIEWS",
}

NICHE_CTA = {
    "web hosting":                  "Find the Best Hosting Deal →",
    "vpn services":                 "Compare Top VPN Prices →",
    "email marketing tools":        "See Email Marketing Reviews →",
    "ai writing tools":             "Read AI Writing Tool Reviews →",
    "password managers":            "Find Your Best Password Manager →",
    "antivirus software":           "Compare Antivirus Options Today →",
    "project management software":  "Find Your Perfect PM Tool →",
    "online courses":               "Explore Top-Rated Courses →",
}

# ─── Fonts ────────────────────────────────────────────────────────────────────
_FONT_CACHE: dict = {}

def _font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    paths = (
        [
            "assets/fonts/Inter-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
        ]
        if bold
        else [
            "assets/fonts/Inter-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
    )
    f = None
    for p in paths:
        try:
            f = ImageFont.truetype(p, size)
            break
        except (IOError, OSError):
            continue
    if f is None:
        try:
            f = ImageFont.load_default(size=size)
        except TypeError:
            f = ImageFont.load_default()
    _FONT_CACHE[key] = f
    return f


def _tw(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    """Text width — compatible across Pillow versions."""
    try:
        return int(draw.textlength(text, font=font))
    except AttributeError:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0]


# ─── Gradient background ──────────────────────────────────────────────────────
def _gradient(w: int, h: int, top: tuple, bot: tuple) -> Image.Image:
    try:
        import numpy as np
        t = np.array(top, dtype=np.float32)
        b = np.array(bot, dtype=np.float32)
        alpha = np.linspace(0, 1, h)[:, None]
        arr = (t * (1 - alpha) + b * alpha).astype(np.uint8)
        arr = np.broadcast_to(arr[:, None, :], (h, w, 3)).copy()
        return Image.fromarray(arr, "RGB")
    except ImportError:
        img = Image.new("RGB", (w, h))
        px = img.load()
        for y in range(h):
            r = int(top[0] + (bot[0] - top[0]) * y / h)
            g = int(top[1] + (bot[1] - top[1]) * y / h)
            b_ = int(top[2] + (bot[2] - top[2]) * y / h)
            for x in range(w):
                px[x, y] = (r, g, b_)
        return img


# ─── Adaptive title font size ─────────────────────────────────────────────────
def _title_font_size(char_count: int) -> int:
    if char_count <= 30:
        return 72
    if char_count <= 50:
        return 62
    if char_count <= 70:
        return 52
    return 44


# ─── Pin image generation ─────────────────────────────────────────────────────
def generate_pin(title: str, description: str, niche: str) -> bytes:
    theme = NICHE_THEMES.get(niche, _DEFAULT_THEME)
    acc = theme["acc"]

    img = _gradient(PIN_W, PIN_H, theme["top"], theme["bot"])
    draw = ImageDraw.Draw(img)

    # Subtle dot grid texture
    for x in range(0, PIN_W, 60):
        for y in range(0, PIN_H, 60):
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(*acc, 18))

    # ── Top bar ──
    badge_font = _font(22)
    badge_text = theme["lbl"]
    badge_y = 52
    bw = _tw(draw, badge_text, badge_font) + 28
    draw.rounded_rectangle([48, badge_y, 48 + bw, badge_y + 38], radius=6, fill=acc)
    draw.text((48 + 14, badge_y + 8), badge_text, font=badge_font, fill=(0, 0, 0))

    site_font = _font(22, bold=False)
    sw = _tw(draw, SITE_NAME, site_font)
    draw.text((PIN_W - sw - 48, badge_y + 8), SITE_NAME, font=site_font, fill=(*acc, 200))

    # ── Stars ──
    star_font = _font(52)
    stars = "★★★★★"
    sw = _tw(draw, stars, star_font)
    draw.text(((PIN_W - sw) // 2, 185), stars, font=star_font, fill=acc)

    # ── Title ──
    fs = _title_font_size(len(title))
    title_font = _font(fs)
    chars_per_line = max(16, int(PIN_W * 0.78 / (fs * 0.55)))
    lines = textwrap.wrap(title, width=chars_per_line)[:5]
    line_h = int(fs * 1.22)
    title_y = 295

    for i, line in enumerate(lines):
        lw = _tw(draw, line, title_font)
        x = (PIN_W - lw) // 2
        y = title_y + i * line_h
        draw.text((x + 2, y + 2), line, font=title_font, fill=(0, 0, 0, 70))
        draw.text((x, y), line, font=title_font, fill=(255, 255, 255))

    # ── Divider ──
    div_y = title_y + len(lines) * line_h + 48
    draw.rectangle([48, div_y, PIN_W - 48, div_y + 4], fill=acc)
    draw.rectangle([48, div_y + 8, PIN_W - 48, div_y + 10], fill=(*acc, 60))

    # ── Description ──
    desc = (description or title)[:220]
    desc_font = _font(32, bold=False)
    desc_lines = textwrap.wrap(desc, width=34)[:4]
    desc_y = div_y + 38
    for i, line in enumerate(desc_lines):
        lw = _tw(draw, line, desc_font)
        draw.text(((PIN_W - lw) // 2, desc_y + i * 46), line, font=desc_font, fill=(200, 212, 228))

    # ── CTA pill ──
    cta_text = NICHE_CTA.get(niche, "Read Full Review →")
    cta_font = _font(34)
    cta_y = desc_y + len(desc_lines) * 46 + 58
    cw = _tw(draw, cta_text, cta_font)
    pad = 28
    pill_x0 = (PIN_W - cw) // 2 - pad
    pill_x1 = (PIN_W + cw) // 2 + pad
    draw.rounded_rectangle([pill_x0, cta_y - 12, pill_x1, cta_y + 48], radius=36, fill=acc)
    draw.text(((PIN_W - cw) // 2, cta_y), cta_text, font=cta_font, fill=(0, 0, 0))

    # ── Bottom accent bar ──
    draw.rectangle([0, PIN_H - 14, PIN_W, PIN_H], fill=acc)

    buf = BytesIO()
    img.save(buf, "JPEG", quality=88, optimize=True)
    return buf.getvalue()


# ─── Pinterest API ────────────────────────────────────────────────────────────
def _headers() -> dict:
    return {
        "Authorization": f"Bearer {PINTEREST_TOKEN}",
        "Content-Type": "application/json",
    }


def list_boards() -> list:
    resp = requests.get(f"{PINTEREST_API}/boards", headers=_headers(), timeout=30)
    resp.raise_for_status()
    return resp.json().get("items", [])


def post_pin(title: str, description: str, link: str, image_bytes: bytes, board_id: str) -> dict:
    payload = {
        "board_id": board_id,
        "title": title[:100],
        "description": description[:500],
        "link": link,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/jpeg",
            "data": base64.b64encode(image_bytes).decode(),
        },
    }
    resp = requests.post(f"{PINTEREST_API}/pins", headers=_headers(), json=payload, timeout=60)
    if not resp.ok:
        logger.error(f"Pinterest API {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    return resp.json()


# ─── Database ─────────────────────────────────────────────────────────────────
def _init_pins_table():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pinterest_pins (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL UNIQUE,
                pin_id     TEXT,
                board_id   TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def _get_unpinned(limit: int) -> list:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.id, a.title, a.slug, a.niche, a.meta_description
            FROM articles a
            LEFT JOIN pinterest_pins pp ON pp.article_id = a.id
            WHERE a.status = 'published' AND pp.id IS NULL
            ORDER BY
                CASE a.niche
                    WHEN 'web hosting'                 THEN 1
                    WHEN 'vpn services'                THEN 2
                    WHEN 'email marketing tools'       THEN 3
                    WHEN 'ai writing tools'            THEN 4
                    WHEN 'password managers'           THEN 5
                    WHEN 'antivirus software'          THEN 6
                    WHEN 'project management software' THEN 7
                    ELSE 8
                END,
                a.created_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
    return [dict(r) for r in rows]


def _mark_pinned(article_id: int, pin_id: str, board_id: str):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO pinterest_pins (article_id, pin_id, board_id) VALUES (?,?,?)",
            (article_id, pin_id, board_id),
        )
        conn.commit()


def _board_for(niche: str) -> str:
    return BOARD_IDS.get(niche, DEFAULT_BOARD_ID)


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Post affiliate articles to Pinterest")
    ap.add_argument("--limit", type=int, default=15, help="Max pins per run (default 15)")
    ap.add_argument("--dry-run", action="store_true", help="Generate images, skip API calls")
    ap.add_argument("--list-boards", action="store_true", help="Print Pinterest boards and exit")
    ap.add_argument("--save-images", action="store_true", help="Save images to docs/pins/")
    args = ap.parse_args()

    if not PINTEREST_TOKEN:
        if args.dry_run or args.list_boards:
            logger.warning("No PINTEREST_ACCESS_TOKEN — running dry-run mode")
        else:
            logger.error(
                "PINTEREST_ACCESS_TOKEN not set.\n"
                "  1. Go to developers.pinterest.com\n"
                "  2. Create an app → get access token\n"
                "  3. Add token as GitHub Secret PINTEREST_ACCESS_TOKEN"
            )
            sys.exit(1)

    if args.list_boards:
        print("\nYour Pinterest boards:")
        for b in list_boards():
            print(f"  {b['id']}  {b['name']}")
        print("\nSet PINTEREST_BOARD_IDS JSON:")
        print('  {"web hosting": "<id>", "vpn services": "<id>", ...}')
        return

    init_db()
    _init_pins_table()

    if args.save_images:
        Path("docs/pins").mkdir(parents=True, exist_ok=True)

    articles = _get_unpinned(args.limit)
    if not articles:
        logger.info("All articles already pinned.")
        return

    logger.info(f"Posting {len(articles)} pins to Pinterest...")
    posted = 0

    for art in articles:
        title = art["title"]
        slug = art["slug"]
        niche = (art["niche"] or "").lower()
        desc = art["meta_description"] or title
        link = f"{SITE_URL}/article/{slug}/"
        board_id = _board_for(niche)

        if not board_id and not args.dry_run:
            logger.warning(f"No board for niche '{niche}' — skipping: {title[:55]}")
            continue

        try:
            logger.info(f"  Generating: {title[:65]}")
            image_bytes = generate_pin(title, desc, niche)
            size_kb = len(image_bytes) // 1024

            if args.save_images:
                p = Path("docs/pins") / f"{slug[:80]}.jpg"
                p.write_bytes(image_bytes)

            if args.dry_run:
                logger.info(f"  [DRY RUN] {size_kb}KB — {link}")
                posted += 1
                continue

            pin = post_pin(title, desc, link, image_bytes, board_id)
            pin_id = pin.get("id", "")
            _mark_pinned(art["id"], pin_id, board_id)
            posted += 1
            logger.info(f"  [OK] pin={pin_id} niche={niche} {size_kb}KB")

            time.sleep(1.5)  # stay within Pinterest rate limits

        except Exception as exc:
            logger.error(f"  [!!] Failed '{title[:50]}': {exc}")
            time.sleep(5)

    logger.info(f"\nDone: {posted}/{len(articles)} pins posted")


if __name__ == "__main__":
    main()
