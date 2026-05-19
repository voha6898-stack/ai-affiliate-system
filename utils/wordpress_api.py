"""
WordPress REST API Publisher
- Auto-publishes articles to WordPress
- Sets SEO meta tags (Yoast/RankMath compatible)
- Manages categories and tags
- Updates existing posts
"""
import json
import logging
import requests
import base64
from typing import Dict, Optional, List
from config import config

logger = logging.getLogger(__name__)


class WordPressPublisher:
    """
    Publishes articles directly to WordPress via REST API.
    Supports Yoast SEO and RankMath meta tags.
    """

    def __init__(self):
        self.base_url = config.wordpress.site_url.rstrip("/")
        self.api_url = f"{self.base_url}/wp-json/wp/v2"
        self.auth = self._build_auth()
        self._category_cache: Dict[str, int] = {}
        self._tag_cache: Dict[str, int] = {}

    def _build_auth(self) -> str:
        """Build Basic auth header from WP credentials."""
        credentials = f"{config.wordpress.username}:{config.wordpress.app_password}"
        return base64.b64encode(credentials.encode()).decode()

    def _headers(self) -> Dict:
        return {
            "Authorization": f"Basic {self.auth}",
            "Content-Type": "application/json"
        }

    def publish(self, article: Dict) -> Dict:
        """
        Publish an article to WordPress.

        Args:
            article: Dict with title, content, meta_description, slug, keyword, niche

        Returns:
            Dict with wp_post_id, wp_url, seo_score
        """
        if not self.base_url:
            logger.warning("WordPress not configured. Saving article locally.")
            return self._save_locally(article)

        logger.info(f"Publishing to WordPress: {article.get('title', '')}")

        try:
            # Get or create category
            category_id = self._get_or_create_category(article.get("niche", "Reviews"))

            # Get or create tags from keyword
            tag_ids = self._get_or_create_tags(article.get("keyword", ""))

            # Build post payload
            payload = {
                "title": article["title"],
                "content": article["content"],
                "slug": article.get("slug", ""),
                "status": config.wordpress.default_status,
                "categories": [category_id],
                "tags": tag_ids,
                "meta": {
                    # Yoast SEO meta
                    "_yoast_wpseo_metadesc": article.get("meta_description", ""),
                    "_yoast_wpseo_focuskw": article.get("keyword", ""),
                    # RankMath meta
                    "rank_math_description": article.get("meta_description", ""),
                    "rank_math_focus_keyword": article.get("keyword", ""),
                }
            }

            resp = requests.post(
                f"{self.api_url}/posts",
                headers=self._headers(),
                json=payload,
                timeout=30
            )
            resp.raise_for_status()

            post_data = resp.json()
            wp_post_id = post_data.get("id")
            wp_url = post_data.get("link", "")

            # Calculate basic SEO score
            seo_score = self._calculate_seo_score(article)

            logger.info(f"Published successfully: {wp_url}")
            return {
                "success": True,
                "wp_post_id": wp_post_id,
                "wp_url": wp_url,
                "seo_score": seo_score
            }

        except requests.exceptions.ConnectionError:
            logger.warning("Cannot connect to WordPress. Saving locally.")
            return self._save_locally(article)

        except requests.exceptions.HTTPError as e:
            logger.error(f"WordPress HTTP error: {e.response.status_code} - {e.response.text[:200]}")
            return self._save_locally(article)

        except Exception as e:
            logger.error(f"WordPress publish error: {e}")
            return self._save_locally(article)

    def update_post(self, wp_post_id: int, article: Dict) -> Dict:
        """Update an existing WordPress post."""
        if not self.base_url:
            return {"success": False, "error": "WordPress not configured"}

        try:
            payload = {
                "title": article.get("title", ""),
                "content": article.get("content", ""),
                "meta": {
                    "_yoast_wpseo_metadesc": article.get("meta_description", ""),
                }
            }

            resp = requests.post(
                f"{self.api_url}/posts/{wp_post_id}",
                headers=self._headers(),
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            return {"success": True, "wp_post_id": wp_post_id}

        except Exception as e:
            logger.error(f"WordPress update error: {e}")
            return {"success": False, "error": str(e)}

    def _get_or_create_category(self, name: str) -> int:
        """Get existing category ID or create new one."""
        if name in self._category_cache:
            return self._category_cache[name]

        try:
            # Search existing
            resp = requests.get(
                f"{self.api_url}/categories",
                params={"search": name},
                headers=self._headers(),
                timeout=10
            )
            categories = resp.json()
            if categories and isinstance(categories, list):
                self._category_cache[name] = categories[0]["id"]
                return categories[0]["id"]

            # Create new
            resp = requests.post(
                f"{self.api_url}/categories",
                headers=self._headers(),
                json={"name": name},
                timeout=10
            )
            resp.raise_for_status()
            cat_id = resp.json()["id"]
            self._category_cache[name] = cat_id
            return cat_id

        except Exception:
            return 1  # Default category

    def _get_or_create_tags(self, keyword: str) -> List[int]:
        """Create tags from keyword words."""
        if not keyword:
            return []

        tag_ids = []
        # Use keyword + "review" + "2026" as tags
        tag_names = [keyword, f"{keyword} review", "2026"]

        for tag_name in tag_names[:3]:
            if tag_name in self._tag_cache:
                tag_ids.append(self._tag_cache[tag_name])
                continue
            try:
                resp = requests.post(
                    f"{self.api_url}/tags",
                    headers=self._headers(),
                    json={"name": tag_name},
                    timeout=10
                )
                if resp.status_code in (200, 201):
                    tag_id = resp.json()["id"]
                    self._tag_cache[tag_name] = tag_id
                    tag_ids.append(tag_id)
                elif resp.status_code == 400:
                    # Tag exists, find it
                    search_resp = requests.get(
                        f"{self.api_url}/tags",
                        params={"search": tag_name},
                        headers=self._headers(),
                        timeout=10
                    )
                    tags = search_resp.json()
                    if tags:
                        tag_ids.append(tags[0]["id"])
            except Exception:
                pass

        return tag_ids

    def _calculate_seo_score(self, article: Dict) -> int:
        """Calculate basic SEO score (0-100)."""
        score = 0
        content = article.get("content", "")
        keyword = article.get("keyword", "").lower()
        title = article.get("title", "").lower()

        # Keyword in title
        if keyword in title:
            score += 20

        # Meta description present
        if article.get("meta_description"):
            score += 15

        # Word count
        words = len(content.split())
        if words >= 2000:
            score += 20
        elif words >= 1500:
            score += 10

        # Has H2 tags
        if "<h2" in content.lower():
            score += 15

        # Has affiliate links
        if "affiliate-link" in content:
            score += 10

        # Has images (img tags)
        if "<img" in content.lower():
            score += 10

        # Has FAQ section
        if "faq" in content.lower() or "frequently asked" in content.lower():
            score += 10

        return min(score, 100)

    def _save_locally(self, article: Dict) -> Dict:
        """Save article to local file when WordPress is unavailable."""
        import os
        os.makedirs("data/articles", exist_ok=True)

        slug = article.get("slug", "article")
        filename = f"data/articles/{slug}.html"

        html_content = f"""<!DOCTYPE html>
<html>
<head>
<title>{article.get('title', '')}</title>
<meta name="description" content="{article.get('meta_description', '')}">
</head>
<body>
{article.get('content', '')}
</body>
</html>"""

        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)

        seo_score = self._calculate_seo_score(article)
        logger.info(f"Saved locally: {filename}")

        return {
            "success": True,
            "wp_post_id": 0,
            "wp_url": filename,
            "seo_score": seo_score,
            "local": True
        }

    def test_connection(self) -> bool:
        """Test WordPress API connection."""
        if not self.base_url:
            return False
        try:
            resp = requests.get(f"{self.api_url}/", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
