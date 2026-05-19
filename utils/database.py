"""
SQLite database manager - zero cost, zero setup.
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from config import config

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    conn = sqlite3.connect(config.database.path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create all tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                niche TEXT,
                search_volume INTEGER DEFAULT 0,
                difficulty INTEGER DEFAULT 0,
                buyer_intent_score REAL DEFAULT 0,
                content_type TEXT,
                status TEXT DEFAULT 'pending',  -- pending | in_progress | published | skip
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword_id INTEGER REFERENCES keywords(id),
                niche TEXT DEFAULT '',
                title TEXT NOT NULL,
                slug TEXT,
                content TEXT,
                meta_description TEXT DEFAULT '',
                word_count INTEGER DEFAULT 0,
                wp_post_id INTEGER,
                wp_url TEXT,
                affiliate_links_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'draft',  -- draft | published | needs_update
                seo_score INTEGER DEFAULT 0,
                published_at TEXT,
                updated_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS affiliate_products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,  -- amazon | clickbank | shareasale
                product_id TEXT,
                affiliate_url TEXT NOT NULL,
                commission_rate REAL DEFAULT 0,
                avg_price REAL DEFAULT 0,
                category TEXT,
                niche TEXT,
                conversion_score REAL DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER REFERENCES articles(id),
                date TEXT NOT NULL,
                organic_clicks INTEGER DEFAULT 0,
                affiliate_clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                avg_position REAL DEFAULT 0,
                impressions INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS niches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                total_articles INTEGER DEFAULT 0,
                total_revenue REAL DEFAULT 0,
                avg_commission REAL DEFAULT 0,
                priority INTEGER DEFAULT 5,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_keywords_status ON keywords(status);
            CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
            CREATE INDEX IF NOT EXISTS idx_performance_date ON performance(date);
        """)
        # Migrate existing DBs that are missing new columns
        _migrate_db(conn)
    logger.info("Database initialized.")


def _migrate_db(conn):
    """Add new columns to existing tables without breaking old data."""
    existing = {r[1] for r in conn.execute("PRAGMA table_info(articles)")}
    migrations = [
        ("niche",            "ALTER TABLE articles ADD COLUMN niche TEXT DEFAULT ''"),
        ("meta_description", "ALTER TABLE articles ADD COLUMN meta_description TEXT DEFAULT ''"),
    ]
    for col, sql in migrations:
        if col not in existing:
            conn.execute(sql)
            logger.info(f"DB migrated: added articles.{col}")


