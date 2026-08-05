"""
Fix href="#" placeholder links in articles.
Replaces with real tracked affiliate links based on niche + anchor text.
"""
import sqlite3, re, os
from dotenv import load_dotenv
load_dotenv()

DB_PATH = "data/affiliate_ai.db"
AMAZON_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "123abc0bc-20")
NORDVPN_ID = os.getenv("NORDVPN_AFF_ID", "")
HOSTINGER_REF = os.getenv("HOSTINGER_REF", "")
CLICKBANK_ID = os.getenv("CLICKBANK_ID", "")

# Real affiliate links by niche — used when no keyword match
NICHE_DEFAULT = {
    "vpn services":               f"https://go.nordvpn.net/aff_c?offer_id=15&aff_id={NORDVPN_ID}&url_id=902" if NORDVPN_ID else "https://nordvpn.com/pricing/",
    "web hosting":                f"https://www.hostinger.com/web-hosting?REFERRALCODE={HOSTINGER_REF}" if HOSTINGER_REF else "https://www.hostinger.com/web-hosting",
    "antivirus software":         f"https://www.amazon.com/s?k=antivirus+software&tag={AMAZON_TAG}",
    "email marketing tools":      "https://www.getresponse.com/pricing",
    "password managers":          f"https://www.amazon.com/s?k=password+manager&tag={AMAZON_TAG}",
    "project management software":f"https://www.amazon.com/s?k=project+management+software&tag={AMAZON_TAG}",
    "online courses":             f"https://www.amazon.com/s?k=online+courses&tag={AMAZON_TAG}",
    "ai writing tools":           "https://www.jasper.ai/pricing",
}

# Keyword → affiliate URL mapping (checked against anchor text)
KEYWORD_LINKS = {
    "nordvpn":      f"https://go.nordvpn.net/aff_c?offer_id=15&aff_id={NORDVPN_ID}&url_id=902" if NORDVPN_ID else "https://nordvpn.com/pricing/",
    "expressvpn":   "https://www.expressvpn.com/order",
    "surfshark":    "https://surfshark.com/vpn",
    "hostinger":    f"https://www.hostinger.com/web-hosting?REFERRALCODE={HOSTINGER_REF}" if HOSTINGER_REF else "https://www.hostinger.com/web-hosting",
    "bluehost":     "https://www.bluehost.com/web-hosting",
    "siteground":   "https://www.siteground.com/web-hosting.htm",
    "jasper":       "https://www.jasper.ai/pricing",
    "copy.ai":      "https://www.copy.ai/pricing",
    "writesonic":   "https://writesonic.com/pricing",
    "getresponse":  "https://www.getresponse.com/pricing",
    "mailchimp":    "https://mailchimp.com/pricing/",
    "convertkit":   "https://convertkit.com/pricing",
    "1password":    "https://1password.com/sign-up/",
    "lastpass":     "https://www.lastpass.com/pricing",
    "dashlane":     "https://www.dashlane.com/pricing",
    "norton":       f"https://www.amazon.com/s?k=norton+antivirus&tag={AMAZON_TAG}",
    "bitdefender":  "https://www.bitdefender.com/solutions/total-security.html",
    "malwarebytes": f"https://www.amazon.com/s?k=malwarebytes&tag={AMAZON_TAG}",
    "monday":       "https://monday.com/pricing",
    "notion":       "https://www.notion.so/pricing",
    "asana":        "https://asana.com/pricing",
    "udemy":        f"https://www.amazon.com/s?k=udemy+courses&tag={AMAZON_TAG}",
    "coursera":     "https://www.coursera.org/courseraplus",
}

def get_replacement_url(anchor_text: str, niche: str) -> str:
    text_lower = anchor_text.lower()
    for keyword, url in KEYWORD_LINKS.items():
        if keyword in text_lower:
            return url
    return NICHE_DEFAULT.get(niche, f"https://www.amazon.com/s?k={anchor_text.replace(' ', '+')[:50]}&tag={AMAZON_TAG}")

def fix_hash_links(content: str, niche: str) -> tuple[str, int]:
    count = 0
    def replacer(m):
        nonlocal count
        full_tag = m.group(0)
        anchor_text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not anchor_text:
            return full_tag
        new_url = get_replacement_url(anchor_text, niche)
        count += 1
        return full_tag.replace('href="#"', f'href="{new_url}"')

    # Match <a href="#" ...>content</a>
    content = re.sub(
        r'<a\s+href=["\']#["\'][^>]*>(.*?)</a>',
        replacer,
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    return content, count

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
articles = conn.execute("SELECT id, title, content, niche FROM articles WHERE status='published'").fetchall()

total_fixed = 0
articles_fixed = 0

for a in articles:
    new_content, count = fix_hash_links(a["content"], a["niche"] or "")
    if count:
        conn.execute("UPDATE articles SET content=? WHERE id=?", (new_content, a["id"]))
        total_fixed += count
        articles_fixed += 1
        print(f"[OK] Fixed {count} links in: {a['title'][:60]}")

conn.commit()
conn.close()
print(f"\nDone: {total_fixed} broken links fixed across {articles_fixed} articles")
