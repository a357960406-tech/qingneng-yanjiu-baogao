"""资料相关的输入输出结构。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_type: str
    status: str
    chunk_count: int
    char_count: int
    error_reason: str | None = None
    created_at: str


class DocumentListOut(BaseModel):
    items: list[DocumentOut]
