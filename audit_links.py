"""Deep audit of all affiliate links in generated HTML files."""
import os, re
from collections import Counter

OUT_DIR = "docs/article"
problems = []
ok_count = 0

for root, dirs, files in os.walk(OUT_DIR):
    for fname in files:
        if fname != "index.html":
            continue
        path = os.path.join(root, fname)
        with open(path, encoding="utf-8", errors="ignore") as f:
            html = f.read()

        links = re.findall(r'href=["\']([^"\']+)["\']', html)
        for link in links:
            link = link.strip()
            if not link.startswith("http"):
                continue
            # Detect bad patterns
            bad = None
            if "affiliates/" in link and link.endswith("/affiliates/"):
                bad = "signup page (affiliates/)"
            elif link.endswith("/affiliate") or link.endswith("/affiliates"):
                bad = "signup page (/affiliate)"
            elif "/partner" in link and "getresponse" in link:
                bad = "partner signup page"
            elif "REFERRALCODE=" in link and len(link.split("REFERRALCODE=")[-1]) < 3:
                bad = "empty referral code"
            elif "aff_id=&" in link or "aff_id=0" in link:
                bad = "empty aff_id"
            elif link == "https://www.shareasale.com/":
                bad = "generic ShareASale (no tracking)"
            elif "example.com" in link:
                bad = "example.com placeholder"
            elif link.count("http") > 1:
                bad = "double URL"

            if bad:
                article = root.replace(OUT_DIR, "").strip("/\\")[:50]
                problems.append((bad, link[:90], article))
            else:
                ok_count += 1

# Group by issue type
by_type = Counter(p[0] for p in problems)
print(f"OK links: {ok_count}")
print(f"Bad links: {len(problems)}")
print(f"\nIssues by type:")
for issue, count in by_type.most_common():
    print(f"  [{count}] {issue}")

print(f"\nSample bad links:")
seen_types = set()
for bad_type, link, article in problems:
    if bad_type not in seen_types:
        print(f"\n  Type: {bad_type}")
        print(f"  Link: {link}")
        print(f"  In:   {article}")
        seen_types.add(bad_type)
