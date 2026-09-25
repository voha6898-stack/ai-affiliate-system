"""SEO text helpers shared across agents."""


def clean_seo_title(keyword: str, year: int = 2026) -> str:
    """
    Build a fallback SEO title from a raw keyword without duplicating a
    leading buyer-intent word the keyword already contains (e.g. keyword
    "best online courses for photography" must not become
    "Best Best Online Courses For Photography").
    """
    kw_title = keyword.strip().title()
    if not kw_title:
        return f"Best Products in {year}: Top Picks Reviewed"

    lead_word = kw_title.split()[0].lower()
    if lead_word in ("best", "top"):
        return f"{kw_title} in {year}: Top Picks Reviewed"
    return f"Best {kw_title} in {year}: Top Picks Reviewed"
