import re

MAX_TOKENS = 600


class Chunk:
    __slots__ = ("content", "heading_path", "page_number")

    def __init__(self, content: str, heading_path: str = "", page_number: int | None = None):
        self.content = content
        self.heading_path = heading_path
        self.page_number = page_number


def _est_tokens(text: str) -> int:
    return max(1, len(text) // 2)  # 中英混合粗略估算


def _split_long(content: str) -> list[str]:
    paras = [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]
    result: list[str] = []
    current = ""
    for p in paras:
        if _est_tokens(current + "\n" + p) > MAX_TOKENS and current:
            result.append(current.strip())
            current = p
        else:
            current = current + "\n" + p
    if current.strip():
        result.append(current.strip())
    return result


def chunk_text_page(text: str, page_number: int | None = None) -> list[Chunk]:
    """标题感知分块：按 Markdown 标题切，超长段落按 token 数二次切。"""
    lines = text.splitlines()
    chunks: list[Chunk] = []
    stack: list[tuple[int, str]] = []
    buffer: list[str] = []

    def flush():
        content = "\n".join(buffer).strip()
        if not content:
            buffer.clear()
            return
        heading = " / ".join(title for _, title in stack)
        if _est_tokens(content) > MAX_TOKENS:
            for para in _split_long(content):
                chunks.append(Chunk(para, heading, page_number))
        else:
            chunks.append(Chunk(content, heading, page_number))
        buffer.clear()

    for line in lines:
        m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if m:
            flush()
            level = len(m.group(1))
            title = m.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        else:
            buffer.append(line)
    flush()
    return chunks


def chunk_document(pages: list[tuple[str, int | None]]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for text, page in pages:
        chunks.extend(chunk_text_page(text, page))
    return chunks
