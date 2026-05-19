"""
Blog Publisher — dang bai len Flask blog tren Render.
Thay the WordPress khi dung hosting mien phi.
"""
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class BlogPublisher:
    """
    Dang bai len Flask blog qua REST API.
    Hoat dong voi ca local preview server va Render cloud.
    """

    def __init__(self):
        self.blog_url = os.getenv("BLOG_URL", "http://localhost:5000").rstrip("/")
        self.api_secret = os.getenv("BLOG_API_SECRET", "change-this-secret-key")
        self._auto_sync_secret()

    def _auto_sync_secret(self):
        """Tu dong lay secret tu blog neu chua co hoac con la gia tri mac dinh."""
        if self.api_secret not in ("change-this-secret-key", "", None):
            return
        try:
            resp = requests.get(f"{self.blog_url}/api/init-key", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                self.api_secret = data.get("api_secret", self.api_secret)
                # Luu vao .env de lan sau khoi dong khong can sync lai
                env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
                self._update_env(env_path, "BLOG_API_SECRET", self.api_secret)
                logger.info(f"Auto-synced BLOG_API_SECRET from {self.blog_url}")
        except Exception as e:
            logger.debug(f"Could not auto-sync secret: {e}")

    def _update_env(self, env_path: str, key: str, value: str):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            updated = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}={value}\n"
                    updated = True
                    break
            if not updated:
                lines.append(f"{key}={value}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
        except Exception:
            pass

    def publish(self, article: dict) -> dict:
        """Dang 1 bai viet len blog."""
        if not self.blog_url:
            return self._save_locally(article)

        try:
            resp = requests.post(
                f"{self.blog_url}/api/publish",
                headers={
                    "X-API-Key": self.api_secret,
                    "Content-Type": "application/json"
                },
                json={
                    "title": article.get("title", ""),
                    "slug": article.get("slug", ""),
                    "content": article.get("content", ""),
                    "meta_description": article.get("meta_description", ""),
                    "keyword": article.get("keyword", ""),
                    "niche": article.get("niche", ""),
                    "word_count": article.get("word_count", 0),
                    "affiliate_links_count": article.get("affiliate_links_count", 0),
                },
                timeout=15
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                seo_score = self._calc_seo_score(article)
                logger.info(f"Published to blog: {data.get('url', '')}")
                return {
                    "success": True,
                    "wp_post_id": 0,
                    "wp_url": data.get("url", ""),
                    "seo_score": seo_score
                }
            else:
                logger.warning(f"Blog API error {resp.status_code}: {resp.text[:100]}")
                return self._save_locally(article)

        except requests.exceptions.ConnectionError:
            logger.info("Blog server not reachable, saving locally.")
            return self._save_locally(article)

        except Exception as e:
            logger.error(f"Publish error: {e}")
            return self._save_locally(article)

    def test_connection(self) -> bool:
        try:
            resp = requests.get(f"{self.blog_url}/api/stats", timeout=60)
            return resp.status_code == 200
        except Exception:
            return False

    def _calc_seo_score(self, article: dict) -> int:
        score = 0
        content = article.get("content", "")
        if article.get("keyword", "").lower() in article.get("title", "").lower(): score += 20
        if article.get("meta_description"): score += 15
        if article.get("word_count", 0) >= 2000: score += 20
        elif article.get("word_count", 0) >= 1500: score += 10
        if "<h2" in content: score += 15
        if "affiliate-link" in content: score += 10
        if "faq" in content.lower(): score += 10
        if "<table" in content: score += 10
        return min(score, 100)

    def _save_locally(self, article: dict) -> dict:
        import os, re
        os.makedirs("data/articles", exist_ok=True)
        slug = article.get("slug", "article")
        filename = f"data/articles/{slug}.html"
        html = f"""<!DOCTYPE html>
<html><head><title>{article.get('title','')}</title>
<meta name="description" content="{article.get('meta_description','')}">
</head><body>{article.get('content','')}</body></html>"""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html)
        seo = self._calc_seo_score(article)
        return {"success": True, "wp_post_id": 0, "wp_url": filename, "seo_score": seo, "local": True}
