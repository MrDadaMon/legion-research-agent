import pytest
from unittest.mock import patch, MagicMock

from src.pipeline.extractors.article_scraper import scrape_article


class TestArticleScraper:
    @pytest.mark.asyncio
    async def test_scrape_article_success(self):
        html = """
        <html>
        <head><title>Test Article</title></head>
        <body>
        <article>
            <p>This is the main article content.</p>
            <p>With multiple paragraphs.</p>
        </article>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html

        with patch(
            "src.pipeline.extractors.article_scraper.requests.get",
            return_value=mock_response,
        ):
            title, text = await scrape_article("https://example.com/article")
            assert title == "Test Article"
            assert "main article content" in text

    @pytest.mark.asyncio
    async def test_scrape_article_no_article_tag(self):
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
        <p>Some content without article tag.</p>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.text = html

        with patch(
            "src.pipeline.extractors.article_scraper.requests.get",
            return_value=mock_response,
        ):
            title, text = await scrape_article("https://example.com/page")
            assert title == "Test Page"
