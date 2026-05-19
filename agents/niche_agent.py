"""
Niche & Keyword Research Agent
- Finds profitable niches with high buyer intent
- Discovers low-competition, high-value keywords
- Scores keywords by conversion potential
"""
import json
import logging
import re
import time
import requests
from typing import List, Dict, Optional
from config import config
from utils.claude_client import claude
from utils.database import KeywordDB, init_db
from utils.json_parser import parse_json

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an elite SEO and affiliate marketing strategist with 10+ years experience.
You specialize in finding high-converting, low-competition keywords that generate affiliate revenue.

Your expertise:
- Identifying buyer-intent keywords (people ready to purchase)
- Evaluating keyword difficulty vs. revenue potential
- Understanding affiliate commission structures across niches
- Spotting content gaps competitors haven't covered

Always respond in valid JSON format as specified."""


class NicheAgent:
    """
    Researches profitable niches and generates keyword lists.
    Uses Haiku model (cheap) for bulk keyword generation.
    """

    def __init__(self):
        self.serp_api_key = config.serp_api_key

    def research_keywords(self, niche: str, count: int = 20) -> List[Dict]:
        """
        Generate AND score keywords in 1 API call (tối ưu cost + rate limit).
        Returns sorted list by revenue potential.
        """
        logger.info(f"Researching keywords for niche: {niche}")

        # 1 API call = generate + score cùng lúc
        keywords = self._generate_and_score(niche, count)

        if not keywords:
            logger.warning(f"No keywords from API, using defaults for '{niche}'")
            keywords = self._default_keywords(niche)

        # Filter by difficulty
        filtered = [k for k in keywords if k.get("difficulty", 100) <= config.seo.max_keyword_difficulty]
        if not filtered:
            filtered = keywords  # Nếu filter quá chặt, dùng tất cả

        filtered.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)

        # Save to database
        saved_count = 0
        for kw in filtered:
            result = KeywordDB.add(
                keyword=kw["keyword"],
                niche=niche,
                search_volume=kw.get("estimated_monthly_searches", 1000),
                difficulty=kw.get("difficulty", 35),
                buyer_intent_score=kw.get("buyer_intent_score", 6),
                content_type=kw.get("best_content_type", "best_list")
            )
            if result:
                saved_count += 1

        logger.info(f"Saved {saved_count} keywords for niche '{niche}'")
        return filtered

    def _generate_and_score(self, niche: str, count: int) -> List[Dict]:
        """Generate + score keywords trong 1 API call duy nhất."""
        prompt = f"""Generate {count} profitable affiliate keywords for niche: "{niche}"

Return ONLY a JSON array (no explanation, no markdown):
[
  {{
    "keyword": "best vpn for streaming",
    "buyer_intent_score": 9,
    "difficulty": 28,
    "estimated_monthly_searches": 3200,
    "best_content_type": "best_list",
    "opportunity_score": 88
  }}
]

