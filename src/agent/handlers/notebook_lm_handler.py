"""notebook-lm-pi handler for free AI RAG processing and deliverable generation.

This module provides integration with notebook-lm-pi (GitHub: notebook-lm-pi by Tang Ling).

When NOT_CONFIGURED (no API key/auth), stub methods return helpful messages
pointing to Legion setup. When configured, full capabilities are available.

API key/auth deferred to Legion setup — user configures once when deploying.
"""

import os
import logging
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

NOTEBOOK_LM_API_KEY = os.getenv("NOTEBOOK_LM_API_KEY")
NOT_CONFIGURED = NOTEBOOK_LM_API_KEY is None

DeliverableType = Literal[
    "podcast",
    "infographic",
    "slides",
    "mind_map",
    "flashcards",
    "audio_overview",
]

DELIVERABLE_DESCRIPTIONS: dict[DeliverableType, str] = {
    "podcast": "AI-generated audio discussion of your sources",
    "infographic": "Visual summary with key points and connections",
    "slides": "Presentation deck ready to share",
    "mind_map": "Visual map of how concepts connect",
    "flashcards": "Study cards for active recall",
    "audio_overview": "Concise audio summary of the material",
}


class NotebookLMHandler:
    """Handler for notebook-lm-pi integration.

    Supports:
    - Source upload (YouTube URLs, articles, PDFs)
    - RAG queries against uploaded sources
    - Deliverable generation (podcast, infographic, slides, etc.)

    When not configured (no API key), all methods return stub responses.
    """

    def __init__(self):
        self._client = None
        if not NOT_CONFIGURED:
            self._init_client()

    def _init_client(self):
        try:
            from notebooklm import NotebookLM
            self._client = NotebookLM(api_key=NOTEBOOK_LM_API_KEY)
            logger.info("notebook-lm-pi client initialized")
        except ImportError:
            logger.warning("notebook-lm-pi not installed")
            self._client = None

    def is_configured(self) -> bool:
        """Check if notebook-lm-pi is configured and authenticated."""
        return not NOT_CONFIGURED and self._client is not None

    def upload_source(self, url: str) -> dict:
        """Upload a source (YouTube URL, article, PDF) to Notebook LM.

        Args:
            url: URL to upload (YouTube, article, or PDF)

        Returns:
            dict with status, source_id, and message
        """
        if NOT_CONFIGURED:
            return {
                "status": "not_configured",
                "message": (
                    "notebook-lm-pi is not configured yet. "
                    "API key not found in environment. "
                    "Add NOTEBOOK_LM_API_KEY to your .env file to enable. "
                    "See .env.example for the format."
                ),
            }

        if self._client is None:
            return {"status": "error", "message": "notebook-lm-pi client failed to initialize"}

        try:
            result = self._client.add_source(url=url)
            return {
                "status": "success",
                "source_id": result.get("id"),
                "message": f"Source uploaded successfully: {url}",
            }
        except Exception as e:
            logger.error(f"notebook-lm-pi upload failed: {e}")
            return {"status": "error", "message": f"Upload failed: {str(e)}"}

    def query(self, question: str, source_ids: list[str] | None = None) -> dict:
        """Query Notebook LM's AI RAG analysis of uploaded sources.

        Args:
            question: Question to ask about the sources
            source_ids: Optional list of source IDs to query. If None, queries all.

        Returns:
            dict with status, answer, and sources used
        """
        if NOT_CONFIGURED:
            return {
                "status": "not_configured",
                "message": (
                    "notebook-lm-pi is not configured. "
                    "Add NOTEBOOK_LM_API_KEY to your .env file to enable RAG queries."
                ),
            }

        if self._client is None:
            return {"status": "error", "message": "notebook-lm-pi client not initialized"}

        try:
            result = self._client.query(
                query=question,
                sources=source_ids,
            )
            return {
                "status": "success",
                "answer": result.get("answer", ""),
                "sources_used": source_ids or [],
            }
        except Exception as e:
            logger.error(f"notebook-lm-pi query failed: {e}")
            return {"status": "error", "message": f"Query failed: {str(e)}"}

    def generate_deliverable(
        self,
        deliverable_type: DeliverableType,
        source_ids: list[str] | None = None,
    ) -> dict:
        """Generate a deliverable (podcast, infographic, slides, etc.) from sources.

        Args:
            deliverable_type: Type of deliverable to generate
            source_ids: Optional list of source IDs. If None, uses all.

        Returns:
            dict with status, deliverable_url (or file_path), and message
        """
        if NOT_CONFIGURED:
            return {
                "status": "not_configured",
                "deliverable_type": deliverable_type,
                "message": (
                    f"notebook-lm-pi not configured. Cannot generate {deliverable_type}. "
                    "Add NOTEBOOK_LM_API_KEY to your .env file to enable deliverables."
                ),
            }

        if self._client is None:
            return {"status": "error", "message": "notebook-lm-pi client not initialized"}

        try:
            result = self._client.generate(
                format=deliverable_type,
                sources=source_ids,
            )
            return {
                "status": "success",
                "deliverable_type": deliverable_type,
                "deliverable_url": result.get("url") or result.get("file_path"),
                "message": f"{deliverable_type} generated successfully",
            }
        except Exception as e:
            logger.error(f"notebook-lm-pi generate failed: {e}")
            return {"status": "error", "message": f"Generation failed: {str(e)}"}

    def check_status(self) -> dict:
        """Check notebook-lm-pi configuration and authentication status."""
        if NOT_CONFIGURED:
            return {
                "configured": False,
                "api_key_present": False,
                "message": "NOTEBOOK_LM_API_KEY not found in environment",
            }

        if self._client is None:
            return {
                "configured": False,
                "api_key_present": True,
                "client_init_failed": True,
                "message": "Client failed to initialize — check notebook-lm-pi installation",
            }

        return {
            "configured": True,
            "api_key_present": True,
            "message": "notebook-lm-pi is ready",
        }


def format_deliverable_options() -> str:
    """Format deliverable options for user selection."""
    lines = ["**Generate a deliverable from these results:**", ""]
    for dtype, desc in DELIVERABLE_DESCRIPTIONS.items():
        lines.append(f"- **{dtype.replace('_', ' ').title()}** — {desc}")
    lines.append("")
    lines.append("Say the deliverable type to generate, e.g., 'generate a podcast'")
    return "\n".join(lines)


def format_deliverable_response(result: dict) -> str:
    """Format a deliverable generation result for display."""
    if result["status"] == "not_configured":
        return (
            f"[Deliverable: {result.get('deliverable_type', 'unknown')}]\n\n"
            f"{result['message']}\n\n"
            "When you configure NOTEBOOK_LM_API_KEY, I'll generate this for you."
        )

    if result["status"] == "error":
        return f"[Deliverable Error]\n\n{result['message']}"

    dtype = result.get("deliverable_type", "deliverable")
    url = result.get("deliverable_url", "")
    msg = result.get("message", "Generated successfully")

    lines = [f"[{dtype.replace('_', ' ').title()} Ready]", ""]
    lines.append(msg)
    if url:
        lines.append(f"URL: {url}")
    return "\n".join(lines)
