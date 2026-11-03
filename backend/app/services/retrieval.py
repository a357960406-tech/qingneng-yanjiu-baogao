"""资料库检索（阶段 2-2 用关键词打分，只检索资料库 chunks 表）。

PRD C01：大纲不检索；关键事实提炼和写章只检索资料库。
本阶段用轻量关键词打分（CJK 双字词 + ASCII 词），语义向量检索（Chroma + 本地 embedding）
在效果不达标时再引入（见《技术适配声明》）。
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Chunk, Document

_CJK = re.compile(r"[\u4e00-\u9fff]")
_ASCII_WORD = re.compile(r"[A-Za-z0-9]+")


def _terms(text: str) -> set[str]:
    """提取检索词：中文双字词 + 英文/数字词。"""
    terms: set[str] = set()
    ascii_words = _ASCII_WORD.findall(text)
    terms.update(w.lower() for w in ascii_words if len(w) >= 2)
    cjk = _CJK.findall(text)
    for i in range(len(cjk) - 1):
        terms.add(cjk[i] + cjk[i + 1])
    return terms


def _score(query_terms: set[str], chunk_text: str) -> int:
    return sum(1 for t in query_terms if t in chunk_text)


def retrieve_chunks(db: Session, query: str, k: int = 6) -> list[str]:
    """返回最多 k 段，每段开头带【来源：文件名】。"""
    if not query.strip():
        return []
    query_terms = _terms(query)
    if not query_terms:
        return []
    rows = db.execute(
        select(Chunk.id, Chunk.text, Document.filename)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.status == "可用")
    ).all()
    scored = [( _score(query_terms, text), filename, text) for _, text, filename in rows]
    scored = [s for s in scored if s[0] > 0]
    scored.sort(key=lambda x: (-x[0], x[2]))
    return [f"【来源：{filename}】\n{text}" for _, filename, text in scored[:k]]