Rules:
- Focus on buyer-intent: best, review, vs, cheap, top, worth it, discount
- difficulty 10-50 (low = easier to rank)
- opportunity_score = buyer_intent * (100-difficulty) / 10
- Return ONLY valid JSON array, nothing else"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=3000)

        if not response:
            return []

        parsed = parse_json(response, fallback=None)
        if isinstance(parsed, list) and parsed:
            return parsed

        logger.warning(f"Could not parse keywords for '{niche}', using fallback")
        return []

    def _default_keywords(self, niche: str) -> List[Dict]:
        """Hardcoded fallback keywords khi API không khả dụng."""
        templates = [
            ("best {niche} 2026", 9, 30, 4500, "best_list", 85),
            ("{niche} review", 8, 25, 3200, "review", 80),
            ("top {niche} for beginners", 7, 20, 2100, "best_list", 78),
            ("cheapest {niche} options", 8, 28, 1800, "best_list", 76),
            ("is {niche} worth it", 7, 22, 1500, "review", 74),
            ("{niche} comparison 2026", 8, 35, 2800, "comparison", 72),
            ("best {niche} for professionals", 7, 32, 1600, "best_list", 70),
            ("{niche} buying guide", 6, 18, 1200, "buying_guide", 68),
        ]
        return [
            {
                "keyword": kw.replace("{niche}", niche),
                "buyer_intent_score": intent,
                "difficulty": diff,
                "estimated_monthly_searches": vol,
                "best_content_type": ctype,
                "opportunity_score": score
            }
            for kw, intent, diff, vol, ctype, score in templates
        ]

    def _generate_keyword_ideas(self, niche: str, count: int) -> List[str]:
        """Generate keyword ideas using AI."""
        prompt = f"""Generate {count} high-potential affiliate marketing keywords for the niche: "{niche}"

Focus on buyer-intent keywords:
- "best [product] for [use case]"
- "[product] review"
- "[product A] vs [product B]"
- "cheapest [product]"
- "is [product] worth it"
- "top [number] [products]"

Return ONLY a JSON array of strings, no explanation:
["keyword 1", "keyword 2", ...]"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=1024)
        time.sleep(4)  # Tránh rate limit giữa các call liên tiếp

        parsed = parse_json(response, fallback=None)
        if isinstance(parsed, list):
            return [str(k) for k in parsed if k]

        # Fallback: extract từ text
        lines = [l.strip().strip('"').strip("'").strip(",") for l in response.split("\n")]
        return [l for l in lines if l and len(l) > 5][:count]

    def _score_keywords(self, keywords: List[str], niche: str) -> List[Dict]:
        """Score keywords for buyer intent and opportunity."""
        if not keywords:
            return []

        kw_list = "\n".join(f"- {kw}" for kw in keywords[:20])

        prompt = f"""Analyze these keywords for the "{niche}" affiliate niche.

Keywords:
{kw_list}

For each keyword return:
- buyer_intent_score: 0-10
- difficulty: 0-100 (lower = easier)
- estimated_monthly_searches: number
- best_content_type: best_list|review|comparison|how_to|buying_guide
- opportunity_score: 0-100

Return JSON array ONLY:
[{{"keyword":"...","buyer_intent_score":8,"difficulty":25,"estimated_monthly_searches":2400,"best_content_type":"best_list","opportunity_score":85}}]"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=3000)
        time.sleep(4)

        parsed = parse_json(response, fallback=None)
        if isinstance(parsed, list) and parsed:
            return parsed

        # Fallback: trả về keywords với score mặc định
        logger.warning("Scoring failed, using default scores")
        return [{"keyword": kw, "opportunity_score": 50, "buyer_intent_score": 6,
                 "difficulty": 35, "estimated_monthly_searches": 1200,
                 "best_content_type": "best_list"} for kw in keywords]

    def expand_niches(self) -> List[Dict]:
        """AI discovers new profitable niches to expand into."""
        current_niches = ", ".join(config.target_niches)

        prompt = f"""Current affiliate niches: {current_niches}

Suggest 5 NEW profitable niches to expand into in 2026. Consider:
- High affiliate commission rates (20%+ preferred)
- Growing market trends
- Low competition in SEO
- Evergreen content potential

Return JSON array:
[
  {{
    "niche": "...",
    "why_profitable": "...",
    "avg_commission": "...",
    "competition_level": "low|medium|high",
    "example_products": ["...", "..."],
    "priority_score": 85
  }}
]"""

        response = claude.complete_cheap(SYSTEM_PROMPT, prompt, max_tokens=2000)

        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            return []

    def research_all_niches(self) -> int:
        """Research keywords for all configured niches. Returns total keywords found."""
        total = 0
        for niche in config.target_niches:
            keywords = self.research_keywords(niche, count=20)
            total += len(keywords)
            logger.info(f"Niche '{niche}': {len(keywords)} keywords found")
        return total
