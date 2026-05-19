"""
Competitor Analysis Agent
- Fetches top-ranking articles for a keyword
- Extracts content structure, headings, word count
- Identifies gaps and opportunities to outrank
- Builds a "beat this" brief for content generation
"""
import json
import logging
import requests
import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from config import config
from utils.claude_client import claude
from utils.json_parser import parse_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert SEO content strategist and competitor analysis specialist.
You analyze competitor articles to identify weaknesses, content gaps, and opportunities to create
superior content that outranks them.

Your analysis focuses on:
- Content depth and comprehensiveness
- Missing information or angles
- User intent alignment
- Affiliate opportunity gaps
- Structural improvements

Always respond in valid JSON format."""


class CompetitorAgent:
    """
    Analyzes top-ranking competitors and generates a content brief
    that is designed to outperform them.
    """

    def analyze(self, keyword: str, niche: str) -> Dict:
        """
        Full competitor analysis pipeline.
        Returns a content brief with gap analysis.
        """
        logger.info(f"Analyzing competitors for: {keyword}")

        # Fetch top SERP results
        serp_results = self._fetch_serp(keyword)

        # Scrape content from top 3-5 results
        competitor_data = []
        for result in serp_results[:4]:
            content = self._scrape_article(result["url"])
            if content:
                competitor_data.append({
                    "url": result["url"],
                    "title": result.get("title", ""),
                    "content_preview": content[:3000],
                    "word_count": len(content.split()),
                    "headings": self._extract_headings(content),
                })

        if not competitor_data:
            # No competitor data available, generate brief from keyword alone
            return self._generate_brief_from_keyword(keyword, niche)

        # AI analysis of gaps and opportunities
        content_brief = self._analyze_gaps(keyword, niche, competitor_data)
        return content_brief

    def _fetch_serp(self, keyword: str) -> List[Dict]:
        """Fetch top search results. Uses SerpAPI or falls back to DuckDuckGo."""
        if config.serp_api_key:
            return self._fetch_serpapi(keyword)
        else:
            return self._fetch_duckduckgo(keyword)

    def _fetch_serpapi(self, keyword: str) -> List[Dict]:
        """Fetch SERP using SerpAPI (paid, more reliable)."""
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={
                    "q": keyword,
                    "api_key": config.serp_api_key,
                    "num": 10,
                    "gl": "us",
                    "hl": "en"
                },
                timeout=15
            )
            data = resp.json()
            results = []
            for item in data.get("organic_results", [])[:6]:
                results.append({
                    "url": item.get("link", ""),
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", "")
                })
            return results
        except Exception as e:
            logger.warning(f"SerpAPI failed: {e}")
            return self._fetch_duckduckgo(keyword)

    def _fetch_duckduckgo(self, keyword: str) -> List[Dict]:
        """Free fallback: DuckDuckGo instant answer API."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(
                f"https://duckduckgo.com/html/?q={requests.utils.quote(keyword)}",
                headers=headers,
                timeout=15
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            results = []
            for result in soup.select(".result__body")[:6]:
                link_tag = result.select_one(".result__url")
                title_tag = result.select_one(".result__title")
                if link_tag and title_tag:
                    url = link_tag.get_text(strip=True)
                    if not url.startswith("http"):
                        url = "https://" + url
                    results.append({
                        "url": url,
                        "title": title_tag.get_text(strip=True),
                        "snippet": ""
                    })
            return results
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")
            return []

    def _scrape_article(self, url: str) -> str:
        """Scrape article content from URL."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove nav, footer, sidebar, ads
            for tag in soup.select("nav, footer, aside, .sidebar, .ad, script, style, header"):
                tag.decompose()

            # Extract main content
            main = soup.select_one("article, main, .content, .post-content, #content")
            if main:
                return main.get_text(separator=" ", strip=True)

            # Fallback: get body text
            return soup.body.get_text(separator=" ", strip=True) if soup.body else ""

        except Exception as e:
            logger.debug(f"Failed to scrape {url}: {e}")
            return ""

    def _extract_headings(self, content: str) -> List[str]:
        """Extract H2/H3 headings from HTML or text content."""
        headings = re.findall(r'#{1,3}\s+(.+)', content)
        return headings[:15]

    def _analyze_gaps(self, keyword: str, niche: str, competitors: List[Dict]) -> Dict:
        """Use Claude to analyze gaps and generate superior content brief."""
        competitor_summary = json.dumps([{
            "title": c["title"],
            "word_count": c["word_count"],
            "headings": c["headings"][:8],
            "content_preview": c["content_preview"][:1500]
        } for c in competitors], indent=2)

        prompt = f"""Analyze these top-ranking competitor articles for keyword: "{keyword}" (niche: {niche})

COMPETITOR DATA:
{competitor_summary}

Your task: Create a SUPERIOR content brief that will outrank all these competitors.

Identify:
1. What topics they ALL cover (must include)
2. Important topics they MISS (content gaps = our opportunity)
3. User questions not answered (check implied in their headings)
4. Better title options (more click-worthy + SEO)
5. Ideal content structure to beat them
6. Affiliate product placement opportunities

Return a comprehensive content brief as JSON:
{{
  "recommended_title": "...",
  "alt_titles": ["...", "..."],
  "target_word_count": 2500,
  "content_type": "best_list|review|comparison|how_to|buying_guide",
  "competitor_avg_word_count": 1800,
  "our_advantage": "...",
  "required_sections": [
    {{"heading": "...", "purpose": "...", "key_points": ["...", "..."]}}
  ],
  "content_gaps": ["...", "..."],
  "affiliate_placement_suggestions": [
    {{"location": "...", "product_type": "...", "why": "..."}}
  ],
  "faq_questions": ["...", "..."],
  "internal_link_opportunities": ["...", "..."],
  "meta_description": "...",
  "estimated_difficulty_to_outrank": "low|medium|high"
}}"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=3000)

        result = parse_json(response, fallback=None)
        if isinstance(result, dict) and result:
            return result

        return self._generate_brief_from_keyword(keyword, niche)

    def _generate_brief_from_keyword(self, keyword: str, niche: str) -> Dict:
        """Generate content brief from keyword alone (no competitor data)."""
        prompt = f"""Create a detailed SEO content brief for keyword: "{keyword}" in niche: {niche}

Return JSON ONLY:
{{"recommended_title":"...","alt_titles":["..."],"target_word_count":2500,"content_type":"best_list","required_sections":[{{"heading":"...","purpose":"...","key_points":["...","..."]}}],"content_gaps":[],"affiliate_placement_suggestions":[{{"location":"...","product_type":"...","why":"..."}}],"faq_questions":["...","..."],"meta_description":"...","estimated_difficulty_to_outrank":"medium"}}"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=2000)
        result = parse_json(response, fallback=None)
        if isinstance(result, dict) and result:
            return result

        # Minimal fallback
        return {
            "recommended_title": f"Best {keyword.title()} in 2026: Top Picks Reviewed",
            "target_word_count": 2500,
            "content_type": "best_list",
            "required_sections": [],
            "affiliate_placement_suggestions": [],
            "faq_questions": [],
            "meta_description": f"Discover the best {keyword} options in 2026. Expert reviews, comparisons, and buying advice.",
            "estimated_difficulty_to_outrank": "medium"
        }
