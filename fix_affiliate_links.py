"""
Fix all wrong affiliate signup URLs in existing articles.
Replaces /affiliates/ signup pages with actual product/pricing pages.
"""
import sqlite3
import re

DB_PATH = "data/affiliate_ai.db"

# Map: wrong signup URL → correct product URL (trackable once you add your ID)
URL_FIX_MAP = {
    # VPN
    "https://nordvpn.com/affiliates/":       "https://nordvpn.com/pricing/",
    "https://www.expressvpn.com/affiliates":  "https://www.expressvpn.com/order",
    "https://surfshark.com/affiliates":       "https://surfshark.com/vpn",
    # Hosting
    "https://www.hostinger.com/affiliates":   "https://www.hostinger.com/web-hosting",
    "https://www.bluehost.com/affiliate":     "https://www.bluehost.com/web-hosting",
    "https://www.siteground.com/affiliates.htm": "https://www.siteground.com/web-hosting.htm",
    # Email marketing
    "https://www.getresponse.com/affiliate":  "https://www.getresponse.com/pricing",
    "https://convertkit.com/affiliates":      "https://convertkit.com/pricing",
    "https://www.activecampaign.com/partner": "https://www.activecampaign.com/pricing",
    # Password managers
    "https://1password.com/affiliate":        "https://1password.com/sign-up/",
    "https://www.dashlane.com/partners":      "https://www.dashlane.com/pricing",
    # Project management
    "https://monday.com/affiliate":           "https://monday.com/pricing",
    "https://www.notion.com/affiliates":      "https://www.notion.so/pricing",
    # AI tools
    "https://www.jasper.ai/affiliate":        "https://www.jasper.ai/pricing",
    "https://www.copy.ai/affiliates":         "https://www.copy.ai/pricing",
    # Courses
    "https://www.udemy.com/affiliate/":       "https://www.udemy.com/courses/",
    "https://www.coursera.org/about/affiliates": "https://www.coursera.org/courseraplus",
    # Other generic
    "https://www.shareasale.com/":            "https://www.shareasale.com/",
    "https://www.bitdefender.com/affiliates/": "https://www.bitdefender.com/solutions/total-security.html",
}

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
articles = conn.execute("SELECT id, title, content FROM articles WHERE status='published'").fetchall()

fixed_total = 0
for a in articles:
    content = a["content"]
    original = content
    for wrong, correct in URL_FIX_MAP.items():
        if wrong in content:
            content = content.replace(wrong, correct)

    if content != original:
        count = sum(original.count(w) for w in URL_FIX_MAP if w in original)
        conn.execute("UPDATE articles SET content=? WHERE id=?", (content, a["id"]))
        fixed_total += count
        print(f"[OK] Fixed {count} links in: {a['title'][:60]}")

conn.commit()
conn.close()
print(f"\nDone: {fixed_total} bad affiliate links fixed across all articles.")
