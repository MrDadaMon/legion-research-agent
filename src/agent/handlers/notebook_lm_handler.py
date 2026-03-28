"""notebook-lm handler using notebooklm-py.

notebooklm-py (GitHub: teng-lin/notebooklm-py) — proper Python async API
for Google NotebookLM with CLI login (no API key needed).

Auth setup on Legion:
1. pip install "notebooklm-py[browser]"
2. playwright install chromium
3. notebooklm login  (opens browser, authenticate once)

After login, authentication is stored locally — no API key needed.
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Deliverable types supported by NotebookLM
DeliverableType = Literal[
    "audio_overview",
    "video",
    "slide_deck",
    "infographic",
    "flashcards",
    "quiz",
    "report",
    "mind_map",
    "data_table",
]

DELIVERABLE_DESCRIPTIONS: dict[DeliverableType, str] = {
    "audio_overview": "AI-generated audio discussion of your sources (the classic NotebookLM podcast)",
    "video": "AI-generated video summary with visuals",
    "slide_deck": "Presentation deck ready to share",
    "infographic": "Visual summary with key points and connections",
    "flashcards": "Study cards for active recall",
    "quiz": "Test your knowledge with AI-generated questions",
    "report": "Structured study guide or report",
    "mind_map": "Visual map of how concepts connect",
    "data_table": "Structured data extracted from sources",
}

ARTIFACT_TYPE_MAP: dict[DeliverableType, str] = {
    "audio_overview": "audio",
    "video": "video",
    "slide_deck": "slides",
    "infographic": "infographic",
    "flashcards": "flashcards",
    "quiz": "quiz",
    "report": "report",
    "mind_map": "mind_map",
    "data_table": "data_table",
}


class NotebookLMHandler:
    """Handler for notebooklm-py integration.

    Supports:
    - Source upload (YouTube URLs, articles, PDFs)
    - RAG chat queries against uploaded sources with citations
    - Deliverable generation (audio, video, slides, infographic, flashcards, quiz, etc.)
    - Notebook management (create, list)

    Auth: Run `notebooklm login` once on Legion to authenticate via browser.
    After that, from_storage() reads stored credentials automatically.
    """

    def __init__(self):
        self._client = None
        self._checked = False

    async def _get_client(self):
        """Lazy-initialize the NotebookLM client."""
        if self._client is not None:
            return self._client

        try:
            from notebooklm import NotebookLMClient
            self._client = await NotebookLMClient.from_storage()
            logger.info("notebooklm-py client initialized")
            return self._client
        except ImportError:
            raise RuntimeError(
                "notebooklm-py not installed. Run: pip install 'notebooklm-py[browser]'"
            )

    def is_configured(self) -> bool:
        """Check if notebooklm-py is installed and authenticated."""
        try:
            from notebooklm import NotebookLMClient
            return True
        except ImportError:
            return False

    async def check_status(self) -> dict:
        """Check notebooklm-py configuration and authentication status."""
        try:
            import notebooklm
            notebooklm.NotebookLMClient  # verify class exists
        except ImportError:
            return {
                "configured": False,
                "message": (
                    "notebooklm-py not installed. "
                    "On Legion, run:\n"
                    "  pip install 'notebooklm-py[browser]'\n"
                    "  playwright install chromium\n"
                    "  notebooklm login\n"
                    "Then authenticate via browser."
                ),
            }

        try:
            client = await NotebookLMClient.from_storage()
            await client.close()
            return {
                "configured": True,
                "message": "notebooklm-py is ready. You are authenticated.",
            }
        except Exception as e:
            return {
                "configured": False,
                "authenticated": False,
                "message": f"Authentication check failed: {e}\nRun 'notebooklm login' on Legion to authenticate.",
            }

    async def get_or_create_notebook(self, name: str = "Legion Research") -> str:
        """Get the most recent notebook or create a new one.

        Args:
            name: Name for new notebook if creating

        Returns:
            Notebook ID string
        """
        client = await self._get_client()

        # Try to find existing notebook
        try:
            notebooks = await client.notebooks.list()
            if notebooks:
                # Return most recent
                return notebooks[0].id
        except Exception:
            pass

        # Create new notebook
        notebook = await client.notebooks.create(name)
        return notebook.id

    async def upload_source(self, url: str, notebook_id: str | None = None) -> dict:
        """Upload a source (YouTube URL, article, PDF) to Notebook LM.

        Args:
            url: URL to upload (YouTube, article, or PDF)
            notebook_id: Optional notebook ID. If None, uses most recent or creates new.

        Returns:
            dict with status, source_id, and message
        """
        if notebook_id is None:
            notebook_id = await self.get_or_create_notebook()

        try:
            client = await self._get_client()
            source = await client.sources.add_url(notebook_id, url, wait=True)
            return {
                "status": "success",
                "source_id": source.id,
                "notebook_id": notebook_id,
                "message": f"Source uploaded successfully: {url}",
            }
        except Exception as e:
            logger.error(f"notebooklm-py upload failed: {e}")
            return {
                "status": "error",
                "message": f"Upload failed: {str(e)}",
            }

    async def query(
        self,
        question: str,
        notebook_id: str | None = None,
        source_ids: list[str] | None = None,
    ) -> dict:
        """Query Notebook LM's AI RAG analysis of uploaded sources.

        Args:
            question: Question to ask about the sources
            notebook_id: Optional notebook ID. Uses most recent if None.
            source_ids: Optional list of source IDs to query. If None, queries all.

        Returns:
            dict with status, answer, citations, and conversation_id
        """
        if notebook_id is None:
            notebook_id = await self.get_or_create_notebook()

        try:
            client = await self._get_client()
            result = await client.chat.ask(
                notebook_id,
                question,
                source_ids=source_ids,
            )
            return {
                "status": "success",
                "answer": result.answer,
                "conversation_id": result.conversation_id,
                "references": [
                    {
                        "citation_number": ref.citation_number,
                        "source_id": ref.source_id,
                        "cited_text": ref.cited_text,
                    }
                    for ref in result.references
                ],
            }
        except Exception as e:
            logger.error(f"notebooklm-py query failed: {e}")
            return {
                "status": "error",
                "message": f"Query failed: {str(e)}",
            }

    async def generate_deliverable(
        self,
        deliverable_type: DeliverableType,
        instructions: str | None = None,
        notebook_id: str | None = None,
    ) -> dict:
        """Generate a deliverable from notebook sources.

        Args:
            deliverable_type: Type of deliverable to generate
            instructions: Optional custom instructions for generation
            notebook_id: Optional notebook ID. Uses most recent if None.

        Returns:
            dict with status, task_id, and artifact info
        """
        if notebook_id is None:
            notebook_id = await self.get_or_create_notebook()

        try:
            client = await self._get_client()
            artifact_kind = ARTIFACT_TYPE_MAP[deliverable_type]

            # Call appropriate generate method
            if deliverable_type == "audio_overview":
                status = await client.artifacts.generate_audio(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "video":
                status = await client.artifacts.generate_video(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "slide_deck":
                status = await client.artifacts.generate_slide_deck(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "infographic":
                status = await client.artifacts.generate_infographic(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "flashcards":
                status = await client.artifacts.generate_flashcards(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "quiz":
                status = await client.artifacts.generate_quiz(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "report":
                status = await client.artifacts.generate_report(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "mind_map":
                status = await client.artifacts.generate_mind_map(
                    notebook_id, instructions=instructions
                )
            elif deliverable_type == "data_table":
                status = await client.artifacts.generate_data_table(
                    notebook_id, instructions=instructions
                )
            else:
                return {"status": "error", "message": f"Unknown deliverable type: {deliverable_type}"}

            return {
                "status": "success",
                "task_id": status.task_id,
                "artifact_kind": artifact_kind,
                "notebook_id": notebook_id,
                "message": f"{deliverable_type} generation started. Use task_id to download when ready.",
            }

        except Exception as e:
            logger.error(f"notebooklm-py generate failed: {e}")
            return {
                "status": "error",
                "message": f"Generation failed: {str(e)}",
            }

    async def download_deliverable(
        self,
        deliverable_type: DeliverableType,
        task_id: str,
        output_path: str,
        notebook_id: str | None = None,
    ) -> dict:
        """Download a generated artifact.

        Args:
            deliverable_type: Type of deliverable
            task_id: Task ID returned from generate_deliverable
            output_path: Local path to save the file
            notebook_id: Optional notebook ID

        Returns:
            dict with status and file_path
        """
        if notebook_id is None:
            notebook_id = await self.get_or_create_notebook()

        try:
            client = await self._get_client()

            if deliverable_type == "audio_overview":
                path = await client.artifacts.download_audio(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "video":
                path = await client.artifacts.download_video(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "slide_deck":
                path = await client.artifacts.download_slide_deck(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "infographic":
                path = await client.artifacts.download_infographic(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "flashcards":
                path = await client.artifacts.download_flashcards(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "quiz":
                path = await client.artifacts.download_quiz(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "report":
                path = await client.artifacts.download_report(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "mind_map":
                path = await client.artifacts.download_mind_map(notebook_id, output_path, task_id=task_id)
            elif deliverable_type == "data_table":
                path = await client.artifacts.download_data_table(notebook_id, output_path, task_id=task_id)
            else:
                return {"status": "error", "message": f"Unknown deliverable type: {deliverable_type}"}

            return {"status": "success", "file_path": path}

        except Exception as e:
            logger.error(f"notebooklm-py download failed: {e}")
            return {"status": "error", "message": f"Download failed: {str(e)}"}

    async def wait_for_generation(
        self,
        notebook_id: str,
        task_id: str,
        timeout: float = 300.0,
    ) -> dict:
        """Wait for artifact generation to complete.

        Args:
            notebook_id: Notebook ID
            task_id: Task ID from generate_deliverable
            timeout: Max seconds to wait (default 5 min)

        Returns:
            dict with status, is_complete, and artifact info
        """
        try:
            client = await self._get_client()
            status = await client.artifacts.wait_for_completion(notebook_id, task_id, timeout=timeout)
            return {
                "status": "success",
                "is_complete": status.state.is_complete(),
                "artifact_id": status.artifact_id,
                "message": "Generation complete" if status.state.is_complete() else "Still processing",
            }
        except Exception as e:
            logger.error(f"notebooklm-py wait failed: {e}")
            return {"status": "error", "message": f"Wait failed: {str(e)}"}

    async def close(self):
        """Close the NotebookLM client."""
        if self._client:
            await self._client.close()
            self._client = None


def format_deliverable_options() -> str:
    """Format deliverable options for user selection."""
    lines = ["**Generate a deliverable from these results:**", ""]
    for dtype, desc in DELIVERABLE_DESCRIPTIONS.items():
        lines.append(f"- **{dtype.replace('_', ' ').title()}** — {desc}")
    lines.append("")
    lines.append("Say the deliverable type to generate, e.g., 'generate a podcast' or 'make flashcards'")
    return "\n".join(lines)


def format_query_result(result: dict) -> str:
    """Format a NotebookLM query result for display."""
    if result["status"] != "success":
        return f"[NotebookLM Query Error]\n\n{result.get('message', 'Unknown error')}"

    lines = ["[NotebookLM Answer]", ""]
    lines.append(result["answer"])
    lines.append("")

    refs = result.get("references", [])
    if refs:
        lines.append(f"*{len(refs)} source(s) cited:*")
        for ref in refs:
            lines.append(f"  [{ref['citation_number']}] {ref['cited_text'][:100]}...")

    return "\n".join(lines)


def format_deliverable_response(result: dict) -> str:
    """Format a deliverable generation result for display."""
    if result["status"] == "error":
        return f"[Deliverable Error]\n\n{result.get('message', 'Unknown error')}"

    dtype = result.get("artifact_kind", result.get("deliverable_type", "deliverable"))
    task_id = result.get("task_id", "")
    msg = result.get("message", "")

    lines = [f"[{dtype.title()} Generation Started]", ""]
    lines.append(msg)
    if task_id:
        lines.append(f"Task ID: {task_id}")
    lines.append("")
    lines.append("I'll monitor this and download when ready. You can continue working while it generates.")

    return "\n".join(lines)
