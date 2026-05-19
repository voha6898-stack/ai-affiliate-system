"""
Static Site Generator — tao HTML tu SQLite DB, deploy len GitHub Pages.
Chay sau moi lan AI viet bai moi.
GitHub Pages: https://voha6898-stack.github.io/ai-affiliate-system/
"""
import os
import sqlite3
import re
from datetime import datetime

DB_PATH = "data/affiliate_ai.db"
OUT_DIR = "docs"
SITE_NAME = "AI Affiliate Reviews"
SITE_URL = "https://voha6898-stack.github.io/ai-affiliate-system"


def get_articles():
    if not os.path.exists(DB_PATH):
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # JOIN keywords to always get niche even for old articles without niche column
    rows = conn.execute(
        """SELECT a.id, a.keyword_id, a.title, a.slug, a.content, a.word_count,
                  a.affiliate_links_count, a.status, a.seo_score,
                  a.published_at, a.updated_at, a.created_at,
                  COALESCE(NULLIF(a.niche,''), k.niche, '') as niche,
                  COALESCE(NULLIF(a.meta_description,''), '') as meta_description
           FROM articles a
           LEFT JOIN keywords k ON a.keyword_id = k.id
           WHERE a.status='published'
           ORDER BY a.published_at DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def safe(text):
    if not text:
        return ""
    return str(text).replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')


def write(path, html):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


# ── CSS shared ──────────────────────────────────────────────────────────────
CSS = """
<style>
:root{--bg:#0f172a;--card:#1e293b;--border:#334155;--primary:#6366f1;--text:#e2e8f0;--muted:#94a3b8}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);line-height:1.7}
a{color:var(--primary);text-decoration:none}
a:hover{text-decoration:underline}
header{background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:16px 32px;position:sticky;top:0;z-index:100}
.nav{max-width:1200px;margin:0 auto;display:flex;justify-content:space-between;align-items:center}
.logo{font-size:20px;font-weight:800;color:white}
.nav-links a{color:rgba(255,255,255,.8);margin-left:24px;font-size:14px}
footer{background:var(--card);border-top:1px solid var(--border);padding:24px;text-align:center;color:var(--muted);font-size:13px;margin-top:60px}
</style>
"""

NAV = f"""
<header>
  <div class="nav">
    <a href="{SITE_URL}/" class="logo">{SITE_NAME}</a>
    <div class="nav-links">
      <a href="{SITE_URL}/">Home</a>
      <a href="{SITE_URL}/sitemap.xml">Sitemap</a>
    </div>
  </div>
</header>
"""

FOOTER = f"""
<footer>
  <p>&copy; 2026 {SITE_NAME}. All rights reserved.</p>
  <p>This site contains affiliate links. We may earn a commission when you click and make a purchase.</p>
</footer>
"""


# ── Homepage ─────────────────────────────────────────────────────────────────
def build_index(articles):
    cards = ""
    for a in articles:
        url = f"{SITE_URL}/article/{a['slug']}/"
        desc = (a.get("meta_description") or "")[:120]
        date = (a.get("published_at") or "")[:10]
        niche = a.get("niche", "")
        niche_badge = f'<div style="font-size:11px;font-weight:700;color:var(--primary);text-transform:uppercase;background:rgba(99,102,241,.15);display:inline-block;padding:3px 10px;border-radius:20px;margin-bottom:10px">{safe(niche)}</div>' if niche else ""
        cards += f"""
        <div style="background:var(--card);border:1px solid var(--border);border-radius:16px;padding:24px;transition:transform .2s,border-color .2s" onmouseover="this.style.transform='translateY(-4px)';this.style.borderColor='var(--primary)'" onmouseout="this.style.transform='';this.style.borderColor='var(--border)'">
          {niche_badge}
          <h2 style="font-size:17px;font-weight:700;margin-bottom:10px;line-height:1.4"><a href="{url}" style="color:var(--text)">{safe(a['title'])}</a></h2>
          <p style="font-size:14px;color:var(--muted);margin-bottom:16px">{safe(desc)}{'...' if len(desc)==120 else ''}</p>
          <div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted)">
            <span>{a.get('word_count',0):,} words &bull; {date}</span>
            <a href="{url}" style="background:var(--primary);color:white;padding:6px 16px;border-radius:8px;font-size:13px;font-weight:500">Read More</a>
          </div>
        </div>"""

    empty = '<div style="text-align:center;padding:80px;color:var(--muted)"><h3>No articles yet</h3><p>Check back soon — AI is generating content daily.</p></div>' if not articles else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{SITE_NAME} — Expert Reviews & Buying Guides 2026</title>
<meta name="description" content="AI-powered expert reviews, comparisons and buying guides. Find the best products in 2026.">
<link rel="canonical" href="{SITE_URL}/">
{CSS}
</head>
<body>
{NAV}
<div style="background:linear-gradient(135deg,#1e1b4b,#312e81);padding:60px 24px;text-align:center">
  <h1 style="font-size:36px;font-weight:800;margin-bottom:12px;background:linear-gradient(135deg,#a5b4fc,#e879f9);-webkit-background-clip:text;-webkit-text-fill-color:transparent">Expert Reviews &amp; Buying Guides</h1>
  <p style="font-size:18px;color:var(--muted);max-width:600px;margin:0 auto">AI-powered research to help you find the best products in 2026</p>
</div>
<div style="max-width:1200px;margin:0 auto;padding:48px 24px">
  <div style="font-size:22px;font-weight:700;margin-bottom:24px;display:flex;align-items:center;gap:10px">
    Latest Articles ({len(articles)})
    <span style="flex:1;height:1px;background:var(--border);display:block"></span>
  </div>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:24px">
    {cards}
  </div>
  {empty}
</div>
{FOOTER}
</body>
</html>"""
    write(f"{OUT_DIR}/index.html", html)


# ── Article page ──────────────────────────────────────────────────────────────
_all_articles: list = []  # populated by main() for related articles lookup


def build_article(a):
    slug = a["slug"]
    url = f"{SITE_URL}/article/{slug}/"
    niche = a.get("niche", "")
    date = (a.get("published_at") or "")[:10]
    updated = (a.get("updated_at") or date)[:10]

    schema = f"""<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"Article",
"headline":"{safe(a['title'])}",
"description":"{safe(a.get('meta_description',''))}",
"datePublished":"{date}","dateModified":"{updated}",
"author":{{"@type":"Organization","name":"{SITE_NAME}"}},
"publisher":{{"@type":"Organization","name":"{SITE_NAME}"}},
"mainEntityOfPage":{{"@type":"WebPage","@id":"{url}"}}}}
</script>
<script type="application/ld+json">
{{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},
{{"@type":"ListItem","position":2,"name":"{safe(niche.title())}","item":"{SITE_URL}/niche/{niche}/"}},
{{"@type":"ListItem","position":3,"name":"{safe(a['title'][:60])}"}}
]}}
</script>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe(a['title'])} | {SITE_NAME}</title>
<meta name="description" content="{safe(a.get('meta_description',''))}">
<meta property="og:title" content="{safe(a['title'])}">
<meta property="og:description" content="{safe(a.get('meta_description',''))}">
<meta property="og:type" content="article">
<link rel="canonical" href="{url}">
{schema}
{CSS}
<style>
.container{{max-width:800px;margin:0 auto;padding:40px 24px 80px}}
.article-content{{font-size:16px;line-height:1.8}}
.article-content h1,.article-content h2{{font-size:24px;font-weight:700;margin:40px 0 16px;border-bottom:1px solid var(--border);padding-bottom:8px}}
.article-content h3{{font-size:19px;font-weight:600;margin:28px 0 12px}}
.article-content p{{margin-bottom:16px;color:#cbd5e1}}
.article-content ul,.article-content ol{{margin:16px 0 16px 24px}}
.article-content li{{margin-bottom:8px;color:#cbd5e1}}
.article-content blockquote,.article-content .quick-answer{{background:rgba(99,102,241,.1);border-left:4px solid var(--primary);padding:16px 20px;border-radius:0 8px 8px 0;margin:24px 0;color:#a5b4fc}}
.article-content table{{width:100%;border-collapse:collapse;margin:24px 0;font-size:14px}}
.article-content th{{background:var(--card);padding:10px 14px;text-align:left;border:1px solid var(--border);font-weight:600;color:var(--primary)}}
.article-content td{{padding:10px 14px;border:1px solid var(--border);color:#cbd5e1}}
.article-content tr:nth-child(even) td{{background:rgba(255,255,255,.03)}}
.article-content .faq-item{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px 20px;margin-bottom:12px}}
.article-content a.affiliate-link{{background:rgba(99,102,241,.15);border:1px solid rgba(99,102,241,.3);padding:2px 10px;border-radius:6px;font-weight:500;color:#a5b4fc}}
.article-content a.affiliate-link:hover{{background:rgba(99,102,241,.3)}}
</style>
</head>
<body>
{NAV}
<div class="container">
  <div style="font-size:13px;color:var(--muted);margin-bottom:24px">
    <a href="{SITE_URL}/" style="color:var(--muted)">Home</a> &rsaquo;
    {'<a href="' + SITE_URL + '/niche/' + niche + '/" style="color:var(--muted)">' + safe(niche.title()) + '</a> &rsaquo;' if niche else ''}
    {safe(a['title'][:50])}...
  </div>
  <div style="margin-bottom:32px">
    {'<div style="font-size:12px;font-weight:600;color:var(--primary);text-transform:uppercase;background:rgba(99,102,241,.15);display:inline-block;padding:4px 12px;border-radius:20px;margin-bottom:16px">' + safe(niche) + '</div>' if niche else ''}
    <h1 style="font-size:32px;font-weight:800;line-height:1.3;margin-bottom:16px">{safe(a['title'])}</h1>
    <div style="font-size:14px;color:var(--muted);display:flex;gap:16px;flex-wrap:wrap">
      <span>{date}</span>
      <span>{a.get('word_count',0):,} words</span>
      <span>{a.get('affiliate_links_count',0)} product links</span>
    </div>
  </div>
  <div class="article-content">
    {a.get('content','')}
  </div>
  <div style="background:linear-gradient(135deg,rgba(99,102,241,.2),rgba(139,92,246,.2));border:1px solid rgba(99,102,241,.3);border-radius:12px;padding:24px;margin:32px 0;text-align:center">
    <h3 style="font-size:18px;margin-bottom:8px">Found this helpful?</h3>
    <p style="font-size:14px;color:var(--muted);margin-bottom:16px">Explore more expert reviews on our site.</p>
    <a href="{SITE_URL}/" style="background:var(--primary);color:white;padding:10px 24px;border-radius:8px;display:inline-block;font-weight:600">Browse All Guides</a>
  </div>
  {_build_related(a)}
</div>
{FOOTER}
</body>
</html>"""
    write(f"{OUT_DIR}/article/{slug}/index.html", html)


def _build_related(current):
    """3 related articles from same niche (or random if not enough)."""
    niche = current.get("niche", "")
    others = [x for x in _all_articles if x["slug"] != current["slug"]]
    same = [x for x in others if x.get("niche") == niche]
    picks = (same + others)[:3]
    if not picks:
        return ""
    cards = ""
    for r in picks:
        rurl = f"{SITE_URL}/article/{r['slug']}/"
        cards += (
            f'<a href="{rurl}" style="background:var(--card);border:1px solid var(--border);'
            f'border-radius:10px;padding:16px;display:block;color:var(--text);text-decoration:none">'
            f'<div style="font-size:11px;color:var(--primary);font-weight:600;text-transform:uppercase;margin-bottom:6px">'
            f'{safe(r.get("niche","").title())}</div>'
            f'<div style="font-size:14px;font-weight:600;line-height:1.4">{safe(r["title"])}</div>'
            f'</a>'
        )
    return (
        f'<div style="margin-top:48px"><h3 style="font-size:18px;font-weight:700;margin-bottom:16px">'
        f'Related Articles</h3>'
        f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px">'
        f'{cards}</div></div>'
    )


# ── Niche page ────────────────────────────────────────────────────────────────
def build_niche(niche, articles):
    cards = ""
    for a in articles:
        url = f"{SITE_URL}/article/{a['slug']}/"
        desc = (a.get("meta_description") or "")[:100]
        date = (a.get("published_at") or "")[:10]
        cards += f'<div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px"><h2 style="font-size:16px;margin-bottom:8px"><a href="{url}" style="color:var(--text)">{safe(a["title"])}</a></h2><p style="font-size:13px;color:var(--muted);margin-bottom:12px">{safe(desc)}</p><div style="font-size:12px;color:var(--muted)">{date} &bull; {a.get("word_count",0):,} words</div></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe(niche.title())} Reviews | {SITE_NAME}</title>
<meta name="description" content="Expert {safe(niche)} reviews and buying guides. Find the best {safe(niche)} in 2026.">
<link rel="canonical" href="{SITE_URL}/niche/{niche}/">
{CSS}
</head>
<body>
{NAV}
<div style="background:linear-gradient(135deg,#1e1b4b,#312e81);padding:40px 24px;text-align:center">
  <h1 style="font-size:28px;font-weight:800">{safe(niche.title())} Reviews</h1>
  <p style="color:var(--muted);margin-top:8px">Expert guides and comparisons — {len(articles)} articles</p>
</div>
<div style="max-width:900px;margin:0 auto;padding:40px 24px">
  <div style="display:grid;gap:16px">{cards}</div>
</div>
{FOOTER}
</body>
</html>"""
    write(f"{OUT_DIR}/niche/{niche}/index.html", html)


# ── Sitemap ───────────────────────────────────────────────────────────────────
def build_sitemap(articles):
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += f'  <url><loc>{SITE_URL}/</loc><changefreq>daily</changefreq><priority>1.0</priority></url>\n'
    for a in articles:
        updated = (a.get("updated_at") or a.get("published_at") or "")[:10]
        xml += f'  <url><loc>{SITE_URL}/article/{a["slug"]}/</loc><lastmod>{updated}</lastmod><priority>0.8</priority></url>\n'
    xml += '</urlset>'
    write(f"{OUT_DIR}/sitemap.xml", xml)


# ── robots.txt ────────────────────────────────────────────────────────────────
def build_robots():
    write(f"{OUT_DIR}/robots.txt",
          f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")


def build_nojekyll():
    open(f"{OUT_DIR}/.nojekyll", "w").close()


# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    articles = get_articles()
    print(f"Generating site: {len(articles)} articles...")

    # Populate global for related articles
    _all_articles[:] = articles

    build_index(articles)
    build_robots()
    build_nojekyll()
    build_sitemap(articles)

    niches = {}
    for a in articles:
        niche = a.get("niche", "")
        if niche:
            niches.setdefault(niche, []).append(a)
        build_article(a)

    for niche, niche_articles in niches.items():
        build_niche(niche, niche_articles)

    print(f"[OK] Site generated: {len(articles)} articles, {len(niches)} niches")
    print(f"[OK] Output: {OUT_DIR}/")
    print(f"[OK] URL: {SITE_URL}/")
