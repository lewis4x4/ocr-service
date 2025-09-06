# Simple, safe starter: PDF text fast-path; image path stub.
# You can upgrade later to add OCR fallback (pdf2image -> Vision).

import mimetypes
from typing import Dict, Any, Tuple, List, Optional
import fitz  # PyMuPDF
from pydantic import BaseModel, Field

class PipelineConfig(BaseModel):
    min_text_chars: int = 300
    currency_default: str = "USD"

class Expense(BaseModel):
    vendor: Optional[str] = None
    date: Optional[str] = None
    end_date: Optional[str] = None
    currency: Optional[str] = "USD"
    subtotal: Optional[float] = None
    taxes_fees: Optional[float] = None
    total: Optional[float] = None
    nights: Optional[int] = None
    category: Optional[str] = "Lodging"

def process_upload(file_bytes: bytes, filename: str, mime: Optional[str], cfg: PipelineConfig) -> Expense:
    mime = mime or mimetypes.guess_type(filename, strict=False)[0] or "application/octet-stream"

    if mime.startswith("image/"):
        # TODO: Send image bytes to Vision OCR (later). For now, return empty draft.
        return Expense()

    if mime == "application/pdf":
        text, _prov = extract_pdf_text(file_bytes)
        if len(text) >= cfg.min_text_chars:
            data = simple_extract(text)
            return Expense(**data)
        # If PDF had no text (scanned), return minimal draft; upgrade later with OCR fallback.
        return Expense()

    # Unsupported types: return minimal draft
    return Expense()

def extract_pdf_text(pdf_bytes: bytes) -> Tuple[str, List[Dict[str, Any]]]:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    parts, prov = [], []
    for i, page in enumerate(doc):
        t = page.get_text("text")
        if t.strip():
            parts.append(t)
            prov.append({"source": "pdf_text", "page": i+1, "score": 0.9})
    return "\n".join(parts), prov

# VERY simple field picking (works for many receipts/confirmations)
def simple_extract(text: str) -> Dict[str, Any]:
    import re
    def pick(pats):
        for p in pats:
            m = re.search(p, text, re.I|re.S)
            if m: return (m.group(1) if m.lastindex else m.group(0)).strip()
        return None
    def pick_num(pats):
        v = pick(pats)
        try: return float(v) if v else None
        except: return None
    def pick_int(pats):
        v = pick(pats)
        try: return int(v) if v else None
        except: return None

    return {
        "vendor": pick([r"(?m)^(.*Sonesta.*)$", r"Hotel[:\s]+(.+)$", r"Vendor[:\s]+(.+)$"]),
        "date": pick([r"Check-in.*?([A-Za-z]{3},?\s?\w+\s?\d{1,2})", r"Date[:\s]+(\d{4}-\d{2}-\d{2})"]),
        "end_date": pick([r"Check-?out.*?([A-Za-z]{3},?\s?\w+\s?\d{1,2})"]),
        "currency": "USD",
        "subtotal": pick_num([r"Subtotal\s*\$([\d\.]+)", r"1\s*night\s*\$([\d\.]+)"]),
        "taxes_fees": pick_num([r"Taxes\s*&\s*fees\s*\$([\d\.]+)"]),
        "total": pick_num([r"Total\s*\$([\d\.]+)"]),
        "nights": pick_int([r"(\d+)\s*night"]),
        "category": "Lodging",
    }
