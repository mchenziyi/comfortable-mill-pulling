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
    """OCR using pymupdf for rendering + tesseract CLI for recognition.
    Avoids pytesseract's numpy dependency issues."""
    try:
        importlib.import_module("fitz")
    except ImportError:
        try:
            install("pymupdf")
            importlib.import_module("fitz")
        except Exception:
            return None

    import fitz
    from PIL import Image

    # Find tesseract binary
    tesseract_bin = None
    for tpath in [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]:
        if os.path.exists(tpath):
            tesseract_bin = tpath
            break
    else:
        # Try PATH
        import shutil
        found = shutil.which("tesseract")
        if found:
            tesseract_bin = found

    if not tesseract_bin:
        print("[OCR] Tesseract not found. Install: winget install UB-Mannheim.TesseractOCR", file=sys.stderr)
        return None

    # Find chi_sim language data
    tessdata_prefix = os.environ.get("TESSDATA_PREFIX", "")
    if not tessdata_prefix:
        for prefix in [
            r"C:\Program Files\Tesseract-OCR",
            r"C:\Program Files (x86)\Tesseract-OCR",
        ]:
            if os.path.exists(os.path.join(prefix, "tessdata", "chi_sim.traineddata")):
                tessdata_prefix = prefix
                break
        else:
            custom = os.path.join(os.environ.get("TEMP", "/tmp"), "tessdata")
            if os.path.exists(os.path.join(custom, "chi_sim.traineddata")):
                tessdata_prefix = custom

    env = os.environ.copy()
    if tessdata_prefix:
        env["TESSDATA_PREFIX"] = tessdata_prefix

    doc = fitz.open(path)
    parts = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=250)
            png_path = os.path.join(tmp, f"page_{i}.png")
            txt_path = os.path.join(tmp, f"page_{i}")
            pix.save(png_path)
            try:
                subprocess.run(
                    [tesseract_bin, png_path, txt_path, "-l", "chi_sim+eng"],
                    capture_output=True, timeout=30, env=env
                )
                with open(txt_path + ".txt", "r", encoding="utf-8") as f:
                    text = f.read().strip()
                if text:
                    parts.append(text)
            except Exception:
                pass
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
