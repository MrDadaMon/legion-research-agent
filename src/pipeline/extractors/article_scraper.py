import re
import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


async def scrape_article(url: str) -> tuple[str, str]:
    response = requests.get(
        url,
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    soup = BeautifulSoup(response.text, "html.parser")

    title_tag = soup.find("meta", property="og:title") or soup.find("title")
    if title_tag:
        title = title_tag.get("content", None) or (title_tag.text.strip() if title_tag else "Untitled")
    else:
        title = "Untitled"

    article = (
        soup.find("article")
        or soup.find("main")
        or soup.find(class_=re.compile(r"content|article|post", re.I))
    )

    if article:
        text = article.get_text(separator="\n", strip=True)
    else:
        text = response.text[:500]

    if len(text) < 200 or any(kw in text.lower() for kw in ["nav", "menu", "subscribe"]):
        logger.warning(f"Article content may be low quality for URL: {url}")

    return (title, text)
