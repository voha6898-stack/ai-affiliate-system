"""
AI Affiliate System — Local Dashboard
Mo trinh duyet tai: http://localhost:5050
Hien thi: pipeline, bai viet, tien kiem duoc, trang thai he thong
"""
import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, jsonify
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

DB_PATH = "data/affiliate_ai.db"
BLOG_URL = os.getenv("BLOG_URL", "")
PORT = 5050


def get_stats():
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    articles = conn.execute(
        "SELECT * FROM articles WHERE status='published' ORDER BY published_at DESC"
    ).fetchall()
    articles = [dict(r) for r in articles]

    keywords_pending = conn.execute(
        "SELECT COUNT(*) as n FROM keywords WHERE status='pending'"
    ).fetchone()["n"]
    keywords_total = conn.execute(
        "SELECT COUNT(*) as n FROM keywords"
    ).fetchone()["n"]
    keywords_published = conn.execute(
        "SELECT COUNT(*) as n FROM keywords WHERE status='published'"
    ).fetchone()["n"]

    perf = conn.execute(
        "SELECT SUM(revenue) as rev, SUM(conversions) as conv, "
        "SUM(affiliate_clicks) as aff_clicks, SUM(organic_clicks) as org_clicks "
        "FROM performance"
    ).fetchone()

    products = conn.execute(
        "SELECT * FROM affiliate_products WHERE active=1 ORDER BY revenue DESC LIMIT 10"
    ).fetchall()
    products = [dict(r) for r in products]

    conn.close()

    avg_seo = sum(a.get("seo_score", 0) for a in articles) / len(articles) if articles else 0
    total_words = sum(a.get("word_count", 0) for a in articles)
    total_links = sum(a.get("affiliate_links_count", 0) for a in articles)

    return {
        "articles": articles,
        "keywords_pending": keywords_pending,
        "keywords_total": keywords_total,
        "keywords_published": keywords_published,
        "total_articles": len(articles),
        "avg_seo": round(avg_seo, 1),
        "total_words": total_words,
        "total_links": total_links,
        "revenue": round(float(perf["rev"] or 0), 2),
        "conversions": int(perf["conv"] or 0),
        "affiliate_clicks": int(perf["aff_clicks"] or 0),
        "organic_clicks": int(perf["org_clicks"] or 0),
        "products": products,
    }


def check_ai_provider():
    if os.getenv("GROQ_API_KEY"):
        return "GROQ"
    if os.getenv("GEMINI_API_KEY"):
        return "GEMINI"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "CLAUDE"
    return "UNKNOWN"


def check_blog_async():
    """Kiem tra blog trong background thread, khong block main thread."""
    if not BLOG_URL or BLOG_URL == "http://localhost:5000":
        return "NOT SET", {}
    try:
        import requests
        r = requests.get(f"{BLOG_URL}/api/stats", timeout=3)
        if r.status_code == 200:
            return "ONLINE", r.json()
        return "ERROR", {}
    except Exception:
        return "SLEEPING", {}


