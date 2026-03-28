import pytest
from src.agent.handlers.notebook_lm_handler import (
    NotebookLMHandler,
    format_deliverable_options,
    format_query_result,
    format_deliverable_response,
    DELIVERABLE_DESCRIPTIONS,
    ARTIFACT_TYPE_MAP,
)


class TestNotebookLMHandlerStructure:
    """Tests for handler structure — package not installed in test env."""

    def test_handler_has_required_methods(self):
        handler = NotebookLMHandler()
        assert hasattr(handler, "is_configured")
        assert hasattr(handler, "check_status")
        assert hasattr(handler, "get_or_create_notebook")
        assert hasattr(handler, "upload_source")
        assert hasattr(handler, "query")
        assert hasattr(handler, "generate_deliverable")
        assert hasattr(handler, "download_deliverable")
        assert hasattr(handler, "wait_for_generation")
        assert hasattr(handler, "close")

    def test_is_configured_false_when_package_not_installed(self, monkeypatch):
        """When notebooklm-py is not installed, is_configured returns False."""
        import sys
        # Simulate package not installed
        monkeypatch.delitem(sys.modules, "notebooklm", raising=False)
        handler = NotebookLMHandler()
        assert handler.is_configured() is False

    @pytest.mark.asyncio
    async def test_check_status_reports_not_installed(self, monkeypatch):
        """check_status returns helpful setup instructions when package missing."""
        import sys
        monkeypatch.delitem(sys.modules, "notebooklm", raising=False)
        handler = NotebookLMHandler()
        status = await handler.check_status()
        assert status["configured"] is False
        assert "pip install" in status["message"]


class TestFormatDeliverableOptions:
    def test_lists_all_deliverable_types(self):
        output = format_deliverable_options()
        for dtype in DELIVERABLE_DESCRIPTIONS:
            formatted = dtype.replace("_", " ").title()
            assert formatted in output

    def test_mentions_how_to_request(self):
        output = format_deliverable_options()
        assert "generate" in output.lower()


class TestFormatQueryResult:
    def test_error_formatting(self):
        result = {"status": "error", "message": "Something went wrong"}
        output = format_query_result(result)
        assert "Error" in output
        assert "Something went wrong" in output

    def test_success_formatting(self):
        result = {
            "status": "success",
            "answer": "The main theme is AI safety.",
            "references": [
                {"citation_number": 1, "source_id": "src1", "cited_text": "AI safety is important"},
            ],
        }
        output = format_query_result(result)
        assert "AI safety is important" in output
        assert "1 source" in output


class TestFormatDeliverableResponse:
    def test_error_response(self):
        result = {"status": "error", "message": "Generation failed"}
        output = format_deliverable_response(result)
        assert "Error" in output

    def test_success_response(self):
        result = {
            "status": "success",
            "artifact_kind": "audio",
            "task_id": "task-123",
            "message": "Audio generation started",
        }
        output = format_deliverable_response(result)
        assert "Audio" in output
        assert "task-123" in output
        assert "download" in output.lower()


class TestDeliverableConstants:
    def test_all_deliverable_types_defined(self):
        expected = {
            "audio_overview", "video", "slide_deck", "infographic",
            "flashcards", "quiz", "report", "mind_map", "data_table",
        }
        assert set(DELIVERABLE_DESCRIPTIONS.keys()) == expected

    def test_artifact_type_map_complete(self):
        assert set(ARTIFACT_TYPE_MAP.keys()) == set(DELIVERABLE_DESCRIPTIONS.keys())
