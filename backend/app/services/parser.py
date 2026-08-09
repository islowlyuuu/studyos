import io

import pdfplumber


def parse_document(filename: str, data: bytes, file_type: str) -> list[tuple[str, int | None]]:
    """把原始文件解析为 [(文本, 页码)]，页码仅 PDF 有值。"""
    if file_type == "pdf":
        return _parse_pdf(data)
    return [(_decode_text(data), None)]


def _decode_text(data: bytes) -> str:
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_pdf(data: bytes) -> list[tuple[str, int | None]]:
    pages: list[tuple[str, int | None]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append((text, i))
    return pages
