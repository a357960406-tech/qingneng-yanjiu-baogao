"""写全文接口：一键写全文（后台）、进度查询、从第 N 章继续。"""
from __future__ import annotations

import json
import threading

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.database import get_db
from app.models.report import Chapter, Report
from app.services.writing_service import run_writing_job

router = APIRouter(prefix="/api/v1/reports", tags=["writing"])

# 单进程内防止重复启动写全文
_running: set[int] = set()
_lock = threading.Lock()


class ChapterProgress(BaseModel):
    chapter_id: int
    title: str
    suggested_words: int
    status: str
    rewrite_count: int
    truncated: bool
    body: str | None = None
    missing: list[str] = []
    issues: list[dict] = []
    warnings: list[dict] = []


class ProgressOut(BaseModel):
    report_id: int
    report_status: str
    writing_status: str
    current_chapter: int
    total_chapters: int
    current_substep: str | None = None
    write_error: str | None = None
    user_notices: list[str] = []
    truth_sources: dict = {}
    chapters: list[ChapterProgress]


def _progress(db: Session, report: Report) -> ProgressOut:
    chapters = db.scalars(
        select(Chapter).where(Chapter.report_id == report.id).order_by(Chapter.chapter_id)
    ).all()
    items: list[ChapterProgress] = []
    for ch in chapters:
        audit = json.loads(ch.audit) if ch.audit else {}
        issues = [i for i in audit.get("issues", []) if str(i.get("severity", "")).upper() == "CRITICAL"]
        warnings = [i for i in audit.get("issues", []) if str(i.get("severity", "")).upper() == "WARNING"]
        items.append(
            ChapterProgress(
                chapter_id=ch.chapter_id,
                title=ch.title,
                suggested_words=ch.suggested_words,
                status=ch.status,
                rewrite_count=ch.rewrite_count,
                truncated=ch.truncated,
                body=ch.body,
                missing=json.loads(ch.missing) if ch.missing else [],
                issues=issues,
                warnings=warnings,
            )
        )
    truth = json.loads(report.truth_base) if report.truth_base else {}
    return ProgressOut(
        report_id=report.id,
        report_status=report.status,
        writing_status=report.writing_status,
        current_chapter=report.current_chapter,
        total_chapters=len(chapters),
        current_substep=report.current_substep,
        write_error=report.write_error,
        user_notices=json.loads(report.user_notices) if report.user_notices else [],
        truth_sources=truth.get("sources", {}),
        chapters=items,
    )


def _get_report(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise AppError("not_found", "报告不存在", status_code=404)
    return report


@router.post("/{report_id}/write", response_model=ProgressOut, status_code=202)
def start_writing(report_id: int, db: Session = Depends(get_db)) -> ProgressOut:
    report = _get_report(db, report_id)
    if not report.outline_confirmed:
        raise AppError("outline_not_confirmed", "请先确认大纲再写全文")
    with _lock:
        if report_id in _running:
            raise AppError("already_writing", "写全文已经在进行中")
        _running.add(report_id)

    def _job() -> None:
        try:
            run_writing_job(report_id)
        finally:
            with _lock:
                _running.discard(report_id)

    threading.Thread(target=_job, daemon=True).start()
    return _progress(db, report)


@router.post("/{report_id}/write/continue", response_model=ProgressOut, status_code=202)
def continue_writing(report_id: int, db: Session = Depends(get_db)) -> ProgressOut:
    """从第 N 章继续：已定稿章节不重写，truth_base 沿用已提炼的。"""
    report = _get_report(db, report_id)
    if not report.outline_confirmed:
        raise AppError("outline_not_confirmed", "请先确认大纲再写全文")
    with _lock:
        if report_id in _running:
            raise AppError("already_writing", "写全文已经在进行中")
        _running.add(report_id)

    def _job() -> None:
        try:
            run_writing_job(report_id)
        finally:
            with _lock:
                _running.discard(report_id)

    threading.Thread(target=_job, daemon=True).start()
    return _progress(db, report)


@router.get("/{report_id}/progress", response_model=ProgressOut)
def get_progress(report_id: int, db: Session = Depends(get_db)) -> ProgressOut:
    return _progress(db, _get_report(db, report_id))
