"""Tests for document service (validation, text extraction)."""

import pytest

from app.services.document_service import DocumentService


class TestFileValidation:
    """Tests for file upload validation."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.service = DocumentService()

    def test_valid_pdf(self):
        # Should not raise
        self.service.validate_file("document.pdf", 1024 * 100, "application/pdf")

    def test_valid_docx(self):
        self.service.validate_file(
            "contract.docx", 1024 * 500,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_valid_image(self):
        self.service.validate_file("photo.jpg", 1024 * 200, "image/jpeg")
        self.service.validate_file("scan.png", 1024 * 300, "image/png")

    def test_reject_exe(self):
        with pytest.raises(ValueError, match="not allowed"):
            self.service.validate_file("malware.exe", 1024, "application/octet-stream")

    def test_reject_zip(self):
        with pytest.raises(ValueError, match="not allowed"):
            self.service.validate_file("archive.zip", 1024, "application/zip")

    def test_reject_oversized(self):
        with pytest.raises(ValueError, match="exceeds"):
            self.service.validate_file("big.pdf", 11 * 1024 * 1024, "application/pdf")

    def test_reject_script(self):
        with pytest.raises(ValueError, match="not allowed"):
            self.service.validate_file("hack.js", 100, "text/javascript")

    def test_exactly_at_limit(self):
        # Exactly 10MB should be fine
        self.service.validate_file("exact.pdf", 10 * 1024 * 1024, "application/pdf")

    def test_one_byte_over_limit(self):
        with pytest.raises(ValueError, match="exceeds"):
            self.service.validate_file("over.pdf", 10 * 1024 * 1024 + 1, "application/pdf")

    def test_valid_pdf_magic_bytes(self):
        # Should pass when binary starts with %PDF
        self.service.validate_file("legit.pdf", 1024, "application/pdf", content=b"%PDF-1.4 test binary data")

    def test_reject_spoofed_pdf_magic_bytes(self):
        # Should reject executable masquerading as a PDF
        with pytest.raises(ValueError, match="valid PDF format"):
            self.service.validate_file("malware.pdf", 1024, "application/pdf", content=b"MZ\x90\x00\x03\x00\x00\x00")

    def test_reject_spoofed_png_magic_bytes(self):
        # Should reject invalid header on png file
        with pytest.raises(ValueError, match="valid PNG format"):
            self.service.validate_file("fake.png", 1024, "image/png", content=b"RIFF\x00\x00\x00\x00WEBP")

    def test_valid_docx_magic_bytes(self):
        # Zip/DOCX PK magic bytes
        self.service.validate_file(
            "valid.docx", 1024,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content=b"PK\x03\x04\x14\x00\x06\x00"
        )

