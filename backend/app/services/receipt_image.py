"""Extract text locally from digital PDFs and receipt photos."""
from pypdf import PdfReader
from pypdf.errors import PyPdfError
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image, UnidentifiedImageError
from io import BytesIO


class NoReceiptText(ValueError):
    pass


def receipt_text(content, *, psm=None):
    if content.startswith(b"%PDF-"):
        try:
            pdf = PdfReader(BytesIO(content))
            if pdf.is_encrypted or not 1 <= len(pdf.pages) <= 4:
                raise ValueError("Use an unencrypted receipt of one to four pages")
            text = "\n".join(page.extract_text() or "" for page in pdf.pages).strip()
        except (PyPdfError, OSError) as exc:
            raise ValueError("Unreadable PDF receipt") from exc
        if not text or len(text) > 12000:
            raise ValueError("Use a text PDF, or upload the scanned page as an image for OCR")
        return text

    with TemporaryDirectory() as folder:
        image_path = Path(folder) / "receipt.png"
        try:
            with Image.open(BytesIO(content)) as image:
                if image.format not in {"JPEG", "PNG"} or image.width * image.height > 12000000:
                    raise ValueError("Use a PNG or JPEG under 12 megapixels")
                image.thumbnail((2600, 2600))
                image.convert("RGB").save(image_path)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise ValueError("Unreadable receipt image") from exc
        if shutil.which("tesseract"):
            command = ["tesseract", str(image_path), "stdout"]
            if psm is not None:
                command.extend(["--psm", str(psm)])
        else:
            raise ValueError("Image OCR requires Tesseract on this server. Paste receipt text instead.")
        try:
            result = subprocess.run(command, capture_output=True, timeout=30, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError("Local OCR unavailable. Paste receipt text instead.") from exc
        text = result.stdout.decode("utf-8-sig", errors="replace").strip()
        if not text:
            raise NoReceiptText("No receipt text found. Paste the merchant, date and INR total.")
        if len(text) > 12000:
            raise ValueError("No usable receipt text. Paste the merchant, date and INR total.")
        return text
