"""
Fix Amazon affiliate links — add tracking tag to all amazon.com links.
Tag is already known: 123abc0bc-20
"""
import sqlite3, re, os
from dotenv import load_dotenv
load_dotenv()

DB_PATH = "data/affiliate_ai.db"
TAG = os.getenv("AMAZON_AFFILIATE_TAG", "123abc0bc-20")

def fix_amazon_url(url: str) -> str:
    if "amazon.com" not in url:
        return url
    if f"tag={TAG}" in url:
        return url  # already tagged
    # Remove any existing tag= param to avoid duplicates
    url = re.sub(r'[&?]tag=[^&"\s]*', '', url)
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}tag={TAG}"

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
articles = conn.execute("SELECT id, title, content FROM articles WHERE status='published'").fetchall()

total_fixed = 0
articles_fixed = 0

for a in articles:
    content = a["content"]
    original = content

    def replacer(m):
        fixed = fix_amazon_url(m.group(0))
        return fixed

    content = re.sub(r'https?://(?:www\.)?amazon\.com[^\s"\'<>]*', replacer, content)

    if content != original:
        count = len(re.findall(r'https?://(?:www\.)?amazon\.com', original))
        conn.execute("UPDATE articles SET content=? WHERE id=?", (content, a["id"]))
        total_fixed += count
        articles_fixed += 1

conn.commit()
conn.close()
print(f"[OK] Fixed {total_fixed} Amazon links across {articles_fixed} articles")
print(f"[OK] Tag used: {TAG}")
print(f"[OK] Example: https://www.amazon.com/s?k=NordVPN&tag={TAG}")
