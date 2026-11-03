"""资料（上传文件）与切段数据模型。

阶段 2-1：切段存进 SQLite 的 chunks 表；语义检索索引（Chroma）到 2-2 再建。
所有业务记录从第一张表起带归属字段 owner_id（当前不登录，写固定默认值）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base

DEFAULT_OWNER = "local"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), default=DEFAULT_OWNER, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)  # 安全处理后的展示名
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False)  # 落盘文件名
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)  # pdf/docx/md/txt
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 可用/无文字/失败
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 提取到的正文字符数
    error_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 从 1 开始
    text: Mapped[str] = mapped_column(Text, nullable=False)
