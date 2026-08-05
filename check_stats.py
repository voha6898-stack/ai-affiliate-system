import sqlite3
conn = sqlite3.connect('data/affiliate_ai.db')
articles = conn.execute("SELECT COUNT(*) FROM articles WHERE status='published'").fetchone()[0]
keywords = conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0]
niches = conn.execute("SELECT niche, COUNT(*) as c FROM articles WHERE status='published' GROUP BY niche ORDER BY c DESC").fetchall()
print(f"Articles published: {articles}")
print(f"Keywords researched: {keywords}")
print("Niches breakdown:")
for row in niches:
    print(f"  {row[0] or '(unknown)'}: {row[1]} bai")
conn.close()
