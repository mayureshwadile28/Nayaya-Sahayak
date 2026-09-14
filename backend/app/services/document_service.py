"""Document processing service: upload validation, text extraction, type detection."""

import logging
import tempfile
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)


class DocumentService:
    """Handles document upload validation and text extraction."""

    def validate_file(
        self,
        filename: str,
        file_size: int,
        content_type: str | None,
        content: bytes | None = None,
    ) -> None:
        """Validate uploaded file type, size, and binary magic bytes.

        Args:
            filename: Original filename.
            file_size: File size in bytes.
            content_type: MIME type of the file.
            content: Raw byte content for magic bytes signature validation.

        Raises:
            ValueError: If file type, size, or signature is invalid.
        """
        # Check file extension
        safe_filename = Path(filename).name
        ext = Path(safe_filename).suffix.lower()
        if ext not in settings.allowed_extensions:
            msg = (
                f"File type '{ext}' is not allowed. "
                f"Accepted types: {', '.join(settings.allowed_extensions)}"
            )
            raise ValueError(msg)

        # Check file size
        if file_size > settings.max_upload_size:
            max_mb = settings.max_upload_size / (1024 * 1024)
            msg = f"File size exceeds the {max_mb:.0f}MB limit."
            raise ValueError(msg)

        # Magic bytes sniffing for file spoofing protection
        if content:
            if ext == ".pdf" and not content.startswith(b"%PDF"):
                raise ValueError("Security check failed: File content does not match valid PDF format.")
            if ext in (".docx", ".doc") and not content.startswith(b"PK\x03\x04"):
                raise ValueError("Security check failed: File content does not match valid DOCX format.")
            if ext == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Security check failed: File content does not match valid PNG format.")
            if ext in (".jpg", ".jpeg") and not content.startswith(b"\xff\xd8\xff"):
                raise ValueError("Security check failed: File content does not match valid JPEG format.")

        # Check MIME type if provided
        if content_type and content_type not in settings.allowed_mime_types:
            # Allow through if extension is valid — some systems send incorrect MIME types
            logger.warning(
                "MIME type '%s' not in allowlist but extension '%s' is valid. Allowing.",
                content_type,
                ext,
            )

    def extract_text(self, file_path: Path, filename: str) -> tuple[str, int]:
        """Extract text from a document file.

        Args:
            file_path: Path to the uploaded file.
            filename: Original filename (used to determine type).

        Returns:
            Tuple of (extracted_text, page_count).

        Raises:
            ValueError: If text extraction fails.
        """
        ext = Path(filename).suffix.lower()

        if ext == ".pdf":
            return self._extract_from_pdf(file_path)
        if ext in (".docx", ".doc"):
            return self._extract_from_docx(file_path)
        if ext in (".jpg", ".jpeg", ".png"):
            return self._extract_from_image(file_path)

        msg = f"Unsupported file type for text extraction: {ext}"
        raise ValueError(msg)

    def _extract_from_pdf(self, file_path: Path) -> tuple[str, int]:
        """Extract text from PDF using PyMuPDF."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(file_path))
            text_parts: list[str] = []
            for page in doc:
                text_parts.append(page.get_text())
            page_count = len(doc)
            doc.close()

            text = "\n\n".join(text_parts).strip()
            if not text:
                logger.warning("PDF text extraction returned empty — may be a scanned document")

            return text, page_count
        except Exception as e:
            logger.error("PDF extraction failed: %s", e)
            msg = f"Failed to extract text from PDF: {e}"
            raise ValueError(msg) from e

    def _extract_from_docx(self, file_path: Path) -> tuple[str, int]:
        """Extract text from DOCX using python-docx."""
        try:
            from docx import Document

            doc = Document(str(file_path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            text = "\n\n".join(paragraphs)

            # Approximate page count (rough: ~3000 chars per page)
            page_count = max(1, len(text) // 3000)

            return text, page_count
        except Exception as e:
            logger.error("DOCX extraction failed: %s", e)
            msg = f"Failed to extract text from DOCX: {e}"
            raise ValueError(msg) from e

    def _extract_from_image(self, file_path: Path) -> tuple[str, int]:
        """Extract text from image using Gemini vision capabilities.

        Uses Gemini's native document understanding for OCR.
        """
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)
            image_bytes = file_path.read_bytes()
            ext = file_path.suffix.lower()

            mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}
            mime_type = mime_map.get(ext, "image/jpeg")

            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "Extract all text from this document image. Return only the extracted text, "
                    "preserving the original formatting and structure as much as possible. "
                    "If the text is in a language other than English, preserve the original text.",
                ],
            )

            text = response.text.strip() if response.text else ""
            return text, 1
        except Exception as e:
            logger.error("Image OCR via Gemini failed: %s", e)
            msg = f"Failed to extract text from image: {e}"
            raise ValueError(msg) from e

    def save_temp_file(self, content: bytes, filename: str) -> Path:
        """Save uploaded content to a temporary file.

        Args:
            content: File content bytes.
            filename: Original filename.

        Returns:
            Path to the saved temporary file.
        """
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix
        with tempfile.NamedTemporaryFile(
            dir=str(settings.upload_dir),
            suffix=ext,
            delete=False,
        ) as temp_file:
            temp_file.write(content)
        return Path(temp_file.name)



    def cleanup_temp_file(self, file_path: Path) -> None:
        """Remove a temporary file."""
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError as e:
            logger.warning("Failed to cleanup temp file %s: %s", file_path, e)
