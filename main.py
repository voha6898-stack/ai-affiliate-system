"""
AI Content + Affiliate Automation System — Main Orchestrator

This is the brain that coordinates all agents:
1. Research keywords -> 2. Analyze competitors -> 3. Generate content
4. Insert affiliate links -> 5. Publish to Blog -> 6. Monitor & optimize

Run modes:
  python main.py setup     — Initial setup and validation
  python main.py run       — Full automation cycle (publish N articles)
  python main.py research  — Only keyword research
  python main.py publish 1 — Publish N articles manually
  python main.py report    — Show performance report
  python main.py schedule  — Start continuous scheduler (3 articles/day)
"""
import sys
import logging
import time
import schedule
from datetime import datetime
from typing import Optional

from config import config
from utils.database import init_db
from utils.claude_client import claude
from utils.affiliate_manager import AffiliateManager
from utils.blog_publisher import BlogPublisher
from agents.niche_agent import NicheAgent
from agents.competitor_agent import CompetitorAgent
from agents.content_agent import ContentAgent
from agents.monitor_agent import MonitorAgent
from utils.database import KeywordDB, ArticleDB

# Setup logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(config.log_file, encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


class AffiliateAISystem:
    """
    Master orchestrator for the AI affiliate content system.
    Coordinates all agents in the correct pipeline order.
    """

    def __init__(self):
        # Initialize database
        init_db()

        # Initialize all agents
        self.niche_agent = NicheAgent()
        self.competitor_agent = CompetitorAgent()
        self.content_agent = ContentAgent()
        self.monitor_agent = MonitorAgent()
        self.affiliate_manager = AffiliateManager()
        self.publisher = BlogPublisher()

        logger.info("AI Affiliate System initialized.")

    def setup(self):
        """Initial setup: validate config, test connections, seed keywords."""
        print("\n" + "="*60)
        print("  AI CONTENT + AFFILIATE SYSTEM — SETUP")
        print("="*60)

        # Detect which AI provider is active
        from utils.ai_client import AIClient
        try:
            ai = AIClient()
            print(f"[OK] AI Provider  : {ai.provider.upper()}")
        except ValueError as e:
            print(f"[!!] {e}")
            return

        # Check blog connection
        blog_ok = self.publisher.test_connection()
        if blog_ok:
            print(f"[OK] Blog Server  : {self.publisher.blog_url}")
        else:
            print(f"[--] Blog Server  : {self.publisher.blog_url} (offline — articles saved locally)")

        # Check affiliate config
        if config.affiliate.amazon_tag:
            print(f"[OK] Amazon Tag   : {config.affiliate.amazon_tag}")
        else:
            print("[--] Amazon Tag   : not set (products will be AI-suggested)")

        # Show target niches
        print(f"\nTarget Niches ({len(config.target_niches)}):")
        for niche in config.target_niches:
            print(f"   - {niche}")

        # Run initial keyword research
        print("\nRunning initial keyword research (this may take 1-2 minutes)...")
        total = self.niche_agent.research_all_niches()
        print(f"[OK] Found {total} keywords across all niches")

        print("\n[OK] Setup complete! Run: python main.py schedule")
        print("="*60 + "\n")

    def run_one_cycle(self, max_articles: int = 3) -> int:
        """
        Run one complete automation cycle.
        Returns number of articles published.
        """
        logger.info(f"Starting automation cycle (target: {max_articles} articles)")
        published_count = 0

        # Get pending keywords sorted by opportunity
        pending = KeywordDB.get_pending(limit=max_articles * 2)

        if not pending:
            logger.info("No pending keywords. Running niche research...")
            self.niche_agent.research_all_niches()
            pending = KeywordDB.get_pending(limit=max_articles * 2)

        if not pending:
            logger.warning("No keywords found. Check your niche configuration.")
            return 0

        for kw_data in pending[:max_articles]:
            try:
                keyword = kw_data["keyword"]
                niche = kw_data["niche"]
                keyword_id = kw_data["id"]

                logger.info(f"\n{'='*50}")
                logger.info(f"Processing keyword: {keyword}")
                logger.info(f"Niche: {niche} | Opportunity score: {kw_data.get('buyer_intent_score', 0)}")

                # Step 1: Analyze competitors
                logger.info("Step 1/4: Analyzing competitors...")
                content_brief = self.competitor_agent.analyze(keyword, niche)

                # Step 2: Get affiliate products
                logger.info("Step 2/4: Getting affiliate products...")
                products = self.affiliate_manager.get_products_for_niche(niche, keyword)
                logger.info(f"Found {len(products)} affiliate products")

                # Step 3: Generate content
                logger.info("Step 3/4: Generating content...")
                article = self.content_agent.generate(
                    keyword=keyword,
                    keyword_id=keyword_id,
                    niche=niche,
                    content_brief=content_brief,
                    affiliate_products=products,
                )
                logger.info(f"Generated: {article['word_count']} words, {article['affiliate_links_count']} affiliate links")

                # Step 4: Publish
                logger.info("Step 4/4: Publishing...")
                publish_result = self.publisher.publish(article)

                if publish_result.get("success"):
                    # Update database with publish info
                    ArticleDB.update_published(
                        article_id=article["article_id"],
                        wp_post_id=publish_result.get("wp_post_id", 0),
                        wp_url=publish_result.get("wp_url", ""),
                        seo_score=publish_result.get("seo_score", 0)
                    )
                    KeywordDB.update_status(keyword_id, "published")
                    published_count += 1

                    logger.info(f"[OK] Published: {article['title']}")
                    logger.info(f"   URL: {publish_result.get('wp_url', 'local')}")
                    logger.info(f"   SEO Score: {publish_result.get('seo_score', 0)}/100")
                else:
                    logger.error(f"Failed to publish: {article['title']}")

                # Brief pause between articles (be nice to APIs)
                if published_count < max_articles:
                    time.sleep(3)

            except Exception as e:
                logger.error(f"Error processing keyword '{kw_data.get('keyword', '')}': {e}", exc_info=True)
                continue

        return published_count

    def research_only(self):
        """Run keyword research without publishing."""
        print("\nRunning keyword research for all niches...")
        total = self.niche_agent.research_all_niches()
        print(f"[OK] Research complete: {total} new keywords found")

        # Show top opportunities
        pending = KeywordDB.get_pending(limit=10)
        if pending:
            print(f"\nTop {len(pending)} keyword opportunities:")
            for i, kw in enumerate(pending, 1):
                print(f"  {i:2d}. {kw['keyword']:<45} Intent: {kw['buyer_intent_score']}/10  Vol: {kw['search_volume']:,}")

    def show_report(self):
        """Show performance report."""
        report = self.monitor_agent.generate_revenue_report()
        print(report)
        cost = claude.get_cost_summary()
        print(f"[i] API cost this session: ${cost['total_cost_usd']:.4f} (saved ${cost['estimated_savings_usd']:.4f} via caching)")

    def start_scheduler(self):
        """Start the continuous automation scheduler."""
        print("\n" + "="*60)
        print("  AI AFFILIATE SYSTEM -- AUTO SCHEDULER STARTED")
        print("="*60)
        print(f"  Publishing {config.scheduler.articles_per_day} articles/day")
        print(f"  Scheduled hours: {config.scheduler.publish_hours}")
        print(f"  Content refresh: every {config.scheduler.content_refresh_days} days")
        print(f"  Press Ctrl+C to stop")
        print("="*60 + "\n")

        # Schedule daily publishing
        for hour in config.scheduler.publish_hours:
            schedule.every().day.at(f"{hour:02d}:00").do(
                lambda: self.run_one_cycle(max_articles=1)
            )

        # Schedule daily keyword research (2am)
        schedule.every().day.at("02:00").do(self.niche_agent.research_all_niches)

        # Schedule daily monitoring (3am)
        schedule.every().day.at("03:00").do(self.monitor_agent.run_daily_check)

        # Schedule weekly report (Monday 9am)
        schedule.every().monday.at("09:00").do(self.show_report)

        logger.info("Scheduler started. Waiting for scheduled tasks...")

        while True:
            schedule.run_pending()
            time.sleep(60)


def main():
    system = AffiliateAISystem()
    args = sys.argv[1:]
    command = args[0] if args else "run"

    if command == "setup":
        system.setup()

    elif command == "run":
        n = int(args[1]) if len(args) > 1 else config.scheduler.articles_per_day
        published = system.run_one_cycle(max_articles=n)
        print(f"\n[OK] Cycle complete: {published} articles published")
        system.show_report()

    elif command == "publish":
        n = int(args[1]) if len(args) > 1 else 1
        published = system.run_one_cycle(max_articles=n)
        print(f"\n[OK] Published {published} articles")

    elif command == "research":
        system.research_only()

    elif command == "report":
        system.show_report()

    elif command == "monitor":
        result = system.monitor_agent.run_daily_check()
        print(f"\n[>>] Monitor check complete:")
        for action in result.get("actions", []):
            print(f"  - {action}")

    elif command == "schedule":
        system.start_scheduler()

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
