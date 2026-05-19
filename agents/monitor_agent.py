"""
Performance Monitor & Optimizer Agent
- Tracks article performance (clicks, rankings, revenue)
- Identifies underperforming content
- Auto-suggests and applies optimizations
- Generates revenue reports
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import config
from utils.claude_client import claude
from utils.database import ArticleDB, PerformanceDB, KeywordDB

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an SEO performance analyst and content optimization expert.
You analyze content performance data and provide specific, actionable recommendations
to improve rankings, traffic, and affiliate revenue.

Focus on:
- Why content might be underperforming
- Specific changes to improve CTR and rankings
- Affiliate link optimization for higher conversions
- Content freshness and update recommendations

Always be specific and data-driven."""


class MonitorAgent:
    """
    Monitors performance and triggers optimizations automatically.
    """

    def run_daily_check(self) -> Dict:
        """
        Daily performance check and optimization cycle.
        Returns summary of actions taken.
        """
        logger.info("Running daily performance check...")
        actions = []

        # Check articles needing update
        old_articles = ArticleDB.get_needs_update(days_old=config.scheduler.content_refresh_days)
        if old_articles:
            actions.append(f"Found {len(old_articles)} articles needing refresh")
            for article in old_articles[:3]:  # Process top 3 per day
                self._refresh_article(article)
                actions.append(f"Refreshed: {article.get('title', '')[:50]}")

        # Get performance summary
        summary = PerformanceDB.get_summary()

        # Generate optimization recommendations
        published = ArticleDB.get_all_published()
        if published:
            recommendations = self._analyze_portfolio(published)
            actions.append(f"Generated {len(recommendations)} optimization recommendations")

        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "articles_refreshed": len(old_articles[:3]),
            "total_published": len(ArticleDB.get_all_published()),
            "revenue_summary": summary,
            "actions": actions,
        }

    def _refresh_article(self, article: Dict):
        """Refresh an old article with updated content and data."""
        logger.info(f"Refreshing article: {article.get('title', '')[:50]}")

        prompt = f"""Article to refresh:
Title: {article.get('title', '')}
Keyword: {article.get('keyword', '')}
Published: {article.get('published_at', '')}

Generate an update plan:
1. What data/stats need updating for 2026
2. New products to add or replace
3. New sections to add based on emerging trends
4. Title improvement suggestions

Return JSON:
{{
  "new_title": "...",
  "sections_to_update": ["...", "..."],
  "sections_to_add": ["...", "..."],
  "data_to_refresh": ["...", "..."],
  "new_products_to_add": ["...", "..."]
}}"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=1000)

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                plan = json.loads(response[start:end])
                logger.info(f"Refresh plan: {plan.get('new_title', 'same title')}")
                return plan
        except json.JSONDecodeError:
            pass

    def _analyze_portfolio(self, articles: List[Dict]) -> List[Dict]:
        """Analyze full article portfolio and suggest improvements."""
        if not articles:
            return []

        portfolio_summary = []
        for a in articles[:20]:
            portfolio_summary.append({
                "title": a.get("title", "")[:60],
                "word_count": a.get("word_count", 0),
                "seo_score": a.get("seo_score", 0),
                "affiliate_links": a.get("affiliate_links_count", 0),
                "days_old": (datetime.now() - datetime.fromisoformat(
                    a.get("published_at") or datetime.now().isoformat()
                )).days if a.get("published_at") else 0
            })

        prompt = f"""Analyze this content portfolio and provide optimization recommendations:

Portfolio ({len(articles)} articles):
{json.dumps(portfolio_summary[:10], indent=2)}

Identify:
1. Articles with low SEO scores (< 60) — what to fix
2. Articles with too few affiliate links (< 3) — where to add
3. Articles that are too short (< 1800 words) — what to expand
4. Articles older than 90 days — prioritize for refresh

Return top 5 actionable recommendations as JSON:
[
  {{
    "priority": 1,
    "article_title": "...",
    "issue": "...",
    "recommendation": "...",
    "expected_impact": "low|medium|high"
  }}
]"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=1500)

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return []

    def generate_revenue_report(self) -> str:
        """Generate a human-readable revenue and performance report."""
        summary = PerformanceDB.get_summary()
        articles = ArticleDB.get_all_published()

        cost_summary = claude.get_cost_summary()

        report = f"""
╔══════════════════════════════════════════════════════════╗
║           AI AFFILIATE SYSTEM — PERFORMANCE REPORT       ║
║                  {datetime.now().strftime('%Y-%m-%d %H:%M')}                      ║
╚══════════════════════════════════════════════════════════╝

📊 CONTENT STATS
  Total Published Articles : {len(articles)}
  Total Organic Clicks     : {summary.get('total_clicks', 0):,}
  Affiliate Link Clicks    : {summary.get('total_affiliate_clicks', 0):,}
  Conversions              : {summary.get('total_conversions', 0):,}
  Total Revenue            : ${summary.get('total_revenue', 0):.2f}

💰 API COST OPTIMIZATION
  Total API Cost           : ${cost_summary['total_cost_usd']:.4f}
  Estimated Savings        : ${cost_summary['estimated_savings_usd']:.4f}
  Cache Hit Rate           : {cost_summary['cache_hit_rate']}%
  Input Tokens Used        : {cost_summary['input_tokens']:,}
  Output Tokens Used       : {cost_summary['output_tokens']:,}

🎯 TOP PERFORMING CONTENT
"""
        for a in articles[:5]:
            report += f"  • {a.get('title', '')[:55]:<55} | SEO: {a.get('seo_score', 0)}/100\n"

        report += f"""
⚡ SYSTEM STATUS
  Status: RUNNING AUTOMATICALLY
  Next publish: {(datetime.now() + timedelta(hours=4)).strftime('%H:%M')}
"""
        return report

    def record_performance(
        self,
        article_id: int,
        organic_clicks: int = 0,
        affiliate_clicks: int = 0,
        conversions: int = 0,
        revenue: float = 0.0,
        avg_position: float = 0.0,
        impressions: int = 0
    ):
        """Record daily performance metrics for an article."""
        PerformanceDB.add(
            article_id=article_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            organic_clicks=organic_clicks,
            affiliate_clicks=affiliate_clicks,
            conversions=conversions,
            revenue=revenue,
            avg_position=avg_position,
            impressions=impressions
        )
