"""
Fix articles with missing niche tags.
Assigns niche based on keyword matching in title + content.
"""
import sqlite3
import re

DB_PATH = "data/affiliate_ai.db"

NICHE_KEYWORDS = {
    "web hosting": ["hosting", "bluehost", "hostinger", "siteground", "cpanel", "wordpress host", "web host", "vps", "shared hosting", "domain"],
    "vpn services": ["vpn", "nordvpn", "expressvpn", "surfshark", "private internet", "virtual private network", "ip address", "encryption", "anonymous"],
    "password managers": ["password manager", "1password", "lastpass", "dashlane", "bitwarden", "keepass", "password vault", "password security"],
    "antivirus software": ["antivirus", "norton", "bitdefender", "malwarebytes", "kaspersky", "mcafee", "virus", "malware", "cybersecurity", "internet security"],
    "email marketing tools": ["email marketing", "getresponse", "mailchimp", "convertkit", "activecampaign", "aweber", "newsletter", "email list", "autoresponder", "drip campaign"],
    "project management software": ["project management", "monday.com", "asana", "trello", "notion", "clickup", "jira", "task management", "team collaboration"],
    "online courses": ["online course", "udemy", "coursera", "skillshare", "teachable", "e-learning", "elearning", "learn online", "certification", "tutorial"],
    "ai writing tools": ["ai writing", "jasper", "copy.ai", "writesonic", "chatgpt", "gpt", "ai content", "ai writer", "content generation", "copywriting ai"],
}

def detect_niche(title: str, content: str) -> str:
    text = (title + " " + content[:2000]).lower()
    scores = {}
    for niche, keywords in NICHE_KEYWORDS.items():
        score = sum(text.count(kw.lower()) for kw in keywords)
        if score > 0:
            scores[niche] = score
    if not scores:
        return ""
    return max(scores, key=scores.get)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

articles = conn.execute(
    "SELECT id, title, content, niche FROM articles WHERE status='published' AND (niche IS NULL OR niche = '')"
).fetchall()

print(f"Found {len(articles)} articles without niche tag\n")

fixed = 0
for a in articles:
    detected = detect_niche(a["title"], a["content"])
    if detected:
        conn.execute("UPDATE articles SET niche=? WHERE id=?", (detected, a["id"]))
        print(f"[OK] '{a['title'][:55]}...' → {detected}")
        fixed += 1
    else:
        print(f"[??] '{a['title'][:55]}...' → could not detect niche")

conn.commit()
conn.close()
print(f"\nDone: {fixed}/{len(articles)} articles fixed.")
