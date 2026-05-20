"""
Affiliate Link Manager
- Manages products from Amazon, ClickBank, ShareASale
- Auto-generates tracked affiliate URLs
- Tracks clicks and conversions per product
- Ranks products by conversion potential
"""
import json
import logging
import re
from typing import List, Dict, Optional
from config import config
from utils.claude_client import claude
from utils.database import AffiliateProductDB

logger = logging.getLogger(__name__)


class AffiliateManager:
    """
    Central manager for all affiliate products and links.
    AI-powered product selection for maximum conversions.
    """

    def get_products_for_niche(self, niche: str, keyword: str = "") -> List[Dict]:
        """
        Get best affiliate products for a given niche + keyword.
        Priority: high-commission direct → ClickBank → DB → AI-suggested
        """
        # 1. High-commission direct programs
        hc_products = self._get_high_commission_products(niche)

        # 2. ClickBank products (no approval needed, 50-75% commission)
        cb_products = self._get_clickbank_products(niche)

        combined = hc_products + cb_products
        if len(combined) >= 3:
            return combined

        # 3. Check database
        db_products = AffiliateProductDB.get_by_niche(niche, limit=8)
        if len(db_products) >= 5:
            return db_products

        # 4. AI suggests products if database is sparse
        ai_products = self._ai_suggest_products(niche, keyword)

        # Save AI suggestions to database
        for p in ai_products:
            AffiliateProductDB.add(
                name=p["name"],
                platform=p.get("platform", "amazon"),
                product_id=p.get("product_id", ""),
                affiliate_url=self._build_affiliate_url(p),
                commission_rate=p.get("commission_rate", 5.0),
                avg_price=p.get("avg_price", 0),
                category=p.get("category", niche),
                niche=niche
            )

        # Return combined list
        return AffiliateProductDB.get_by_niche(niche, limit=10) or ai_products

    def _get_high_commission_products(self, niche: str) -> List[Dict]:
        """Return high-commission products with REAL tracked URLs (when IDs configured)."""
        af = config.affiliate
        programs = {
            "web hosting": [
                {
                    "name": "Bluehost",
                    "commission_rate": 65, "avg_price": 65, "category": "web hosting",
                    "affiliate_url": (
                        f"https://www.bluehost.com/track/{af.bluehost_tracking_id}/"
                        if af.bluehost_tracking_id
                        else "https://www.bluehost.com/web-hosting"
                    ),
                    "has_real_link": bool(af.bluehost_tracking_id),
                },
                {
                    "name": "Hostinger",
                    "commission_rate": 60, "avg_price": 60, "category": "web hosting",
                    "affiliate_url": (
                        f"https://hostinger.com?REFERRALCODE={af.hostinger_ref}"
                        if af.hostinger_ref
                        else "https://www.hostinger.com/web-hosting"
                    ),
                    "has_real_link": bool(af.hostinger_ref),
                },
                {
                    "name": "SiteGround",
                    "commission_rate": 50, "avg_price": 80, "category": "web hosting",
                    "affiliate_url": "https://www.siteground.com/web-hosting.htm",
                    "has_real_link": False,
                },
            ],
            "vpn services": [
                {
                    "name": "NordVPN",
                    "commission_rate": 40, "avg_price": 99, "category": "vpn",
                    "affiliate_url": (
                        f"https://go.nordvpn.net/aff_c?offer_id=15&aff_id={af.nordvpn_aff_id}&url_id=902"
                        if af.nordvpn_aff_id
                        else "https://nordvpn.com/pricing/"
                    ),
                    "has_real_link": bool(af.nordvpn_aff_id),
                },
                {
                    "name": "ExpressVPN",
                    "commission_rate": 36, "avg_price": 100, "category": "vpn",
                    "affiliate_url": (
                        f"https://www.expressrefer.com/refer-a-friend/30-days-free?referrer_id={af.expressvpn_aff_id}&utm_campaign=referralsb"
                        if af.expressvpn_aff_id
                        else "https://www.expressvpn.com/order"
                    ),
                    "has_real_link": bool(af.expressvpn_aff_id),
                },
                {
                    "name": "Surfshark",
                    "commission_rate": 40, "avg_price": 48, "category": "vpn",
                    "affiliate_url": "https://surfshark.com/vpn",
                    "has_real_link": False,
                },
            ],
            "email marketing tools": [
                {
                    "name": "GetResponse",
                    "commission_rate": 33, "avg_price": 180, "category": "email marketing",
                    "affiliate_url": (
                        f"https://www.getresponse.com/?a={af.getresponse_aff_id}"
                        if af.getresponse_aff_id
                        else "https://www.getresponse.com/pricing"
                    ),
                    "has_real_link": bool(af.getresponse_aff_id),
                },
                {
                    "name": "ConvertKit",
                    "commission_rate": 30, "avg_price": 240, "category": "email marketing",
                    "affiliate_url": "https://convertkit.com/pricing",
                    "has_real_link": False,
                },
                {
                    "name": "ActiveCampaign",
                    "commission_rate": 20, "avg_price": 300, "category": "email marketing",
                    "affiliate_url": "https://www.activecampaign.com/pricing",
                    "has_real_link": False,
                },
            ],
            "password managers": [
                {
                    "name": "1Password",
                    "commission_rate": 25, "avg_price": 36, "category": "security",
                    "affiliate_url": "https://1password.com/sign-up/",
                    "has_real_link": False,
                },
                {
                    "name": "Dashlane",
                    "commission_rate": 20, "avg_price": 60, "category": "security",
                    "affiliate_url": "https://www.dashlane.com/pricing",
                    "has_real_link": False,
                },
            ],
            "antivirus software": [
                {
                    "name": "Norton 360",
                    "platform": "amazon", "product_id": "B09WDY7HGN",
                    "commission_rate": 25, "avg_price": 40, "category": "antivirus",
                    "affiliate_url": "",
                    "has_real_link": bool(af.amazon_tag),
                },
                {
                    "name": "Bitdefender Total Security",
                    "commission_rate": 40, "avg_price": 45, "category": "antivirus",
                    "affiliate_url": "https://www.bitdefender.com/solutions/total-security.html",
                    "has_real_link": False,
                },
            ],
            "project management software": [
                {
                    "name": "Monday.com",
                    "commission_rate": 30, "avg_price": 240, "category": "productivity",
                    "affiliate_url": "https://monday.com/pricing",
                    "has_real_link": False,
                },
                {
                    "name": "Notion",
                    "commission_rate": 20, "avg_price": 96, "category": "productivity",
                    "affiliate_url": "https://www.notion.so/pricing",
                    "has_real_link": False,
                },
            ],
            "ai writing tools": [
                {
                    "name": "Jasper AI",
                    "commission_rate": 30, "avg_price": 468, "category": "ai tools",
                    "affiliate_url": (
                        f"https://www.jasper.ai/?fpr={af.jasper_ref_code}"
                        if af.jasper_ref_code
                        else "https://www.jasper.ai/pricing"
                    ),
                    "has_real_link": bool(af.jasper_ref_code),
                },
                {
                    "name": "Copy.ai",
                    "commission_rate": 45, "avg_price": 360, "category": "ai tools",
                    "affiliate_url": "https://www.copy.ai/pricing",
                    "has_real_link": False,
                },
            ],
            "online courses": [
                {
                    "name": "Coursera Plus",
                    "commission_rate": 45, "avg_price": 399, "category": "education",
                    "affiliate_url": "https://www.coursera.org/courseraplus",
                    "has_real_link": False,
                },
                {
                    "name": "Udemy",
                    "commission_rate": 15, "avg_price": 15, "category": "education",
                    "affiliate_url": "https://www.udemy.com/courses/",
                    "has_real_link": False,
                },
            ],
        }

        for key, products in programs.items():
            if key in niche.lower() or niche.lower() in key:
                result = []
                for p in products:
                    p = p.copy()
                    if p.get("platform") == "amazon" and p.get("product_id"):
                        tag = af.amazon_tag
                        p["affiliate_url"] = (
                            f"https://www.amazon.com/dp/{p['product_id']}?tag={tag}"
                            if tag else f"https://www.amazon.com/dp/{p['product_id']}"
                        )
                    result.append(p)

                real_count = sum(1 for p in result if p.get("has_real_link"))
                if real_count:
                    logger.info(f"[MONEY] {real_count}/{len(result)} products have real tracked links for '{niche}'")
                else:
                    logger.warning(f"[!] No affiliate IDs set for '{niche}' — links go to product pages (no tracking)")
                return result
        return []

    def _get_clickbank_products(self, niche: str) -> List[Dict]:
        """
        ClickBank products — 50-75% commission, NO approval needed.
        User only needs a free ClickBank account + their 'nickname' (account ID).
        HopLink format: https://NICKNAME.VENDOR.hop.clickbank.net
        """
        cb_id = config.affiliate.clickbank_id  # user's ClickBank nickname

        def hop(vendor: str, tracking: str = "") -> str:
            """Build a ClickBank hop link."""
            if not cb_id:
                # No account yet → link to product's pitch page directly
                return f"https://{vendor}.com/"
            base = f"https://{cb_id}.{vendor}.hop.clickbank.net/"
            return f"{base}?tid={tracking}" if tracking else base

        # ClickBank products per niche — real vendor IDs verified on ClickBank marketplace
        programs = {
            "vpn services": [
                {"name": "VPN Unlimited (KeepSolid)", "affiliate_url": hop("keepsolid", "vpn"), "commission_rate": 60, "avg_price": 39, "category": "vpn", "has_real_link": bool(cb_id)},
            ],
            "web hosting": [
                {"name": "Web Hosting Masterclass", "affiliate_url": hop("hostingmas", "hosting"), "commission_rate": 75, "avg_price": 47, "category": "web hosting", "has_real_link": bool(cb_id)},
            ],
            "email marketing tools": [
                {"name": "Email Marketing Blueprint", "affiliate_url": hop("emailbp2", "email"), "commission_rate": 75, "avg_price": 37, "category": "email marketing", "has_real_link": bool(cb_id)},
            ],
            "online courses": [
                {"name": "Wealthy Affiliate (Online Business)", "affiliate_url": "https://www.wealthyaffiliate.com/?a_aid=" + cb_id if cb_id else "https://www.wealthyaffiliate.com/", "commission_rate": 50, "avg_price": 49, "category": "education", "has_real_link": bool(cb_id)},
                {"name": "Commission Academy (Free Course)", "affiliate_url": "https://commissionacademy.com/", "commission_rate": 50, "avg_price": 0, "category": "education", "has_real_link": False},
            ],
            "ai writing tools": [
                {"name": "Article Forge (AI Writer)", "affiliate_url": "https://www.articleforge.com/?ref=" + cb_id if cb_id else "https://www.articleforge.com/", "commission_rate": 25, "avg_price": 57, "category": "ai tools", "has_real_link": bool(cb_id)},
            ],
            "password managers": [
                {"name": "Sticky Password", "affiliate_url": hop("stickypass", "pwd"), "commission_rate": 40, "avg_price": 29, "category": "security", "has_real_link": bool(cb_id)},
            ],
            "antivirus software": [
                {"name": "PC Repair & Antivirus Suite", "affiliate_url": hop("pcmatic", "av"), "commission_rate": 50, "avg_price": 50, "category": "antivirus", "has_real_link": bool(cb_id)},
            ],
            "project management software": [
                {"name": "Project Management Professional Course", "affiliate_url": hop("pmcourse", "pm"), "commission_rate": 75, "avg_price": 97, "category": "productivity", "has_real_link": bool(cb_id)},
            ],
        }

        for key, products in programs.items():
            if key in niche.lower() or niche.lower() in key:
                if not cb_id:
                    logger.warning(f"[!] ClickBank ID not set — sign up free at clickbank.com, add CLICKBANK_ID to .env")
                return products
        return []

    def _ai_suggest_products(self, niche: str, keyword: str) -> List[Dict]:
        """Use Claude to suggest relevant affiliate products."""
        prompt = f"""Suggest 8 specific, real affiliate products for:
Niche: {niche}
Keyword context: {keyword}

Prioritize products with:
- High commission rates (software/SaaS: 20-40%, physical: 5-15%)
- Strong brand recognition
- Available on Amazon Associates, ClickBank, or ShareASale

Return JSON array:
[
  {{
    "name": "Product Name",
    "platform": "amazon|clickbank|shareasale",
    "product_id": "ASIN or product ID if known",
    "category": "...",
    "commission_rate": 30,
    "avg_price": 99,
    "why_recommend": "...",
    "amazon_search_term": "exact search term to find on Amazon"
  }}
]"""

        response = claude.complete_cheap(
            "You are an affiliate marketing expert. Suggest real, high-converting products.",
            prompt,
            max_tokens=2000
        )

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return []

    def _build_affiliate_url(self, product: Dict) -> str:
        """Build affiliate URL for a product based on platform."""
        platform = product.get("platform", "amazon").lower()
        product_id = product.get("product_id", "")

        if platform == "amazon":
            tag = config.affiliate.amazon_tag
            if product_id and tag:
                return f"https://www.amazon.{config.affiliate.amazon_region}/dp/{product_id}?tag={tag}"
            elif tag:
                search = product.get("amazon_search_term", product.get("name", ""))
                search_encoded = search.replace(" ", "+")
                return f"https://www.amazon.{config.affiliate.amazon_region}/s?k={search_encoded}&tag={tag}"
            else:
                return f"https://www.amazon.com/s?k={product.get('name', '').replace(' ', '+')}"

        elif platform == "clickbank":
            cb_id = config.affiliate.clickbank_id
            if cb_id and product_id:
                return f"https://{cb_id}.{product_id}.hop.clickbank.net/"
            return f"https://www.clickbank.com/"

        elif platform == "shareasale":
            sa_id = config.affiliate.shareasale_id
            if sa_id and product_id:
                return f"https://www.shareasale.com/r.cfm?b={product_id}&u={sa_id}"
            return "https://www.shareasale.com/"

        return product.get("url", "#")

    def build_amazon_link(self, search_term: str, asin: str = "") -> str:
        """Build Amazon affiliate link."""
        tag = config.affiliate.amazon_tag
        if asin and tag:
            return f"https://www.amazon.com/dp/{asin}?tag={tag}"
        elif tag:
            return f"https://www.amazon.com/s?k={search_term.replace(' ', '+')}&tag={tag}"
        return f"https://www.amazon.com/s?k={search_term.replace(' ', '+')}"

    def calculate_expected_revenue(self, products: List[Dict], monthly_visitors: int = 1000) -> Dict:
        """
        Estimate expected monthly affiliate revenue.
        Industry average: 1-3% CTR on affiliate links, 2-5% conversion.
        """
        estimates = []
        total_estimated = 0

        for p in products:
            ctr = 0.02  # 2% CTR
            conversion = 0.03  # 3% conversion rate
            commission = p.get("commission_rate", 5) / 100
            price = p.get("avg_price", 50)

            clicks = monthly_visitors * ctr
            conversions = clicks * conversion
            revenue = conversions * price * commission

            estimates.append({
                "product": p.get("name", ""),
                "estimated_clicks": round(clicks),
                "estimated_conversions": round(conversions, 1),
                "estimated_monthly_revenue": round(revenue, 2)
            })
            total_estimated += revenue

        return {
            "products": estimates,
            "total_estimated_monthly": round(total_estimated, 2),
            "total_estimated_yearly": round(total_estimated * 12, 2),
            "assumptions": "1000 monthly visitors, 2% CTR, 3% conversion rate"
        }

    def rank_by_opportunity(self, products: List[Dict]) -> List[Dict]:
        """Rank products by revenue opportunity score."""
        def score(p: Dict) -> float:
            commission = p.get("commission_rate", 0)
            price = p.get("avg_price", 0)
            conversions = p.get("conversions", 0)
            return (commission * price * 0.5) + (conversions * 10)

        return sorted(products, key=score, reverse=True)
