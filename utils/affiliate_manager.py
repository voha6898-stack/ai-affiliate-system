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
        Combines database products with AI-suggested products.
        """
        # Check database first
        db_products = AffiliateProductDB.get_by_niche(niche, limit=8)

        if len(db_products) >= 5:
            return db_products

        # AI suggests products if database is sparse
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
