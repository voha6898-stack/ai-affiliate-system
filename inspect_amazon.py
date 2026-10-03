import sqlite3, re

conn = sqlite3.connect("data/affiliate_ai.db")
articles = conn.execute("SELECT content FROM articles WHERE status='published'").fetchall()
conn.close()

samples = []
for (content,) in articles:
    links = re.findall(r'https?://(?:www\.)?amazon\.com[^\s"\'<>\)]*', content)
    samples.extend(links)

print(f"Total Amazon links: {len(samples)}")
print("\nSample links (first 10):")
for l in samples[:10]:
    print(f"  {l}")

# Check tag distribution
has_tag = [l for l in samples if "tag=" in l]
no_tag  = [l for l in samples if "tag=" not in l]
print(f"\nWith tag: {len(has_tag)}")
print(f"Without tag: {len(no_tag)}")
if has_tag:
    print("\nExisting tags found:")
    tags = set(re.search(r'tag=([^&"\s\)]+)', l).group(1) for l in has_tag if re.search(r'tag=([^&"\s\)]+)', l))
    for t in tags:
        print(f"  tag={t}")
