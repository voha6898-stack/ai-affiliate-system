"""
Central configuration for AI Content + Affiliate Automation System
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ClaudeConfig:
    api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    # Haiku for cheap tasks (research, classification)
    haiku_model: str = "claude-haiku-4-5-20251001"
    # Sonnet for quality content generation
    sonnet_model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    # Cache system prompts to cut API cost ~90%
    use_prompt_caching: bool = True


@dataclass
class WordPressConfig:
    site_url: str = field(default_factory=lambda: os.getenv("WP_SITE_URL", ""))
    username: str = field(default_factory=lambda: os.getenv("WP_USERNAME", ""))
    app_password: str = field(default_factory=lambda: os.getenv("WP_APP_PASSWORD", ""))
    auto_publish: bool = True  # False = save as draft for review
    default_category: str = "Reviews"
    default_status: str = "publish"  # publish | draft


@dataclass
class AffiliateConfig:
    # Amazon Associates
    amazon_tag: str = field(default_factory=lambda: os.getenv("AMAZON_AFFILIATE_TAG", ""))
    amazon_region: str = "com"  # com, co.uk, etc.

    # ClickBank
    clickbank_id: str = field(default_factory=lambda: os.getenv("CLICKBANK_ID", ""))

    # ShareASale
    shareasale_id: str = field(default_factory=lambda: os.getenv("SHAREASALE_ID", ""))

    # Minimum commission rate to include product (%)
    min_commission_rate: float = 5.0

    # High-value categories to prioritize
    priority_categories: List[str] = field(default_factory=lambda: [
        "software", "online courses", "hosting", "vpn",
        "fitness equipment", "supplements", "electronics"
    ])


@dataclass
class SEOConfig:
    # Target article length (words)
    min_word_count: int = 1800
    target_word_count: int = 2500

    # Keyword difficulty threshold (0-100, lower = easier to rank)
    max_keyword_difficulty: int = 40

    # Minimum monthly search volume
    min_search_volume: int = 500

    # Buyer intent keywords (highest conversion)
    buyer_intent_modifiers: List[str] = field(default_factory=lambda: [
        "best", "review", "reviews", "buy", "top", "vs",
        "comparison", "alternative", "cheap", "discount",
        "coupon", "deal", "recommended", "worth it"
    ])

    # Content types to generate
    content_types: List[str] = field(default_factory=lambda: [
        "best_list",      # "10 Best X for Y"
        "review",         # "X Review: Is It Worth It?"
        "comparison",     # "X vs Y: Which Is Better?"
        "how_to",         # "How to Use X to Achieve Y"
        "buying_guide"    # "Complete Buying Guide for X"
    ])


@dataclass
class SchedulerConfig:
    # Articles to publish per day
    articles_per_day: int = 3

    # Hours between publishing (spread throughout day)
    publish_hours: List[int] = field(default_factory=lambda: [8, 14, 20])

    # Days between updating old content
    content_refresh_days: int = 90

    # Monitor performance every N hours
    monitor_interval_hours: int = 24


@dataclass
class DatabaseConfig:
    path: str = "data/affiliate_ai.db"


@dataclass
class AppConfig:
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    wordpress: WordPressConfig = field(default_factory=WordPressConfig)
    affiliate: AffiliateConfig = field(default_factory=AffiliateConfig)
    seo: SEOConfig = field(default_factory=SEOConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    # Target niches — sorted by commission rate (highest first)
    target_niches: List[str] = field(default_factory=lambda: [
        "web hosting",            # Bluehost $65-100/sale, Hostinger $60+
        "vpn services",           # NordVPN 40%, ExpressVPN 36%
        "password managers",      # 1Password 25% recurring, Dashlane 20%
        "antivirus software",     # Norton 20-30%, Bitdefender 40%
        "email marketing tools",  # GetResponse 33% recurring, ConvertKit 30%
        "project management software",  # Monday.com $50+, Notion 20%
        "online courses",         # Udemy 10-30%, Teachable 30%
        "ai writing tools",       # Jasper 30%, Copy.ai 30% recurring
    ])

    # SERP API (use free tier of serpapi or valueserp)
    serp_api_key: str = field(default_factory=lambda: os.getenv("SERP_API_KEY", ""))

    # Logs
    log_level: str = "INFO"
    log_file: str = "data/affiliate_ai.log"


# Singleton config instance
config = AppConfig()
