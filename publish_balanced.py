"""
publish_balanced.py — Niche-balanced publisher.
Prioritizes niches with fewest articles, weighted by commission rate.
Fixes the imbalance: web hosting/VPN/password managers had 0 articles.

Usage: python publish_balanced.py [n_articles=3]
"""
import sys
import time
import logging

from config import config
from utils.database import get_db, init_db, KeywordDB, ArticleDB
from main import AffiliateAISystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Commission weight per niche — higher = publish first when under-represented
COMMISSION_WEIGHT = {
    "web hosting":                10,  # Hostinger $60+, Bluehost $65+
    "vpn services":               9,   # NordVPN $40–50/sale
    "email marketing tools":      8,   # GetResponse 33% recurring
    "ai writing tools":           7,   # Jasper 30% recurring
    "password managers":          6,   # 1Password 25% recurring
    "antivirus software":         6,   # Bitdefender 40%
    "project management software": 5,
    "online courses":             4,
}


def niche_article_counts() -> dict:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT niche, COUNT(*) as cnt FROM articles "
            "WHERE status='published' AND niche != '' GROUP BY niche"
        ).fetchall()
    return {r["niche"]: r["cnt"] for r in rows}


def pick_keywords(n: int) -> list:
    """
    Select n keywords from most-underrepresented niches.
    Priority score = commission_weight × 10 / max(article_count, 0.5)
    A niche with 0 articles and high commission gets picked first.
    """
    counts = niche_article_counts()

    logger.info("Current article counts per niche:")
    for niche in config.target_niches:
        logger.info(f"  {niche}: {counts.get(niche, 0)} articles")

    priority = []
    for niche in config.target_niches:
        cnt = counts.get(niche, 0)
        w = COMMISSION_WEIGHT.get(niche, 5)
        score = (w * 10) / max(cnt, 0.5)
        priority.append((score, niche, cnt))
    priority.sort(reverse=True)

    logger.info("\nPublishing priority:")
    for score, niche, cnt in priority:
        logger.info(f"  [{score:6.1f}] {niche} ({cnt} articles)")

    selected = []
    with get_db() as conn:
        for _, niche, _ in priority:
            if len(selected) >= n:
                break
            row = conn.execute(
                """SELECT * FROM keywords
                   WHERE status='pending' AND niche=?
                   ORDER BY buyer_intent_score DESC, search_volume DESC
                   LIMIT 1""",
                (niche,),
            ).fetchone()
            if row:
                selected.append(dict(row))
                logger.info(f"  → [{niche}] {row['keyword']}")

    return selected


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3

    init_db()
    system = AffiliateAISystem()

    keywords = pick_keywords(n)
    if not keywords:
        logger.error("No pending keywords. Run: python main.py research")
        return

    published = 0
    for kw_data in keywords:
        keyword = kw_data["keyword"]
        niche = kw_data["niche"]
        keyword_id = kw_data["id"]

        logger.info(f"\n{'='*55}")
        logger.info(f"Keyword : {keyword}")
        logger.info(f"Niche   : {niche}")
        logger.info(f"Intent  : {kw_data.get('buyer_intent_score', 0)}/10")

        try:
            brief = system.competitor_agent.analyze(keyword, niche)
            products = system.affiliate_manager.get_products_for_niche(niche, keyword)
            article = system.content_agent.generate(
                keyword=keyword,
                keyword_id=keyword_id,
                niche=niche,
                content_brief=brief,
                affiliate_products=products,
            )
            result = system.publisher.publish(article)

            if result.get("success"):
                ArticleDB.update_published(
                    article_id=article["article_id"],
                    wp_post_id=result.get("wp_post_id", 0),
                    wp_url=result.get("wp_url", ""),
                    seo_score=result.get("seo_score", 0),
                )
                KeywordDB.update_status(keyword_id, "published")
                published += 1
                logger.info(
                    f"[OK] {article['title'][:65]}\n"
                    f"     {article['word_count']} words · "
                    f"{article['affiliate_links_count']} affiliate links"
                )
            else:
                logger.error(f"[!!] Publish failed: {article.get('title', keyword)}")

        except Exception as e:
            logger.error(f"[!!] Error '{keyword}': {e}", exc_info=True)

        if published < n:
            time.sleep(3)

    logger.info(f"\n{'='*55}")
    logger.info(f"Done: {published}/{n} articles published")


if __name__ == "__main__":
    main()
