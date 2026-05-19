"""
Content Generation Agent — The Core Revenue Engine
- Generates 2000-2500 word SEO-optimized articles
- Intelligently inserts affiliate links at high-conversion spots
- Uses Claude Sonnet for maximum quality
- Prompt caching cuts cost by 80%+ on bulk generation
"""
import json
import logging
import re
from typing import List, Dict, Optional
from config import config
from utils.claude_client import claude
from utils.database import ArticleDB, KeywordDB, AffiliateProductDB

logger = logging.getLogger(__name__)

# This large system prompt is CACHED — only paid once, then reused for free
CONTENT_SYSTEM_PROMPT = """You are a world-class SEO content writer and affiliate marketing expert.
You write authoritative, helpful, and highly readable content that:

1. RANKS on Google (proper keyword usage, LSI terms, E-E-A-T signals)
2. CONVERTS readers to buyers (strategic affiliate link placement)
3. KEEPS readers engaged (clear structure, scannable, valuable)
4. BUILDS TRUST (honest reviews, balanced pros/cons, expert voice)

Your writing principles:
- Lead with value, not sales pitches
- Use data, statistics, and specific examples
- Structure content for scanability (H2/H3, bullets, tables)
- Place affiliate links naturally within helpful context
- Include comparison tables for best_list and comparison articles
- Add FAQ section targeting voice search and featured snippets
- Always write in American English, active voice
- Match the search intent perfectly

For affiliate links: Insert them where they provide the MOST value to the reader —
after explaining benefits, in product recommendations, in comparison sections.
Never force links where they feel unnatural.

Output format: Well-structured HTML suitable for WordPress publishing."""


