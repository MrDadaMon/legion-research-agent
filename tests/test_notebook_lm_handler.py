import pytest
from src.agent.handlers.notebook_lm_handler import (
    NotebookLMHandler,
    format_deliverable_options,
    format_deliverable_response,
    DELIVERABLE_DESCRIPTIONS,
)


class TestNotebookLMHandlerNotConfigured:
    """Tests for NotebookLMHandler when API key is not set."""

    def test_is_configured_returns_false_when_no_key(self):
        handler = NotebookLMHandler()
        assert handler.is_configured() is False

    def test_check_status_returns_not_configured(self):
        handler = NotebookLMHandler()
        status = handler.check_status()
        assert status["configured"] is False
        assert status["api_key_present"] is False

    def test_upload_source_returns_not_configured_message(self):
        handler = NotebookLMHandler()
        result = handler.upload_source("https://youtube.com/watch?v=abc")
        assert result["status"] == "not_configured"
        assert "NOTEBOOK_LM_API_KEY" in result["message"]

    def test_query_returns_not_configured_message(self):
        handler = NotebookLMHandler()
        result = handler.query("What is the main topic?")
        assert result["status"] == "not_configured"

    def test_generate_deliverable_returns_not_configured(self):
        handler = NotebookLMHandler()
        result = handler.generate_deliverable("podcast")
        assert result["status"] == "not_configured"
        assert result["deliverable_type"] == "podcast"


class TestFormatDeliverableOptions:
    def test_lists_all_deliverable_types(self):
        output = format_deliverable_options()
        for dtype in DELIVERABLE_DESCRIPTIONS:
            formatted = dtype.replace("_", " ").title()
            assert formatted in output

    def test_mentions_how_to_request(self):
        output = format_deliverable_options()
        assert "generate a podcast" in output


class TestFormatDeliverableResponse:
    def test_not_configured_response(self):
        result = {"status": "not_configured", "deliverable_type": "infographic", "message": "Not set up"}
        output = format_deliverable_response(result)
        assert "infographic" in output.lower()
        assert "configure" in output.lower()

    def test_error_response(self):
        result = {"status": "error", "message": "Something went wrong"}
        output = format_deliverable_response(result)
        assert "Error" in output

    def test_success_response(self):
        result = {
            "status": "success",
            "deliverable_type": "slides",
            "deliverable_url": "https://example.com/slides.pdf",
            "message": "Generated successfully",
        }
        output = format_deliverable_response(result)
        assert "slides" in output.lower()
        assert "https://example.com/slides.pdf" in output
