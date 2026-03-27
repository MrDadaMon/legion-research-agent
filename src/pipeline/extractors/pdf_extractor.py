import fitz
import requests


async def extract_pdf(source: str | bytes) -> tuple[str, str]:
    if isinstance(source, str) and source.startswith(("http://", "https://")):
        response = requests.get(source, timeout=30)
        response.raise_for_status()
        doc = fitz.open(stream=response.content, filetype="pdf")
    elif isinstance(source, bytes):
        doc = fitz.open(stream=source, filetype="pdf")
    else:
        doc = fitz.open(source)

    text_parts = [page.get_text() for page in doc]
    metadata = doc.metadata
    doc.close()

    text = "\n".join(text_parts)
    title = metadata.get("title") if metadata and metadata.get("title") else "Untitled PDF"

    if not text.strip():
        text = "[No text extracted from PDF]"

    return (title, text)