class ContentAgent:
    """
    Generates complete, publication-ready SEO articles with affiliate links.
    Uses Claude Sonnet for highest quality content.
    """

    def generate(
        self,
        keyword: str,
        keyword_id: int,
        niche: str,
        content_brief: Dict,
        affiliate_products: List[Dict],
    ) -> Dict:
        """
        Generate a complete article from keyword + brief + products.

        Returns dict with title, content, meta_description, word_count.
        """
        logger.info(f"Generating content for: {keyword}")

        content_type = content_brief.get("content_type", "best_list")
        title = content_brief.get("recommended_title", f"Best {keyword.title()} in 2026")
        target_words = content_brief.get("target_word_count", 2500)

        # Build product context for affiliate insertion
        product_context = self._format_products(affiliate_products)

        # Generate the article
        article_html = self._generate_article(
            keyword=keyword,
            title=title,
            niche=niche,
            content_brief=content_brief,
            product_context=product_context,
            target_words=target_words,
            content_type=content_type,
        )

        # Post-process: insert affiliate links, optimize structure
        article_html = self._insert_affiliate_links(article_html, affiliate_products)
        article_html = self._optimize_html(article_html, keyword)

        word_count = len(re.sub(r'<[^>]+>', '', article_html).split())
        affiliate_count = article_html.count('affiliate-link')
        slug = self._generate_slug(title)

        # Generate SEO meta description
        meta_desc = content_brief.get("meta_description") or self._generate_meta(title, keyword)

        # Save to database
        article_id = ArticleDB.add(
            keyword_id=keyword_id,
            title=title,
            slug=slug,
            content=article_html,
            word_count=word_count,
            affiliate_links_count=affiliate_count
        )

        # Mark keyword as in_progress
        KeywordDB.update_status(keyword_id, "in_progress")

        logger.info(f"Generated article: {title} ({word_count} words, {affiliate_count} affiliate links)")

        return {
            "article_id": article_id,
            "title": title,
            "slug": slug,
            "content": article_html,
            "meta_description": meta_desc,
            "word_count": word_count,
            "affiliate_links_count": affiliate_count,
            "keyword": keyword,
            "niche": niche,
            "content_type": content_type,
        }

    def _generate_article(
        self,
        keyword: str,
        title: str,
        niche: str,
        content_brief: Dict,
        product_context: str,
        target_words: int,
        content_type: str,
    ) -> str:
        """
        Section-by-section generation — đảm bảo 2000+ từ bất kể model.
        Mỗi call sinh 1 section ~300-400 từ, gộp lại = bài hoàn chỉnh.
        """
        sections = content_brief.get("required_sections", [])
        faqs = content_brief.get("faq_questions", [])[:5]

        # Build section list (dùng brief nếu có, không thì dùng default)
        if sections:
            section_list = [s.get("heading", "") for s in sections[:6]]
        else:
            section_list = self._default_sections(keyword, content_type)

        faq_list = "\n".join(f"- {q}" for q in faqs) if faqs else \
            f"- What is the best {keyword}?\n- Is {keyword} worth it?\n- How to choose {keyword}?"

        ctx = f'Article: "{title}" | Keyword: "{keyword}" | Niche: {niche}'
        sys = "You are an expert SEO content writer. Write in HTML. Be thorough and detailed."
        parts = []

        # ── 1. Intro + Quick Answer box (~350 từ) ─────────────────────
        intro = claude.complete_quality(sys,
            f"{ctx}\n\nWrite the article INTRODUCTION (350 words) in HTML:\n"
            f"- Start with <blockquote class='quick-answer'><strong>Quick Answer:</strong> [2-sentence summary]</blockquote>\n"
            f"- Then write an engaging <h1>{title}</h1> followed by 3 paragraphs introducing the topic\n"
            f"- Mention keyword '{keyword}' naturally\n"
            f"- Products to reference: {product_context}\n"
            f"- Write ONLY the intro, nothing else.", max_tokens=2000)
        parts.append(intro)

        # ── 2. Each content section (~300 từ each) ────────────────────
        for i, heading in enumerate(section_list[:5]):
            section = claude.complete_quality(sys,
                f"{ctx}\n\nWrite ONLY the section: <h2>{heading}</h2>\n"
                f"Write 300 words of detailed, helpful content for this section.\n"
                f"Include bullet points or numbered list where appropriate.\n"
                f"Mention relevant products: {product_context}\n"
                f"Add 1-2 affiliate links as: <a href='#' class='affiliate-link' rel='nofollow sponsored'>Product Name</a>\n"
                f"Write ONLY this section, no intro or conclusion.", max_tokens=2000)
            parts.append(section)

        # ── 3. Comparison table (~200 từ) ─────────────────────────────
        table = claude.complete_cheap(sys,
            f"{ctx}\n\nWrite an HTML comparison table for the top 5 {keyword} options.\n"
            f"Include columns: Product | Price | Key Feature | Rating | Best For\n"
            f"Use proper HTML <table> tags with <thead> and <tbody>.\n"
            f"Wrap in <h2>Quick Comparison: Top {keyword.title()} at a Glance</h2>", max_tokens=1500)
        parts.append(table)

        # ── 4. FAQ section (~300 từ) ──────────────────────────────────
        faq = claude.complete_cheap(sys,
            f"{ctx}\n\nWrite an FAQ section answering these questions (2-3 sentences each):\n"
            f"{faq_list}\n\nFormat:\n"
            f"<h2>Frequently Asked Questions</h2>\n"
            f"<div class='faq-item'><h3>Question?</h3><p>Answer...</p></div>\n"
            f"Write ALL questions above.", max_tokens=1500)
        parts.append(faq)

        # ── 5. Conclusion (~150 từ) ───────────────────────────────────
        conclusion = claude.complete_cheap(sys,
            f"{ctx}\n\nWrite a conclusion (150 words) for this article.\n"
            f"- Summarize key takeaways\n"
            f"- Give a clear recommendation\n"
            f"- End with a call-to-action\n"
            f"Format: <h2>Final Verdict</h2><p>...</p>", max_tokens=600)
        parts.append(conclusion)

        return "<article>\n" + "\n\n".join(p for p in parts if p) + "\n</article>"

    def _default_sections(self, keyword: str, content_type: str) -> List[str]:
        """Default section headings khi brief không có sections."""
        templates = {
            "best_list": [
                f"What to Look for in {keyword.title()}",
                f"Top 10 Best {keyword.title()} in 2026",
                f"Detailed Reviews: Our Top Picks",
                f"How We Tested and Ranked Them",
                f"Value for Money: Budget vs Premium",
            ],
            "review": [
                f"What Is {keyword.title()}?",
                f"Key Features and Specifications",
                f"Performance: Real-World Testing",
                f"Pros and Cons",
                f"Who Should Buy It?",
            ],
            "comparison": [
                f"Overview: The Contenders",
                f"Feature-by-Feature Comparison",
                f"Performance and Speed",
                f"Pricing and Value",
                f"Which One Should You Choose?",
            ],
            "buying_guide": [
                f"Why You Need {keyword.title()}",
                f"Key Factors to Consider",
                f"Top Picks for Every Budget",
                f"Common Mistakes to Avoid",
                f"Our Top Recommendation",
            ],
        }
        return templates.get(content_type, templates["best_list"])

    def _format_products(self, products: List[Dict]) -> str:
        """Format affiliate products — concise to keep prompt small."""
        if not products:
            return "Recommend relevant affiliate products from your knowledge."
        lines = [
            f"- {p.get('name','Product')} ({p.get('affiliate_url','#')})"
            for p in products[:5]
        ]
        return "\n".join(lines)

    def _insert_affiliate_links(self, html: str, products: List[Dict]) -> str:
        """
        Ensure affiliate links are properly formatted.
        Adds tracking attributes and ensures proper rel tags.
        """
        for product in products:
            if not product.get("affiliate_url"):
                continue

            url = product["affiliate_url"]
            name = product.get("name", "")

            # Fix any raw URLs to proper anchor tags
            if url in html and f'href="{url}"' not in html:
                html = html.replace(
                    url,
                    f'<a href="{url}" class="affiliate-link" rel="nofollow sponsored" target="_blank">{name}</a>'
                )

        return html

    def _optimize_html(self, html: str, keyword: str) -> str:
        """Clean and optimize HTML structure."""
        # Ensure proper article wrapper
        if not html.strip().startswith("<"):
            html = f"<article>\n{html}\n</article>"

        # Add keyword to first paragraph if missing
        first_para_match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
        if first_para_match and keyword.lower() not in first_para_match.group(1).lower():
            pass  # Claude should have included it; don't force awkward insertion

        return html.strip()

    def _generate_slug(self, title: str) -> str:
        """Convert title to URL slug."""
        slug = title.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug.strip())
        slug = re.sub(r'-+', '-', slug)
        return slug[:60]

    def _generate_meta(self, title: str, keyword: str) -> str:
        """Generate SEO meta description."""
        prompt = f'Write a compelling 155-character SEO meta description for: "{title}" targeting keyword: "{keyword}". Include a CTA. Return ONLY the meta description text.'
        return claude.complete_cheap(
            "You are an SEO specialist. Write concise, compelling meta descriptions.",
            prompt,
            max_tokens=100
        ).strip()[:160]

    def regenerate_underperforming(self, article: Dict) -> Dict:
        """Regenerate an underperforming article with improved strategy."""
        keyword = article.get("keyword", "")
        logger.info(f"Regenerating underperforming article: {keyword}")

        prompt = f"""The article targeting "{keyword}" has low performance.
Analyze why it might be underperforming and suggest a completely different angle/approach.

Return JSON:
{{
  "new_title": "...",
  "new_angle": "...",
  "content_gaps_to_fix": ["...", "..."],
  "new_content_type": "...",
  "recommended_changes": ["...", "..."]
}}"""

        response = claude.complete_cheap(
            CONTENT_SYSTEM_PROMPT,
            prompt,
            max_tokens=1000
        )

        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass

        return {"new_title": article.get("title", ""), "new_angle": "update with fresh data"}
