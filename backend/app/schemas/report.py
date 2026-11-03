"""报告与大纲相关的输入输出结构。"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_TARGET_WORDS = 18000
DEFAULT_TARGET_WORDS = 12000


class ReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    target_words: int = Field(default=DEFAULT_TARGET_WORDS, ge=1, le=MAX_TARGET_WORDS)
    user_requirements: str | None = Field(default=None, max_length=2000)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    target_words: int
    user_requirements: str | None = None
    status: str
    outline_confirmed: bool
    created_at: str


class ReportListOut(BaseModel):
    items: list[ReportOut]


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chapter_id: int
    title: str
    key_points: list[str]
    data_needed: list[str]
    suggested_words: int


class OutlineOut(BaseModel):
    report_id: int
    chapters: list[ChapterOut]
    total_words: int
    notice: str | None = None  # 章数不在 8-13 时提示手动增删
