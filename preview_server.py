"""
Local Preview Server
- Xem tất cả bài viết AI tạo ra trong browser
- Không cần WordPress, không cần internet
- Chạy: python preview_server.py
- Mở: http://localhost:8080
"""
import os
import re
import json
import sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT = 8080
ARTICLES_DIR = "data/articles"
DB_PATH = "data/affiliate_ai.db"


def get_articles_from_db():
    """Lấy danh sách bài từ database."""
    if not os.path.exists(DB_PATH):
        return []
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT a.*, k.keyword, k.niche
            FROM articles a
            LEFT JOIN keywords k ON a.keyword_id = k.id
            ORDER BY a.created_at DESC
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_article_files():
    """Lấy danh sách file HTML trong data/articles/."""
    if not os.path.exists(ARTICLES_DIR):
        return []
    files = []
    for f in sorted(Path(ARTICLES_DIR).glob("*.html"), key=os.path.getmtime, reverse=True):
        stat = f.stat()
        files.append({
            "filename": f.name,
            "path": str(f),
            "size_kb": round(stat.st_size / 1024, 1),
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return files


def build_dashboard() -> str:
    """Tạo trang dashboard HTML."""
    articles = get_articles_from_db()
    files = get_article_files()

    article_rows = ""
    if articles:
        for a in articles:
            status_color = {"published": "#22c55e", "draft": "#f59e0b"}.get(a.get("status","draft"), "#94a3b8")
            article_rows += f"""
            <tr>
                <td><a href="/article/{a.get('slug','')}.html" style="color:#6366f1;font-weight:600">{a.get('title','')[:55]}</a></td>
                <td>{a.get('keyword','')}</td>
                <td>{a.get('niche','')}</td>
                <td>{a.get('word_count',0):,}</td>
                <td>{a.get('affiliate_links_count',0)}</td>
                <td><span style="color:{status_color};font-weight:bold">{a.get('seo_score',0)}/100</span></td>
                <td><span style="background:{status_color};color:white;padding:2px 8px;border-radius:12px;font-size:12px">{a.get('status','draft').upper()}</span></td>
            </tr>"""
    elif files:
        for f in files:
            name = f["filename"].replace("-", " ").replace(".html", "").title()
            article_rows += f"""
            <tr>
                <td><a href="/files/{f['filename']}" style="color:#6366f1;font-weight:600">{name[:55]}</a></td>
                <td>—</td><td>—</td><td>—</td><td>—</td><td>—</td>
                <td><span style="background:#22c55e;color:white;padding:2px 8px;border-radius:12px;font-size:12px">SAVED</span></td>
            </tr>"""
    else:
        article_rows = '<tr><td colspan="7" style="text-align:center;color:#64748b;padding:40px">Chua co bai viet. Chay: python main.py publish 1</td></tr>'

    total_words = sum(a.get("word_count", 0) for a in articles)
    total_links = sum(a.get("affiliate_links_count", 0) for a in articles)

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Affiliate System — Dashboard</title>
<style>
  * {{ margin:0;padding:0;box-sizing:border-box }}
  body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh }}
  .header {{ background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:24px 40px;display:flex;justify-content:space-between;align-items:center }}
  .header h1 {{ font-size:24px;font-weight:700 }}
  .header .status {{ background:rgba(255,255,255,0.2);padding:6px 16px;border-radius:20px;font-size:14px }}
  .container {{ max-width:1400px;margin:0 auto;padding:32px 24px }}
  .stats {{ display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:32px }}
  .stat-card {{ background:#1e293b;border:1px solid #334155;border-radius:12px;padding:20px }}
  .stat-card .label {{ font-size:13px;color:#94a3b8;margin-bottom:8px }}
  .stat-card .value {{ font-size:28px;font-weight:700;color:#6366f1 }}
  .stat-card .sub {{ font-size:12px;color:#64748b;margin-top:4px }}
  .section {{ background:#1e293b;border:1px solid #334155;border-radius:12px;margin-bottom:24px }}
  .section-header {{ padding:16px 24px;border-bottom:1px solid #334155;display:flex;justify-content:space-between;align-items:center }}
  .section-header h2 {{ font-size:16px;font-weight:600 }}
  .btn {{ background:#6366f1;color:white;border:none;padding:8px 20px;border-radius:8px;cursor:pointer;font-size:13px;text-decoration:none;display:inline-block }}
  .btn:hover {{ background:#4f46e5 }}
  table {{ width:100%;border-collapse:collapse }}
  th {{ text-align:left;padding:12px 16px;font-size:12px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;border-bottom:1px solid #334155 }}
  td {{ padding:14px 16px;border-bottom:1px solid #1e293b;font-size:14px }}
  tr:hover td {{ background:#263347 }}
  .cmd {{ background:#0f172a;border:1px solid #334155;border-radius:8px;padding:16px;font-family:monospace;font-size:13px;color:#22c55e;margin:16px 24px 24px }}
  .cmd span {{ color:#94a3b8 }}
</style>
</head>
<body>
<div class="header">
  <h1>AI Affiliate System</h1>
  <div class="status">RUNNING — Groq AI Active</div>
</div>
<div class="container">
  <div class="stats">
    <div class="stat-card">
      <div class="label">Tong bai viet</div>
      <div class="value">{len(articles) or len(files)}</div>
      <div class="sub">Da tao tu dong</div>
    </div>
    <div class="stat-card">
      <div class="label">Tong so tu</div>
      <div class="value">{total_words:,}</div>
      <div class="sub">Noi dung SEO</div>
    </div>
    <div class="stat-card">
      <div class="label">Affiliate Links</div>
      <div class="value">{total_links}</div>
      <div class="sub">Da chen tu dong</div>
    </div>
    <div class="stat-card">
      <div class="label">AI Provider</div>
      <div class="value" style="font-size:20px">GROQ</div>
      <div class="sub">14,400 req/ngay mien phi</div>
    </div>
  </div>

  <div class="section">
    <div class="section-header">
      <h2>Bai Viet Da Tao ({len(articles) or len(files)} bai)</h2>
      <a href="/run" class="btn">+ Tao Bai Moi</a>
    </div>
    <table>
      <thead><tr>
        <th>Tieu De</th><th>Keyword</th><th>Niche</th>
        <th>So Tu</th><th>Aff. Links</th><th>SEO</th><th>Trang Thai</th>
      </tr></thead>
      <tbody>{article_rows}</tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-header"><h2>Lenh Chay Nhanh</h2></div>
    <div class="cmd">
      <span># Tao 1 bai moi ngay:</span><br>
      python main.py publish 1<br><br>
      <span># Bat auto-pilot (3 bai/ngay):</span><br>
      python main.py schedule<br><br>
      <span># Ket noi WordPress:</span><br>
      python main.py setup
    </div>
  </div>
</div>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Tắt log

    def do_GET(self):
        path = self.path

        # Dashboard
        if path == "/" or path == "/dashboard":
            content = build_dashboard().encode("utf-8")
            self._respond(200, "text/html", content)

        # Article từ DB slug
        elif path.startswith("/article/"):
            filename = path.replace("/article/", "")
            filepath = os.path.join(ARTICLES_DIR, filename)
            self._serve_file(filepath)

        # Article từ file
        elif path.startswith("/files/"):
            filename = path.replace("/files/", "")
            filepath = os.path.join(ARTICLES_DIR, filename)
            self._serve_file(filepath)

        # Trigger tạo bài mới
        elif path == "/run":
            html = """<html><body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:40px">
            <h2>Dang tao bai moi...</h2>
            <p>Mo terminal va chay: <code style="background:#1e293b;padding:4px 8px;border-radius:4px">python main.py publish 1</code></p>
            <a href="/" style="color:#6366f1">← Quay lai Dashboard</a>
            </body></html>"""
            self._respond(200, "text/html", html.encode())

        else:
            self._respond(404, "text/plain", b"Not found")

    def _serve_file(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, "rb") as f:
                content = f.read()
            # Inject back button
            back_btn = b'<div style="position:fixed;top:16px;left:16px;z-index:9999"><a href="/" style="background:#6366f1;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;font-family:sans-serif;font-size:13px">&#8592; Dashboard</a></div>'
            content = content.replace(b"<body>", b"<body>" + back_btn, 1)
            self._respond(200, "text/html", content)
        else:
            self._respond(404, "text/plain", b"File not found")

    def _respond(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


def main():
    os.makedirs(ARTICLES_DIR, exist_ok=True)
    server = HTTPServer(("localhost", PORT), Handler)
    print(f"""
==================================================
  AI AFFILIATE SYSTEM -- LOCAL PREVIEW SERVER
==================================================
  Dashboard : http://localhost:{PORT}
  Articles  : http://localhost:{PORT}/files/

  Press Ctrl+C to stop
==================================================
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
