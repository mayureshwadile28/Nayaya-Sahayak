"""Application configuration loaded from environment variables."""

from pathlib import Path

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

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    data_dir: Path = Path(__file__).resolve().parent / "data"
    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"

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
