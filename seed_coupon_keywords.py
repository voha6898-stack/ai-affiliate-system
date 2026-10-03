"""
Seed high-conversion coupon/deal keywords into the DB.
Buyer intent score = 10 (person has already decided to buy, just wants a discount).
These convert 3-5x better than generic review articles.

Run once: python seed_coupon_keywords.py
"""
import sqlite3
from datetime import datetime
from utils.database import get_db, init_db

MONTH = "October 2026"   # Update monthly or make dynamic

COUPON_KEYWORDS = [
    # ── Web Hosting (highest commission: $60-100/sale) ──────────────────────
    ("hostinger coupon code",                         "web hosting", 10.0, 22000),
    (f"hostinger coupon code {MONTH}",                "web hosting", 10.0, 12000),
    ("hostinger promo code",                          "web hosting", 10.0, 18000),
    ("hostinger discount code",                       "web hosting", 10.0, 14000),
    ("hostinger black friday deal",                   "web hosting", 10.0, 9000),
    ("bluehost coupon code",                          "web hosting", 10.0, 20000),
    (f"bluehost coupon code {MONTH}",                 "web hosting", 10.0, 10000),
    ("bluehost promo code",                           "web hosting", 10.0, 16000),
    ("namecheap coupon code",                         "web hosting", 10.0, 15000),
    ("siteground coupon code",                        "web hosting", 10.0, 12000),
    ("dreamhost promo code",                          "web hosting", 10.0, 8000),
    ("a2 hosting coupon code",                        "web hosting", 10.0, 7000),
    ("hostinger vs bluehost cheapest plan",           "web hosting", 9.0,  6000),
    ("cheapest web hosting coupon 2026",              "web hosting", 9.0,  5000),
    ("hostinger wordpress hosting discount",          "web hosting", 9.5,  8000),

    # ── VPN (commission: 40% of purchase price) ──────────────────────────────
    ("nordvpn coupon code",                           "vpn services", 10.0, 30000),
    (f"nordvpn coupon code {MONTH}",                  "vpn services", 10.0, 18000),
    ("nordvpn discount code",                         "vpn services", 10.0, 25000),
    ("nordvpn promo code",                            "vpn services", 10.0, 20000),
    ("nordvpn black friday",                          "vpn services", 10.0, 15000),
    ("expressvpn coupon code",                        "vpn services", 10.0, 22000),
    ("expressvpn discount",                           "vpn services", 10.0, 18000),
    ("surfshark coupon code",                         "vpn services", 10.0, 19000),
    ("surfshark promo code",                          "vpn services", 10.0, 16000),
    ("cyberghost coupon",                             "vpn services", 10.0, 12000),
    ("nordvpn vs expressvpn cheapest",                "vpn services", 9.0,  8000),
    ("best vpn deal right now",                       "vpn services", 9.5,  6000),
    ("cheapest vpn with coupon 2026",                 "vpn services", 9.0,  5000),

    # ── Email Marketing (commission: 33% recurring) ──────────────────────────
    ("getresponse coupon code",                       "email marketing tools", 10.0, 8000),
    ("getresponse promo code",                        "email marketing tools", 10.0, 6000),
    ("mailchimp discount",                            "email marketing tools", 10.0, 9000),
    ("convertkit coupon code",                        "email marketing tools", 10.0, 5000),
    ("activecampaign discount",                       "email marketing tools", 10.0, 7000),
    ("klaviyo promo code",                            "email marketing tools", 10.0, 6000),
    ("aweber coupon code",                            "email marketing tools", 10.0, 4000),
    ("cheapest email marketing tool 2026",            "email marketing tools", 9.0,  4000),

    # ── AI Writing (commission: 30% recurring) ───────────────────────────────
    ("jasper ai coupon code",                         "ai writing tools", 10.0, 9000),
    ("jasper ai promo code",                          "ai writing tools", 10.0, 7000),
    ("copy ai discount",                              "ai writing tools", 10.0, 6000),
    ("writesonic coupon code",                        "ai writing tools", 10.0, 5000),
    ("rytr coupon code",                              "ai writing tools", 10.0, 4000),
    ("surfer seo discount",                           "ai writing tools", 9.5,  5000),
    ("semrush coupon code",                           "ai writing tools", 10.0, 12000),
    ("ahrefs discount code",                          "ai writing tools", 10.0, 10000),

    # ── Password Managers (25% recurring) ───────────────────────────────────
    ("1password coupon code",                         "password managers", 10.0, 6000),
    ("lastpass discount",                             "password managers", 10.0, 5000),
    ("dashlane promo code",                           "password managers", 10.0, 5000),
    ("bitwarden coupon",                              "password managers", 9.0,  3000),
    ("nordpass coupon code",                          "password managers", 10.0, 4000),

    # ── Antivirus (high one-time commissions) ────────────────────────────────
    ("norton discount code",                          "antivirus software", 10.0, 14000),
    ("bitdefender coupon code",                       "antivirus software", 10.0, 11000),
    ("kaspersky promo code",                          "antivirus software", 10.0, 9000),
    ("malwarebytes discount",                         "antivirus software", 10.0, 8000),
    ("mcafee coupon code",                            "antivirus software", 10.0, 10000),

    # ── Project Management ───────────────────────────────────────────────────
    ("monday com coupon code",                        "project management software", 10.0, 7000),
    ("asana discount",                                "project management software", 10.0, 5000),
    ("clickup promo code",                            "project management software", 10.0, 6000),
    ("notion coupon code",                            "project management software", 10.0, 5000),
]


def seed():
    init_db()
    added = 0
    skipped = 0

    with get_db() as conn:
        for keyword, niche, intent_score, search_vol in COUPON_KEYWORDS:
            try:
                conn.execute("""
                    INSERT INTO keywords
                        (keyword, niche, search_volume, buyer_intent_score, status, created_at)
                    VALUES (?, ?, ?, ?, 'pending', ?)
                """, (keyword, niche, search_vol, intent_score, datetime.now().isoformat()))
                added += 1
            except sqlite3.IntegrityError:
                skipped += 1  # already exists

        conn.commit()

    print(f"[OK] Coupon keywords: {added} added, {skipped} already existed")
    print(f"     These have buyer_intent_score=10 -> will be picked FIRST by publish_balanced.py")
    print(f"     High-value targets: Hostinger ($60-100/sale), NordVPN (40% × plan price)")


if __name__ == "__main__":
    seed()