def render_html(stats, blog_status="UNKNOWN", blog_stats=None):
    if blog_stats is None:
        blog_stats = {}
    provider = check_ai_provider()
    blog_articles = blog_stats.get("total_articles", 0) or 0

    articles_html = ""
    for a in stats.get("articles", [])[:20]:
        url = a.get("wp_url", "")
        live_link = f'<a href="{url}" target="_blank" style="color:#6366f1">Xem</a>' if url and url.startswith("http") else '<span style="color:#475569">Local</span>'
        pub_date = (a.get("published_at") or "")[:10]
        seo = a.get("seo_score", 0)
        seo_color = "#22c55e" if seo >= 70 else "#f59e0b" if seo >= 50 else "#ef4444"
        articles_html += f"""
        <tr>
          <td style="padding:10px 8px;color:#e2e8f0;font-size:13px">{a.get('title','')[:60]}</td>
          <td style="padding:10px 8px;color:#94a3b8;font-size:12px">{a.get('niche','')}</td>
          <td style="padding:10px 8px;color:#94a3b8;font-size:12px">{a.get('word_count',0):,}</td>
          <td style="padding:10px 8px;font-size:12px"><span style="color:{seo_color};font-weight:700">{seo}/100</span></td>
          <td style="padding:10px 8px;color:#94a3b8;font-size:12px">{a.get('affiliate_links_count',0)}</td>
          <td style="padding:10px 8px;font-size:12px">{pub_date}</td>
          <td style="padding:10px 8px;font-size:12px">{live_link}</td>
        </tr>"""

    if not articles_html:
        articles_html = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#475569">Chua co bai viet nao. Chay: python main.py publish 1</td></tr>'

    products_html = ""
    for p in stats.get("products", [])[:5]:
        products_html += f"""
        <tr>
          <td style="padding:8px;color:#e2e8f0;font-size:13px">{p.get('name','')[:40]}</td>
          <td style="padding:8px;color:#6366f1;font-size:12px;font-weight:600">{p.get('platform','').upper()}</td>
          <td style="padding:8px;color:#22c55e;font-size:12px">{p.get('commission_rate',0):.0f}%</td>
          <td style="padding:8px;color:#f59e0b;font-size:12px">${p.get('avg_price',0):.0f}</td>
          <td style="padding:8px;color:#94a3b8;font-size:12px">{p.get('clicks',0)}</td>
          <td style="padding:8px;color:#22c55e;font-size:12px">${p.get('revenue',0):.2f}</td>
        </tr>"""
    if not products_html:
        products_html = '<tr><td colspan="6" style="text-align:center;padding:20px;color:#475569">Chua co san pham nao trong database</td></tr>'

    blog_status_color = "#22c55e" if blog_status == "ONLINE" else "#ef4444"
    ai_color = "#22c55e" if provider not in ("UNKNOWN",) else "#ef4444"

    revenue = stats.get("revenue", 0)
    rev_color = "#22c55e" if revenue > 0 else "#475569"

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Affiliate Dashboard</title>
<meta http-equiv="refresh" content="30">
<style>
  :root{{--bg:#0f172a;--card:#1e293b;--border:#334155;--primary:#6366f1;--text:#e2e8f0;--muted:#94a3b8}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
  a{{color:var(--primary)}}

  .topbar{{background:linear-gradient(135deg,#312e81,#4c1d95);padding:16px 32px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border)}}
  .topbar h1{{font-size:20px;font-weight:800}}
  .topbar .sub{{font-size:13px;color:#a5b4fc;margin-top:2px}}
  .refresh-note{{font-size:11px;color:#7c3aed;background:rgba(124,58,237,.15);padding:4px 10px;border-radius:20px}}

  .main{{max-width:1400px;margin:0 auto;padding:24px 24px 60px}}

  /* STATUS BAR */
  .status-bar{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
  .status-item{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-size:13px;display:flex;align-items:center;gap:8px}}
  .dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}

  /* STAT CARDS */
  .cards{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-bottom:28px}}
  .card{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px}}
  .card .label{{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px}}
  .card .value{{font-size:28px;font-weight:800;line-height:1}}
  .card .sub{{font-size:12px;color:var(--muted);margin-top:6px}}

  /* PIPELINE */
  .pipeline{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:28px}}
  .pipeline h2{{font-size:16px;font-weight:700;margin-bottom:20px;color:#a5b4fc}}
  .pipeline-flow{{display:flex;align-items:center;gap:0;flex-wrap:wrap;gap:8px}}
  .step{{background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.3);border-radius:10px;padding:14px 18px;text-align:center;min-width:140px;flex:1}}
  .step .num{{font-size:11px;color:#6366f1;font-weight:700;text-transform:uppercase;letter-spacing:.06em}}
  .step .name{{font-size:15px;font-weight:700;margin:6px 0 4px}}
  .step .desc{{font-size:11px;color:var(--muted);line-height:1.4}}
  .arrow{{color:#475569;font-size:20px;flex-shrink:0}}

  /* HOW MONEY WORKS */
  .money-flow{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:28px}}
  .money-flow h2{{font-size:16px;font-weight:700;margin-bottom:16px;color:#22c55e}}
  .money-steps{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}}
  .money-step{{background:rgba(34,197,94,.07);border:1px solid rgba(34,197,94,.2);border-radius:10px;padding:14px}}
  .money-step .ms-num{{font-size:11px;color:#22c55e;font-weight:700;margin-bottom:6px}}
  .money-step .ms-title{{font-size:14px;font-weight:700;margin-bottom:4px}}
  .money-step .ms-desc{{font-size:12px;color:var(--muted);line-height:1.5}}
  .money-example{{margin-top:16px;background:rgba(245,158,11,.07);border:1px solid rgba(245,158,11,.2);border-radius:10px;padding:14px}}
  .money-example h3{{font-size:13px;color:#f59e0b;margin-bottom:8px}}
  .money-example p{{font-size:12px;color:var(--muted);line-height:1.7}}
  .money-example strong{{color:#e2e8f0}}

  /* TABLES */
  .section{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:24px}}
  .section h2{{font-size:16px;font-weight:700;margin-bottom:16px}}
  table{{width:100%;border-collapse:collapse}}
  th{{text-align:left;padding:8px;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);border-bottom:1px solid var(--border)}}
  tr:hover td{{background:rgba(255,255,255,.02)}}

  /* COMMANDS */
  .commands{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:24px;margin-bottom:24px}}
  .commands h2{{font-size:16px;font-weight:700;margin-bottom:16px;color:#f59e0b}}
  .cmd-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}}
  .cmd-item{{background:rgba(15,23,42,.6);border:1px solid var(--border);border-radius:8px;padding:12px}}
  .cmd-item code{{font-family:monospace;font-size:13px;color:#a5b4fc;display:block;margin-bottom:4px}}
  .cmd-item .cmd-desc{{font-size:12px;color:var(--muted)}}

  @media(max-width:768px){{
    .pipeline-flow{{flex-direction:column}}
    .arrow{{transform:rotate(90deg)}}
  }}
</style>
</head>
<body>

<div class="topbar">
  <div>
    <h1>AI Affiliate System — Dashboard</h1>
    <div class="sub">Theo doi toan bo quy trinh tu dong kiem tien online</div>
  </div>
  <div class="refresh-note">Tu dong cap nhat moi 30 giay</div>
</div>

<div class="main">

  <!-- STATUS BAR -->
  <div class="status-bar">
    <div class="status-item">
      <div class="dot" style="background:{ai_color}"></div>
      <span>AI Provider: <strong>{provider}</strong></span>
    </div>
    <div class="status-item">
      <div class="dot" style="background:{blog_status_color}"></div>
      <span>Blog: <strong>{blog_status}</strong>
        {f'&nbsp;—&nbsp;<a href="{BLOG_URL}" target="_blank">{BLOG_URL}</a>' if BLOG_URL else ''}
      </span>
    </div>
    <div class="status-item">
      <div class="dot" style="background:#22c55e"></div>
      <span>Bai tren Render: <strong>{blog_articles}</strong></span>
    </div>
    <div class="status-item">
      <div class="dot" style="background:#f59e0b"></div>
      <span>Keywords cho: <strong>{stats.get('keywords_pending', 0)}</strong></span>
    </div>
    <div class="status-item" style="margin-left:auto">
      <span style="color:#475569;font-size:12px">Cap nhat: {datetime.now().strftime('%H:%M:%S')}</span>
    </div>
  </div>

  <!-- STAT CARDS -->
  <div class="cards">
    <div class="card">
      <div class="label">Bai da dang</div>
      <div class="value" style="color:#6366f1">{stats.get('total_articles', 0)}</div>
      <div class="sub">{stats.get('keywords_published', 0)} keywords da xu ly</div>
    </div>
    <div class="card">
      <div class="label">Doanh thu</div>
      <div class="value" style="color:{rev_color}">${stats.get('revenue', 0):.2f}</div>
      <div class="sub">{stats.get('conversions', 0)} don hang</div>
    </div>
    <div class="card">
      <div class="label">Luot click affiliate</div>
      <div class="value" style="color:#f59e0b">{stats.get('affiliate_clicks', 0):,}</div>
      <div class="sub">{stats.get('organic_clicks', 0):,} luot doc bai</div>
    </div>
    <div class="card">
      <div class="label">SEO trung binh</div>
      <div class="value" style="color:#22c55e">{stats.get('avg_seo', 0)}/100</div>
      <div class="sub">Diem toi uu noi dung</div>
    </div>
    <div class="card">
      <div class="label">Tong so tu</div>
      <div class="value" style="color:#a5b4fc">{stats.get('total_words', 0):,}</div>
      <div class="sub">{stats.get('total_links', 0)} affiliate links</div>
    </div>
    <div class="card">
      <div class="label">Keywords con lai</div>
      <div class="value" style="color:#f472b6">{stats.get('keywords_pending', 0)}</div>
      <div class="sub">/{stats.get('keywords_total', 0)} tong cong</div>
    </div>
  </div>

  <!-- PIPELINE -->
  <div class="pipeline">
    <h2>PIPELINE — Quy trinh AI tu dong lam viec</h2>
    <div class="pipeline-flow">
      <div class="step">
        <div class="num">Buoc 1</div>
        <div class="name">Nghien cuu</div>
        <div class="desc">AI tim keywords co luong tim kiem cao, it canh tranh trong niche sinh loi</div>
      </div>
      <div class="arrow">&#8594;</div>
      <div class="step">
        <div class="num">Buoc 2</div>
        <div class="name">Phan tich</div>
        <div class="desc">Quet top 10 Google, phan tich cau truc bai viet cua doi thu</div>
      </div>
      <div class="arrow">&#8594;</div>
      <div class="step">
        <div class="num">Buoc 3</div>
        <div class="name">Viet bai</div>
        <div class="desc">AI viet 2000+ tu, chen bang so sanh, FAQ, link affiliate tu dong</div>
      </div>
      <div class="arrow">&#8594;</div>
      <div class="step">
        <div class="num">Buoc 4</div>
        <div class="name">Dang bai</div>
        <div class="desc">Tu dong POST len blog Render, sitemap.xml cap nhat, Google index</div>
      </div>
      <div class="arrow">&#8594;</div>
      <div class="step">
        <div class="num">Buoc 5</div>
        <div class="name">Monitor</div>
        <div class="desc">Theo doi click, tu dong lam moi bai cu, toi uu bai yeu</div>
      </div>
    </div>
  </div>

  <!-- HOW MONEY WORKS -->
  <div class="money-flow">
    <h2>TIEN VE NHU THE NAO — Quy trinh kiem tien affiliate</h2>
    <div class="money-steps">
      <div class="money-step">
        <div class="ms-num">BUOC 1 — NOI DUNG</div>
        <div class="ms-title">Google index bai viet</div>
        <div class="ms-desc">Bai viet SEO chuan xuat hien tren Google khi nguoi dung tim kiem tu khoa nhu "best laptop 2026"</div>
      </div>
      <div class="money-step">
        <div class="ms-num">BUOC 2 — TRAFFIC</div>
        <div class="ms-title">Nguoi doc vao bai</div>
        <div class="ms-desc">Nguoi tim kiem click vao bai viet cua ban. Cang nhieu bai SEO tot, cang nhieu luot truy cap</div>
      </div>
      <div class="money-step">
        <div class="ms-num">BUOC 3 — CLICK</div>
        <div class="ms-title">Click vao link san pham</div>
        <div class="ms-desc">Nguoi doc click vao link Amazon / ClickBank trong bai. Cookie theo doi 24h (Amazon) den 60 ngay (ClickBank)</div>
      </div>
      <div class="money-step">
        <div class="ms-num">BUOC 4 — HOA HONG</div>
        <div class="ms-title">Ho mua hang = tien ve</div>
        <div class="ms-desc">Khi ho mua bat ky san pham tren Amazon trong 24h, ban nhan duoc 3-10% hoa hong. ClickBank tra 30-75%</div>
      </div>
      <div class="money-step">
        <div class="ms-num">BUOC 5 — THANH TOAN</div>
        <div class="ms-title">Amazon tra tien hang thang</div>
        <div class="ms-desc">Amazon Associates tra qua gift card hoac chuyen khoan, nguong toi thieu $10. ClickBank tra moi 2 tuan</div>
      </div>
    </div>
    <div class="money-example">
      <h3>Vi du cu the — 1 bai viet co the kiem bao nhieu?</h3>
      <p>
        Bai: <strong>"Best Noise Cancelling Headphones Under $200 (2026)"</strong><br>
        - 500 luot doc/thang (sau 3 thang Google index)<br>
        - 100 nguoi click link Amazon (20% CTR)<br>
        - 5 nguoi mua headphone $150 (5% conversion)<br>
        - Hoa hong 4% x $150 x 5 = <strong style="color:#22c55e">$30/thang</strong> tu 1 bai viet<br><br>
        He thong tu dong dang <strong>3 bai/ngay = 90 bai/thang</strong>.<br>
        Neu moi bai kiem $10-50/thang sau 3 thang = <strong style="color:#22c55e">$900 - $4,500/thang thu nhap thu dong</strong>
      </p>
    </div>
  </div>

  <!-- ARTICLES TABLE -->
  <div class="section">
    <h2>Bai viet da duoc dang ({stats.get('total_articles', 0)} bai)</h2>
    <table>
      <thead>
        <tr>
          <th>Tieu de</th>
          <th>Niche</th>
          <th>So tu</th>
          <th>SEO</th>
          <th>Links</th>
          <th>Ngay dang</th>
          <th>Xem</th>
        </tr>
      </thead>
      <tbody>{articles_html}</tbody>
    </table>
  </div>

  <!-- PRODUCTS TABLE -->
  <div class="section">
    <h2>San pham Affiliate dang duoc quang cao</h2>
    <table>
      <thead>
        <tr>
          <th>San pham</th>
          <th>Nen tang</th>
          <th>Hoa hong</th>
          <th>Gia TB</th>
          <th>Luot click</th>
          <th>Doanh thu</th>
        </tr>
      </thead>
      <tbody>{products_html}</tbody>
    </table>
    <p style="margin-top:12px;font-size:12px;color:#475569">
      * San pham duoc AI tu dong chon dua tren niche va ty le hoa hong cao nhat
    </p>
  </div>

  <!-- COMMANDS -->
  <div class="commands">
    <h2>Lenh dieu khien he thong</h2>
    <div class="cmd-grid">
      <div class="cmd-item">
        <code>python main.py schedule</code>
        <div class="cmd-desc">Bat che do tu dong: 3 bai/ngay luc 8h, 14h, 20h — chay 24/7</div>
      </div>
      <div class="cmd-item">
        <code>python main.py publish 3</code>
        <div class="cmd-desc">Viet va dang ngay 3 bai viet moi len blog</div>
      </div>
      <div class="cmd-item">
        <code>python main.py research</code>
        <div class="cmd-desc">Chi nghien cuu keywords moi, khong dang bai</div>
      </div>
      <div class="cmd-item">
        <code>python main.py report</code>
        <div class="cmd-desc">Xem bao cao hieu suat va chi phi API</div>
      </div>
      <div class="cmd-item">
        <code>python main.py monitor</code>
        <div class="cmd-desc">Kiem tra va lam moi bai viet cu, toi uu SEO</div>
      </div>
      <div class="cmd-item">
        <code>python dashboard.py</code>
        <div class="cmd-desc">Mo dashboard nay tai http://localhost:5050</div>
      </div>
    </div>
  </div>

</div>
</body>
</html>"""


@app.route("/")
@app.route("/dashboard")
def dashboard():
    stats = get_stats()
    # Kiem tra blog trong thread rieng, timeout ngan
    import concurrent.futures
    blog_status, blog_stats = "UNKNOWN", {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(check_blog_async)
        try:
            blog_status, blog_stats = future.result(timeout=4)
        except Exception:
            blog_status, blog_stats = "TIMEOUT", {}
    return render_html(stats, blog_status, blog_stats)


@app.route("/api/stats")
def api_stats():
    stats = get_stats()
    return jsonify({
        "total_articles": stats.get("total_articles", 0),
        "revenue": stats.get("revenue", 0),
        "affiliate_clicks": stats.get("affiliate_clicks", 0),
        "keywords_pending": stats.get("keywords_pending", 0),
    })


if __name__ == "__main__":
    import threading, webbrowser
    print(f"\n{'='*55}")
    print(f"  AI AFFILIATE DASHBOARD")
    print(f"  Mo trinh duyet: http://localhost:{PORT}")
    print(f"  Tu dong cap nhat moi 30 giay")
    print(f"  Nhan Ctrl+C de dung")
    print(f"{'='*55}\n")
    threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
