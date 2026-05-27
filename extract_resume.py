"""
Resume PDF text extractor. Try multiple approaches in order:
1. PyPDF2 (fast, text-based PDFs)
2. pdfplumber (better table/layout handling)
3. pymupdf / fitz (handles more Chinese font encodings)
4. OCR via pytesseract + pymupdf renderer (image-based PDFs)

Usage: python extract_resume.py <pdf_path>
Outputs extracted text to stdout.
"""

import sys
import os
import subprocess
import importlib
import tempfile
import io


def install(package: str):
    """Install a PyPI package."""
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package, "-q"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def try_pypdf2(path: str) -> str | None:
    try:
        importlib.import_module("PyPDF2")
    except ImportError:
        try:
            install("PyPDF2")
            importlib.import_module("PyPDF2")
        except Exception:
            return None

    from PyPDF2 import PdfReader
    reader = PdfReader(path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text and text.strip():
            parts.append(text.strip())
    result = "\n\n".join(parts)
    return result if result.strip() else None


def try_pdfplumber(path: str) -> str | None:
    try:
        importlib.import_module("pdfplumber")
    except ImportError:
        try:
            install("pdfplumber")
            importlib.import_module("pdfplumber")
        except Exception:
            return None

    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text and text.strip():
                parts.append(text.strip())
    result = "\n\n".join(parts)
    return result if result.strip() else None


def try_pymupdf(path: str) -> str | None:
    """Try pymupdf (fitz) which handles more Chinese font encodings."""
    try:
        importlib.import_module("fitz")
    except ImportError:
        try:
            install("pymupdf")
            importlib.import_module("fitz")
        except Exception:
            return None

    import fitz
    doc = fitz.open(path)
    parts = []
    for page in doc:
        text = page.get_text()
        if text and text.strip():
            parts.append(text.strip())
    doc.close()
    result = "\n\n".join(parts)
    return result if result.strip() else None


def try_ocr(path: str) -> str | None:
    """OCR using pymupdf for rendering + pytesseract for recognition.
    Requires: Tesseract OCR installed with chi_sim language data."""
    try:
        importlib.import_module("fitz")
        importlib.import_module("pytesseract")
    except ImportError:
        try:
            install("pymupdf")
            install("pytesseract")
            install("Pillow")
        except Exception:
            return None

    import fitz
    import pytesseract
    from PIL import Image

    # Auto-detect tesseract path on Windows
    if sys.platform == "win32":
        for tpath in [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]:
            if os.path.exists(tpath):
                pytesseract.pytesseract.tesseract_cmd = tpath
                break

    # Also check TESSDATA_PREFIX for chi_sim
    if "TESSDATA_PREFIX" not in os.environ:
        for prefix in [
            r"C:\Program Files\Tesseract-OCR",
            r"C:\Program Files (x86)\Tesseract-OCR",
            os.path.join(os.environ.get("TEMP", "/tmp"), "tessdata"),
        ]:
            if os.path.exists(os.path.join(prefix, "tessdata", "chi_sim.traineddata")):
                os.environ["TESSDATA_PREFIX"] = prefix
                break

    doc = fitz.open(path)
    parts = []
    for page in doc:
        pix = page.get_pixmap(dpi=250)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        if text and text.strip():
            parts.append(text.strip())
    doc.close()
    result = "\n\n".join(parts)
    return result if result.strip() else None


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_resume.py <pdf_path>", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    for name, func in [
        ("PyPDF2", try_pypdf2),
        ("pdfplumber", try_pdfplumber),
        ("PyMuPDF", try_pymupdf),
        ("OCR", try_ocr),
    ]:
        print(f"[{name}] Trying to extract text...", file=sys.stderr)
        result = func(pdf_path)
        if result:
            print(f"[{name}] Success! ({len(result)} chars)", file=sys.stderr)
            print(result)
            return
        else:
            print(f"[{name}] No text extracted.", file=sys.stderr)

    print("Error: All extraction methods failed.", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
