import pytest
from io import BytesIO
import fitz


class TestPdfExtractor:
    @pytest.mark.asyncio
    async def test_extract_pdf_from_bytes(self):
        from src.pipeline.extractors.pdf_extractor import extract_pdf

        doc = fitz.open()
        doc.new_page(width=595, height=842)
        doc[0].insert_text((50, 50), "Test PDF content here", fontsize=12)
        buffer = BytesIO()
        doc.save(buffer)
        doc.close()
        buffer.seek(0)

        title, text = await extract_pdf(buffer.getvalue())
        assert "Test PDF content here" in text

    @pytest.mark.asyncio
    async def test_extract_pdf_empty_content(self):
        from src.pipeline.extractors.pdf_extractor import extract_pdf

        doc = fitz.open()
        doc.new_page(width=100, height=100)
        buffer = BytesIO()
        doc.save(buffer)
        doc.close()
        buffer.seek(0)

        title, text = await extract_pdf(buffer.getvalue())
        assert text == "[No text extracted from PDF]"
