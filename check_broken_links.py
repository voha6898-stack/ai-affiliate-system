"""Check affiliate links in published articles for issues."""
import sqlite3, re
from collections import Counter

conn = sqlite3.connect("data/affiliate_ai.db")
articles = conn.execute("SELECT title, content FROM articles WHERE status='published'").fetchall()
conn.close()

problems = []
samples = {"ok": [], "broken": []}

for title, content in articles:
    links = re.findall(r'href=["\']([^"\']+)["\']', content)
    for link in links:
        link = link.strip()
        # Detect broken patterns
        if any([
            link.startswith("http") and "  " in link,       # double space
            link.startswith("http") and "\n" in link,        # newline in URL
            "{" in link or "}" in link,                      # unfilled template
            link == "#" or link == "",                        # empty/hash
            "REFERRALCODE" in link and "=" not in link.split("REFERRALCODE")[-1],
            "aff_id=XXXXX" in link or "aff_id=123456" in link,  # placeholder IDs
            "AFFILIATE_ID" in link.upper(),
            link.endswith("/affiliates/") or link.endswith("/affiliate"),
            "signup" in link and "affiliate" in link,
        ]):
            problems.append((title[:50], link[:100]))
            if len(samples["broken"]) < 5:
                samples["broken"].append(link[:120])
        else:
            if link.startswith("http") and len(samples["ok"]) < 3:
                samples["ok"].append(link[:120])

print(f"Total broken/suspicious links: {len(problems)}")
print(f"\nSample broken links:")
for l in samples["broken"]:
    print(f"  {l}")

print(f"\nSample OK links:")
for l in samples["ok"]:
    print(f"  {l}")

if problems:
    print(f"\nArticles with issues (first 10):")
    for title, link in problems[:10]:
        print(f"  [{title}]\n    {link}")
