"""资料解析与切段。

规则来源：PRD V2.2 F1 + 第五节参数默认值。
- 支持 PDF、Word(.docx)、Markdown、TXT；单个文件 ≤ 100MB；
- 扫描件（平均每页提取不到 50 字）标「无文字，检索不到」；
- 切段：每段约 800 字，相邻两段重叠 100 字。
"""
from __future__ import annotations

import re
from pathlib import Path

SUPPORTED_TYPES = {"pdf", "docx", "md", "txt"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
SCAN_PAGE_MIN_CHARS = 50  # 平均每页少于这个字数视为扫描件


class DocumentParseError(RuntimeError):
    """解析失败（含格式不支持、文件过大、无文字）。"""


def safe_filename(filename: str) -> str:
    """安全文件名：去掉路径和危险字符，只保留基本名。"""
    name = Path(filename).name
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", name)
    name = name.strip("._") or "file"
    return name[:200]


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_upload(filename: str, size: int, header: bytes) -> str:
    """校验格式、大小、真实类型；通过返回扩展名（不含点）。"""
    ext = extension_of(filename)
    if ext not in SUPPORTED_TYPES:
        raise DocumentParseError(f"当前格式不支持，请上传 PDF、Word、Markdown 或 TXT")
    if size <= 0:
        raise DocumentParseError("文件为空")
    if size > MAX_FILE_SIZE:
        raise DocumentParseError("上传失败，最大支持 100M 文件")
    if ext == "pdf" and not header.lstrip().startswith(b"%PDF"):
        raise DocumentParseError("文件内容与 PDF 格式不符")
    if ext == "docx" and not header.startswith(b"PK"):
        raise DocumentParseError("文件内容与 Word(.docx) 格式不符")
    if ext in {"md", "txt"}:
        # 文本文件要能按常见编码解码
        _decode_text(header)
    return ext


def _decode_text(data: bytes) -> str:
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise DocumentParseError("文本编码无法识别")


def extract_text(file_type: str, path: Path) -> tuple[str, int]:
    """提取正文。返回 (正文, 页数或 1)。PDF 返回页数用于扫描件判断。"""
    if file_type == "txt" or file_type == "md":
        text = _decode_text(path.read_bytes())
        return text, 1

    if file_type == "docx":
        try:
            from docx import Document as DocxDocument

            doc = DocxDocument(str(path))
            parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
            # 表格里的文字也提取
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text and cell.text.strip():
                            parts.append(cell.text)
            return "\n".join(parts), 1
        except Exception as exc:
            raise DocumentParseError(f"Word 解析失败：{type(exc).__name__}") from exc

    if file_type == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages), max(len(pages), 1)
        except Exception as exc:
            raise DocumentParseError(f"PDF 解析失败：{type(exc).__name__}") from exc

    raise DocumentParseError(f"当前格式不支持，请上传 PDF、Word、Markdown 或 TXT")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """按约 800 字切段，相邻重叠 100 字。"""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = end - overlap
    return chunks


def parse_and_chunk(file_type: str, path: Path) -> tuple[str, list[str], int]:
    """返回 (status, chunks, char_count)。status ∈ 可用/无文字。"""
    text, pages = extract_text(file_type, path)
    stripped = text.strip()
    if not stripped:
        return "无文字", [], 0
    # 扫描件判断：平均每页不到 50 字
    if file_type == "pdf" and len(stripped) / pages < SCAN_PAGE_MIN_CHARS:
        return "无文字", [], len(stripped)
    chunks = chunk_text(stripped)
    if not chunks:
        return "无文字", [], len(stripped)
    return "可用", chunks, len(stripped)
