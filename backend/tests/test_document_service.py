"""资料解析与切段的纯函数测试（mock，不调模型、不联网）。"""
from __future__ import annotations

import pytest

from app.services import document_service as ds


def test_chunk_text_basic():
    text = "字" * 2000
    chunks = ds.chunk_text(text)
    assert len(chunks) >= 3
    assert chunks[0] == text[: ds.CHUNK_SIZE]
    assert chunks[-1].endswith(text[-1])  # 覆盖到最后一个字
    assert all(len(c) <= ds.CHUNK_SIZE for c in chunks)


def test_chunk_text_overlap():
    text = "字" * 1500
    chunks = ds.chunk_text(text)
    assert len(chunks) == 2
    # 第二段开头应包含第一段末尾的 100 字
    assert chunks[1][: ds.CHUNK_OVERLAP] == chunks[0][-ds.CHUNK_OVERLAP:]


def test_chunk_text_empty():
    assert ds.chunk_text("   ") == []


def test_validate_upload_unsupported_extension():
    with pytest.raises(ds.DocumentParseError):
        ds.validate_upload("a.exe", 10, b"MZ")


def test_validate_upload_oversize():
    with pytest.raises(ds.DocumentParseError):
        ds.validate_upload("a.txt", ds.MAX_FILE_SIZE + 1, b"x")


def test_validate_upload_pdf_bad_magic():
    with pytest.raises(ds.DocumentParseError):
        ds.validate_upload("a.pdf", 10, b"not a pdf")


def test_validate_upload_docx_bad_magic():
    with pytest.raises(ds.DocumentParseError):
        ds.validate_upload("a.docx", 10, b"not a zip")


def test_validate_upload_valid_txt():
    assert ds.validate_upload("a.txt", 10, "hello".encode("utf-8")) == "txt"


def test_safe_filename_strips_path():
    assert ds.safe_filename("../../etc/passwd") == "passwd"
    assert "/" not in ds.safe_filename("a/b.txt")


def test_parse_and_chunk_txt(tmp_path):
    path = tmp_path / "a.txt"
    path.write_text("这是正文。" * 300, encoding="utf-8")
    status, chunks, char_count = ds.parse_and_chunk("txt", path)
    assert status == "可用"
    assert char_count > 0
    assert chunks


def test_parse_and_chunk_empty_txt(tmp_path):
    path = tmp_path / "b.txt"
    path.write_text("   ", encoding="utf-8")
    status, chunks, char_count = ds.parse_and_chunk("txt", path)
    assert status == "无文字"
    assert chunks == []
