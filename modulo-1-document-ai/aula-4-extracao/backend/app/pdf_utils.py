import fitz  # PyMuPDF
from fpdf import FPDF
from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path) -> list[dict]:
    """Extract text from each page of a PDF.

    Returns a list of dicts with 'page' (1-indexed) and 'text' keys.
    """
    doc = fitz.open(str(pdf_path))
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        pages.append({"page": i + 1, "text": text})
    doc.close()
    return pages


def format_document_text(pages: list[dict]) -> str:
    """Format extracted pages into a single string with page markers."""
    parts = []
    for p in pages:
        parts.append(f"--- Página {p['page']} ---\n{p['text']}")
    return "\n\n".join(parts)


def text_to_pdf(text: str, output_path: str | Path):
    """Convert plain text to a PDF file."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    for line in text.split("\n"):
        if line.strip() == "":
            pdf.ln(5)
        else:
            pdf.multi_cell(0, 6, line)

    pdf.output(str(output_path))


def find_text_bounding_box(
    pdf_path: str | Path, page_num: int, transcription: str
) -> dict | None:
    """Find the bounding box of a text transcription on a specific page.

    Args:
        pdf_path: Path to the PDF file
        page_num: 1-indexed page number
        transcription: The text to search for

    Returns:
        Normalized bounding box dict {x0, y0, x1, y1, page} or None
    """
    if not transcription or page_num is None or page_num < 1:
        return None

    doc = fitz.open(str(pdf_path))
    if page_num > len(doc):
        doc.close()
        return None

    page = doc[page_num - 1]
    page_rect = page.rect

    # Try exact match first
    areas = page.search_for(transcription)
    if areas:
        bbox = _merge_rects(_first_occurrence(areas))
        result = _normalize_bbox(bbox, page_rect, page_num)
        doc.close()
        return result

    # Try progressively shorter prefixes
    text = transcription.strip()
    for length in range(len(text) - 1, min(9, len(text) - 1), -1):
        partial = text[:length]
        areas = page.search_for(partial)
        if areas:
            bbox = _merge_rects(_first_occurrence(areas))
            result = _normalize_bbox(bbox, page_rect, page_num)
            doc.close()
            return result

    # Try key phrases (split by common separators and search for longest match)
    words = text.split()
    for window_size in range(len(words), 0, -1):
        for start in range(len(words) - window_size + 1):
            phrase = " ".join(words[start : start + window_size])
            if len(phrase) < 5:
                continue
            areas = page.search_for(phrase)
            if areas:
                bbox = _merge_rects(_first_occurrence(areas))
                result = _normalize_bbox(bbox, page_rect, page_num)
                doc.close()
                return result

    # Fallback: return full page bounding box
    doc.close()
    return {"x0": 0.0, "y0": 0.0, "x1": 1.0, "y1": 1.0, "page": page_num}


def _first_occurrence(rects: list) -> list:
    """search_for returns one rect per line for every match on the page.
    Keep only the rects of the first match: consecutive lines that are
    vertically adjacent to each other."""
    group = [rects[0]]
    for r in rects[1:]:
        prev = group[-1]
        if 0 <= r.y0 - prev.y1 <= prev.height:
            group.append(r)
        else:
            break
    return group


def _merge_rects(rects: list) -> fitz.Rect:
    """Merge multiple rectangles into one bounding rectangle."""
    result = rects[0]
    for r in rects[1:]:
        result |= r
    return result


def _normalize_bbox(bbox: fitz.Rect, page_rect: fitz.Rect, page_num: int) -> dict:
    """Normalize bounding box coordinates to 0-1 range."""
    return {
        "x0": max(0.0, bbox.x0 / page_rect.width),
        "y0": max(0.0, bbox.y0 / page_rect.height),
        "x1": min(1.0, bbox.x1 / page_rect.width),
        "y1": min(1.0, bbox.y1 / page_rect.height),
        "page": page_num,
    }
