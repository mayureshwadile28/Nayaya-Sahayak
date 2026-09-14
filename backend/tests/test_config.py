"""Unit tests for application configuration and settings."""

from pathlib import Path
from unittest.mock import patch

from app.config import Settings, settings


class TestSettingsValidation:
    """Test field validators and sanitization in Settings."""

    def test_clean_string_strips_quotes_and_whitespace(self) -> None:
        """Surrounding quotes and whitespace should be stripped."""
        assert Settings.clean_string('  "test-key"  ') == "test-key"
        assert Settings.clean_string(" 'single-quote' ") == "single-quote"
        assert Settings.clean_string("normal_string") == "normal_string"
        assert Settings.clean_string(None) == ""

    def test_clean_port_parsing(self) -> None:
        """Port should be safely parsed to int with fallback to 8000."""
        assert Settings.clean_port("9000") == 9000
        assert Settings.clean_port('"8080"') == 8080
        assert Settings.clean_port(None) == 8000
        assert Settings.clean_port("invalid-port") == 8000
        assert Settings.clean_port("") == 8000

    def test_clean_upload_size_parsing(self) -> None:
        """Upload size should safely parse with fallback to 10MB."""
        ten_mb = 10 * 1024 * 1024
        assert Settings.clean_upload_size("5242880") == 5242880
        assert Settings.clean_upload_size(None) == ten_mb
        assert Settings.clean_upload_size("bad-size") == ten_mb
        assert Settings.clean_upload_size("") == ten_mb

    def test_clean_rate_limit_parsing(self) -> None:
        """Rate limit should safely parse with fallback to 30."""
        assert Settings.clean_rate_limit("60") == 60
        assert Settings.clean_rate_limit(None) == 30
        assert Settings.clean_rate_limit("not-a-number") == 30

    def test_repr_masks_api_key(self) -> None:
        """Settings repr should never reveal the raw gemini_api_key."""
        s = Settings(gemini_api_key="super-secret-key-12345")
        repr_str = repr(s)
        assert "super-secret-key-12345" not in repr_str
        assert "gemini_api_key='***'" in repr_str

    def test_allowed_extensions_and_mimes(self) -> None:
        """Allowed extensions and MIME types should include common document formats."""
        assert ".pdf" in settings.allowed_extensions
        assert ".docx" in settings.allowed_extensions
        assert ".png" in settings.allowed_extensions
        assert "application/pdf" in settings.allowed_mime_types
        assert "image/png" in settings.allowed_mime_types

    def test_writable_dir_vercel_environment(self) -> None:
        """In Vercel or Lambda environments, writable_dir should point to /tmp."""
        s = Settings()
        with patch.dict("os.environ", {"VERCEL": "1"}):
            assert s.writable_dir == Path("/tmp")
            assert s.upload_dir == Path("/tmp/uploads")
            assert s.db_path == Path("/tmp/session_metadata.db")
