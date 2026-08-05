"""Fix remaining bad links: generic ShareASale + example.com placeholders."""
import sqlite3, re, os
from dotenv import load_dotenv
load_dotenv()

DB_PATH = "data/affiliate_ai.db"
AMAZON_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "123abc0bc-20")
NORDVPN_ID = os.getenv("NORDVPN_AFF_ID", "")
HOSTINGER_REF = os.getenv("HOSTINGER_REF", "")

NICHE_FALLBACK = {
    "vpn services":                f"https://go.nordvpn.net/aff_c?offer_id=15&aff_id={NORDVPN_ID}&url_id=902" if NORDVPN_ID else "https://nordvpn.com/pricing/",
    "web hosting":                 f"https://www.hostinger.com/web-hosting?REFERRALCODE={HOSTINGER_REF}" if HOSTINGER_REF else "https://www.hostinger.com/web-hosting",
    "antivirus software":          f"https://www.amazon.com/s?k=antivirus+software&tag={AMAZON_TAG}",
    "email marketing tools":       "https://www.getresponse.com/pricing",
    "password managers":           f"https://www.amazon.com/s?k=password+manager&tag={AMAZON_TAG}",
    "project management software": "https://monday.com/pricing",
    "online courses":              f"https://www.amazon.com/s?k=online+courses&tag={AMAZON_TAG}",
    "ai writing tools":            "https://www.jasper.ai/pricing",
}

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
articles = conn.execute("SELECT id, title, content, niche FROM articles WHERE status='published'").fetchall()

total_fixed = 0
articles_fixed = 0

for a in articles:
    content = a["content"]
    original = content
    niche = a["niche"] or ""
    fallback = NICHE_FALLBACK.get(niche, f"https://www.amazon.com/s?k=best+products&tag={AMAZON_TAG}")

    # Fix 1: generic ShareASale links (no real tracking)
    content = re.sub(
        r'https://www\.shareasale\.com/[^\s"\'<>]*',
        fallback,
        content
    )

    # Fix 2: example.com placeholders
    content = re.sub(
        r'https?://(?:www\.)?example\.com[^\s"\'<>]*',
        fallback,
        content
    )

    # Fix 3: any remaining /affiliates/ signup pages not caught before
    affiliate_signups = [
        (r'https://www\.getresponse\.com/affiliate[^\s"\'<>]*', "https://www.getresponse.com/pricing"),
        (r'https://convertkit\.com/affiliates[^\s"\'<>]*', "https://convertkit.com/pricing"),
        (r'https://www\.activecampaign\.com/partner[^\s"\'<>]*', "https://www.activecampaign.com/pricing"),
        (r'https://www\.jasper\.ai/affiliate[^\s"\'<>]*', "https://www.jasper.ai/pricing"),
        (r'https://monday\.com/affiliate[^\s"\'<>]*', "https://monday.com/pricing"),
        (r'https://www\.notion\.com/affiliates[^\s"\'<>]*', "https://www.notion.so/pricing"),
        (r'https://www\.copy\.ai/affiliates[^\s"\'<>]*', "https://www.copy.ai/pricing"),
        (r'https://www\.bluehost\.com/affiliate[^\s"\'<>]*', "https://www.bluehost.com/web-hosting"),
        (r'https://www\.siteground\.com/affiliates[^\s"\'<>]*', "https://www.siteground.com/web-hosting.htm"),
    ]
    for pattern, replacement in affiliate_signups:
        content = re.sub(pattern, replacement, content)

    if content != original:
        conn.execute("UPDATE articles SET content=? WHERE id=?", (content, a["id"]))
        count = original.count("shareasale.com") - content.count("shareasale.com")
        count += original.count("example.com") - content.count("example.com")
        total_fixed += abs(count) or 1
        articles_fixed += 1
        print(f"[OK] Fixed: {a['title'][:60]}")

conn.commit()
conn.close()
print(f"\nDone: {total_fixed} bad links fixed across {articles_fixed} articles")
