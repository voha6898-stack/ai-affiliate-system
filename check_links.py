"""Check what affiliate links are actually in published articles."""
import sqlite3, re
from collections import Counter

conn = sqlite3.connect("data/affiliate_ai.db")
articles = conn.execute("SELECT content FROM articles WHERE status='published'").fetchall()
conn.close()

all_links = []
for (content,) in articles:
    all_links += re.findall(r'https?://[^\s"\'<>]+', content)

affiliate_domains = [
    "amazon", "nordvpn", "expressvpn", "hostinger", "bluehost",
    "getresponse", "clickbank", "jasper", "copy.ai", "go.nordvpn"
]

found = [l for l in all_links if any(d in l for d in affiliate_domains)]
domain_count = Counter(re.search(r'https?://([^/]+)', l).group(1) for l in found if re.search(r'https?://([^/]+)', l))

print(f"Total affiliate links found: {len(found)}")
print("\nBy domain:")
for domain, count in domain_count.most_common():
    print(f"  {domain}: {count} links")

print("\nSample links:")
for l in found[:5]:
    print(f"  {l[:90]}")
