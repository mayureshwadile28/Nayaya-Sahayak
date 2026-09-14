"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings, loaded from .env file and environment variables."""

    # Gemini API
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # Upload limits
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    # Rate limiting
    rate_limit_rpm: int = 30

    @field_validator("gemini_api_key", "gemini_model", "backend_host", mode="before")
    @classmethod
    def clean_string(cls, v: object) -> str:
        """Strip surrounding quotes and whitespace from string config."""
        if v is None:
            return ""
        val = str(v).strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1].strip()
        return val

    @field_validator("backend_port", mode="before")
    @classmethod
    def clean_port(cls, v: object) -> int:
        """Safely parse backend port."""
        if v is None or v == "":
            return 8000
        try:
            val = str(v).strip().strip("\"'")
            return int(val)
        except (ValueError, TypeError):
            return 8000

    @field_validator("max_upload_size", mode="before")
    @classmethod
    def clean_upload_size(cls, v: object) -> int:
        """Safely parse max upload size."""
        if v is None or v == "":
            return 10 * 1024 * 1024
        try:
            val = str(v).strip().strip("\"'")
            return int(val)
        except (ValueError, TypeError):
            return 10 * 1024 * 1024

    @field_validator("rate_limit_rpm", mode="before")
    @classmethod
    def clean_rate_limit(cls, v: object) -> int:
        """Safely parse rate limit."""
        if v is None or v == "":
            return 30
        try:
            val = str(v).strip().strip("\"'")
            return int(val)
        except (ValueError, TypeError):
            return 30

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Path(__file__).resolve().parent / "data"

    @property
    def writable_dir(self) -> Path:
        import os
        if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
            return Path("/tmp")
        try:
            test_file = self.base_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
            return self.base_dir
        except (OSError, PermissionError):
            return Path("/tmp")

    @property
    def upload_dir(self) -> Path:
        return self.writable_dir / "uploads"

    @property
    def chroma_dir(self) -> Path:
        return self.writable_dir / "chroma_data"

    @property
    def db_path(self) -> Path:
        return self.writable_dir / "session_metadata.db"

    # Allowed file types
    allowed_extensions: list[str] = [".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"]
    allowed_mime_types: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "image/jpeg",
        "image/png",
    ]

    model_config = {
        "env_file": str(Path(__file__).resolve().parent.parent / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
