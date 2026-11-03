"""报告与章节数据模型。

阶段 2-2 新增：truth_base（关键事实，只提炼一次不展示）、写全文进度、章节正文/审计/重写/记忆等字段。
状态取值对齐 PRD F2：待确认大纲 / 写作中 / 已暂停 / 已完成 / 失败。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base

DEFAULT_OWNER = "local"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[str] = mapped_column(String(64), default=DEFAULT_OWNER, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    target_words: Mapped[int] = mapped_column(Integer, nullable=False)
    user_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="待确认大纲", nullable=False)
    outline_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 阶段 2-2 新增
    truth_base: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON：validated_data/sources/global_terminology
    writing_status: Mapped[str] = mapped_column(String(32), default="未开始", nullable=False)  # 未开始/提炼中/写作中/完成/失败
    current_chapter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 当前第几章（1 起）
    current_substep: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 检索中/写作中/压缩中/审计中/重写中
    user_notices: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组，去重后的冲突提示
    write_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False)


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    chapter_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    key_points: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 数组
    data_needed: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 数组
    suggested_words: Mapped[int] = mapped_column(Integer, nullable=False)
    # 阶段 2-2 新增
    body: Mapped[str | None] = mapped_column(Text, nullable=True)  # 定稿正文（用户修改后覆盖）
    original_body: Mapped[str | None] = mapped_column(Text, nullable=True)  # AI 原稿，不随修改变化
    status: Mapped[str] = mapped_column(String(32), default="等待", nullable=False)  # 等待/写作中/通过/待人工/失败
    audit: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON：最后一次审计
    rewrite_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    truncated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retrieved: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON：检索到的段落文件名
    missing: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON：本章 [待补充] 名称
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # 定稿摘要（≤100 字），写记忆用
    user_notice: Mapped[str | None] = mapped_column(Text, nullable=True)  # 本章冲突提示（可空）
