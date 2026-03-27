import re


async def classify_and_store(text: str) -> tuple[str, str, str]:
    stripped = text.strip()
    processed = re.sub(r"\n{3,}", "\n\n", stripped)
    first_line = processed.split("\n")[0][:100] if processed else "Untitled Text"
    title = first_line if first_line else "Untitled Text"
    return ("text", title, processed)
