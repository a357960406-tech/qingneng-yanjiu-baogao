"""报告与大纲接口。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.database import get_db
from app.models.report import Chapter, Report
from app.schemas.report import (
    ChapterOut,
    OutlineOut,
    ReportCreate,
    ReportListOut,
    ReportOut,
)
from app.services.model_client import ModelClient, ModelError
from app.services.outline_service import generate_outline

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _to_out(r: Report) -> ReportOut:
    return ReportOut(
        id=r.id,
        title=r.title,
        target_words=r.target_words,
        user_requirements=r.user_requirements,
        status=r.status,
        outline_confirmed=r.outline_confirmed,
        created_at=r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    )


def _get_report(db: Session, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise AppError("not_found", "报告不存在", status_code=404)
    return report


@router.post("", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate, db: Session = Depends(get_db)) -> ReportOut:
    report = Report(
        title=payload.title.strip(),
        target_words=payload.target_words,
        user_requirements=payload.user_requirements.strip() if payload.user_requirements else None,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _to_out(report)


@router.get("", response_model=ReportListOut)
def list_reports(db: Session = Depends(get_db)) -> ReportListOut:
    reports = db.scalars(select(Report).order_by(Report.created_at.desc())).all()
    return ReportListOut(items=[_to_out(r) for r in reports])


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, db: Session = Depends(get_db)) -> ReportOut:
    return _to_out(_get_report(db, report_id))


def _chapters_out(db: Session, report_id: int) -> list[ChapterOut]:
    chapters = db.scalars(
        select(Chapter).where(Chapter.report_id == report_id).order_by(Chapter.chapter_id)
    ).all()
    return [
        ChapterOut(
            chapter_id=c.chapter_id,
            title=c.title,
            key_points=json.loads(c.key_points or "[]"),
            data_needed=json.loads(c.data_needed or "[]"),
            suggested_words=c.suggested_words,
        )
        for c in chapters
    ]


@router.post("/{report_id}/outline", response_model=OutlineOut)
def create_outline(report_id: int, db: Session = Depends(get_db)) -> OutlineOut:
    report = _get_report(db, report_id)
    try:
        client = ModelClient()
        result = generate_outline(
            client,
            title=report.title,
            target_words=report.target_words,
            user_requirements=report.user_requirements,
        )
    except ModelError as exc:
        raise AppError("model_unavailable", str(exc), status_code=503) from exc
    except ValueError as exc:
        raise AppError("model_output_invalid", str(exc), status_code=502) from exc

    # 重新生成：清掉本报告旧章节，写入新章节
    db.query(Chapter).filter(Chapter.report_id == report_id).delete()
    for ch in result.chapters:
        db.add(
            Chapter(
                report_id=report_id,
                chapter_id=ch.chapter_id,
                title=ch.title,
                key_points=json.dumps(ch.key_points, ensure_ascii=False),
                data_needed=json.dumps(ch.data_needed, ensure_ascii=False),
                suggested_words=ch.suggested_words,
            )
        )
    report.outline_confirmed = False
    db.commit()

    return OutlineOut(
        report_id=report_id,
        chapters=_chapters_out(db, report_id),
        total_words=result.total_words,
        notice=result.notice,
    )


@router.get("/{report_id}/outline", response_model=OutlineOut)
def get_outline(report_id: int, db: Session = Depends(get_db)) -> OutlineOut:
    report = _get_report(db, report_id)
    chapters = _chapters_out(db, report_id)
    return OutlineOut(
        report_id=report_id,
        chapters=chapters,
        total_words=sum(c.suggested_words for c in chapters),
        notice=None,
    )


@router.post("/{report_id}/outline/confirm", response_model=ReportOut)
def confirm_outline(report_id: int, db: Session = Depends(get_db)) -> ReportOut:
    report = _get_report(db, report_id)
    chapters = db.scalars(
        select(Chapter).where(Chapter.report_id == report_id).order_by(Chapter.chapter_id)
    ).all()
    if not chapters:
        raise AppError("no_outline", "还没有大纲，请先生成大纲")
    report.outline_confirmed = True
    db.commit()
    db.refresh(report)
    return _to_out(report)