class KeywordDB:
    @staticmethod
    def add(keyword: str, niche: str, search_volume: int, difficulty: int,
            buyer_intent_score: float, content_type: str) -> int:
        with get_db() as conn:
            try:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO keywords
                       (keyword, niche, search_volume, difficulty, buyer_intent_score, content_type)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (keyword, niche, search_volume, difficulty, buyer_intent_score, content_type)
                )
                return cur.lastrowid
            except Exception as e:
                logger.error(f"Error adding keyword: {e}")
                return 0

    @staticmethod
    def get_pending(limit: int = 10) -> List[Dict]:
        """Round-robin across niches — pick 1 top keyword per niche, cycle through all niches."""
        with get_db() as conn:
            # Get distinct niches that still have pending keywords
            niches = [r[0] for r in conn.execute(
                "SELECT DISTINCT niche FROM keywords WHERE status='pending' AND niche IS NOT NULL ORDER BY niche"
            ).fetchall()]

            if not niches:
                return []

            # Pick the best keyword from each niche, rotating up to `limit` total
            results = []
            per_niche = max(1, limit // max(len(niches), 1))
            for niche in niches:
                rows = conn.execute(
                    """SELECT * FROM keywords WHERE status='pending' AND niche=?
                       ORDER BY buyer_intent_score DESC, search_volume DESC
                       LIMIT ?""",
                    (niche, per_niche)
                ).fetchall()
                results.extend([dict(r) for r in rows])
                if len(results) >= limit:
                    break

            # Sort the combined list by opportunity, return top `limit`
            results.sort(key=lambda x: (x.get("buyer_intent_score", 0), x.get("search_volume", 0)), reverse=True)
            return results[:limit]

    @staticmethod
    def update_status(keyword_id: int, status: str):
        with get_db() as conn:
            conn.execute("UPDATE keywords SET status = ? WHERE id = ?", (status, keyword_id))


class ArticleDB:
    @staticmethod
    def add(keyword_id: int, title: str, slug: str, content: str,
            word_count: int, affiliate_links_count: int,
            niche: str = "", meta_description: str = "") -> int:
        with get_db() as conn:
            cur = conn.execute(
                """INSERT INTO articles
                   (keyword_id, niche, title, slug, content, meta_description,
                    word_count, affiliate_links_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (keyword_id, niche, title, slug, content, meta_description,
                 word_count, affiliate_links_count)
            )
            return cur.lastrowid

    @staticmethod
    def update_published(article_id: int, wp_post_id: int, wp_url: str, seo_score: int):
        with get_db() as conn:
            conn.execute(
                """UPDATE articles SET wp_post_id=?, wp_url=?, seo_score=?,
                   status='published', published_at=CURRENT_TIMESTAMP
                   WHERE id=?""",
                (wp_post_id, wp_url, seo_score, article_id)
            )

    @staticmethod
    def get_needs_update(days_old: int = 90) -> List[Dict]:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT a.*, k.keyword, k.niche as kw_niche FROM articles a
                   JOIN keywords k ON a.keyword_id = k.id
                   WHERE a.status = 'published'
                   AND julianday('now') - julianday(a.published_at) > ?
                   ORDER BY a.seo_score ASC""",
                (days_old,)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def get_all_published() -> List[Dict]:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT a.*, COALESCE(NULLIF(a.niche,''), k.niche, '') as niche
                   FROM articles a
                   LEFT JOIN keywords k ON a.keyword_id = k.id
                   WHERE a.status = 'published'
                   ORDER BY a.published_at DESC"""
            ).fetchall()
            return [dict(r) for r in rows]


class AffiliateProductDB:
    @staticmethod
    def add(name: str, platform: str, product_id: str, affiliate_url: str,
            commission_rate: float, avg_price: float, category: str, niche: str) -> int:
        with get_db() as conn:
            cur = conn.execute(
                """INSERT OR IGNORE INTO affiliate_products
                   (name, platform, product_id, affiliate_url, commission_rate, avg_price, category, niche)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, platform, product_id, affiliate_url, commission_rate, avg_price, category, niche)
            )
            return cur.lastrowid

    @staticmethod
    def get_by_niche(niche: str, limit: int = 10) -> List[Dict]:
        with get_db() as conn:
            rows = conn.execute(
                """SELECT * FROM affiliate_products
                   WHERE niche = ? AND active = 1
                   ORDER BY commission_rate DESC, conversion_score DESC
                   LIMIT ?""",
                (niche, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def record_click(product_id: int):
        with get_db() as conn:
            conn.execute(
                "UPDATE affiliate_products SET clicks = clicks + 1 WHERE id = ?",
                (product_id,)
            )


class PerformanceDB:
    @staticmethod
    def add(article_id: int, date: str, organic_clicks: int = 0,
            affiliate_clicks: int = 0, conversions: int = 0,
            revenue: float = 0, avg_position: float = 0, impressions: int = 0):
        with get_db() as conn:
            conn.execute(
                """INSERT INTO performance
                   (article_id, date, organic_clicks, affiliate_clicks,
                    conversions, revenue, avg_position, impressions)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (article_id, date, organic_clicks, affiliate_clicks,
                 conversions, revenue, avg_position, impressions)
            )

    @staticmethod
    def get_summary() -> Dict:
        with get_db() as conn:
            row = conn.execute(
                """SELECT
                    SUM(organic_clicks) as total_clicks,
                    SUM(affiliate_clicks) as total_affiliate_clicks,
                    SUM(conversions) as total_conversions,
                    SUM(revenue) as total_revenue
                   FROM performance"""
            ).fetchone()
            return dict(row) if row else {}
