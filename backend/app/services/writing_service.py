"""写全文核心链路：逐章「检索 → 写 → 控字数 → 审计 → 重写(≤2) → 定稿」。

PRD V2.2 F5 与全局上下文管理：
- 提炼 truth_base 只在全文开始时做一次；
- 每章定稿（审计通过，或重写 2 次仍 CRITICAL 标待人工）后，才把摘要写入记忆；
- 上一章最后一句从 body 截取；
- 每章 user_notice 收集后去重，全文结束统一提示一次；
- 字数由程序控：超上限压缩一次，仍超在上限内最后一个句号处截断。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.logging import log
from app.models.database import SessionLocal
from app.models.report import Chapter, Report
from app.services.model_client import ModelClient, ModelError
from app.services.prompts.content import (
    build_compress_prompt,
    build_content_prompt,
    build_rewrite_prompt,
)
from app.services.prompts.audit import build_audit_prompt
from app.services.retrieval import retrieve_chunks
from app.services.truth_service import extract_truth_base


def count_words(text: str) -> int:
    """PRD 字数统计：正文去掉空格和换行后的字符数。"""
    return len(re.sub(r"\s", "", text or ""))


def last_sentence(text: str) -> str:
    """从正文截最后一句（按 。！？. 等句末标点切，取非空最后一段）。"""
    body = (text or "").strip()
    if not body:
        return ""
    parts = re.split(r"[。！？!?；;]", body)
    parts = [p.strip() for p in parts if p.strip()]
    return parts[-1] if parts else body


def truncate_at_last_sentence(text: str, max_words: int) -> str:
    """在上限内最后一个句号处截断。"""
    if count_words(text) <= max_words:
        return text
    sentences = re.split(r"(?<=[。！？!?])", text)
    out = ""
    for s in sentences:
        if count_words(out + s) <= max_words:
            out += s
        else:
            break
    return out if out else text[:max_words]


class ChapterDraft(BaseModel):
    body: str = ""
    summary: str = ""
    missing: list[str] = Field(default_factory=list)
    user_notice: str = ""


class AuditResult(BaseModel):
    critical_count: int = 0
    warning_count: int = 0
    issues: list[dict] = Field(default_factory=list)
    unverifiable: list[str] = Field(default_factory=list)


def parse_draft(data: dict) -> ChapterDraft:
    try:
        return ChapterDraft.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"写章输出结构不合法：{exc.errors()[0]}") from exc


def parse_audit(data: dict) -> AuditResult:
    try:
        return AuditResult.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"审计输出结构不合法：{exc.errors()[0]}") from exc


def _critical_issues(audit: AuditResult) -> list[dict]:
    return [i for i in audit.issues if str(i.get("severity", "")).upper() == "CRITICAL"]


def _chapter_task(ch: Chapter) -> str:
    return (
        f"标题：{ch.title}；关键论点：{json.dumps(json.loads(ch.key_points or '[]'), ensure_ascii=False)}；"
        f"所需数据：{json.dumps(json.loads(ch.data_needed or '[]'), ensure_ascii=False)}；建议字数：{ch.suggested_words}"
    )


@dataclass
class WriteOutcome:
    body: str
    summary: str
    missing: list[str]
    user_notice: str
    audit: AuditResult
    rewrite_count: int
    truncated: bool
    retrieved: list[str]


def _generate_with_control(
    client: ModelClient,
    report: Report,
    ch: Chapter,
    chapter_no: int,
    total: int,
    truth: dict,
    summaries: list[dict],
    last_ending: str,
    context: str,
) -> tuple[ChapterDraft, bool, str]:
    """写一章并控字数；返回 (draft, truncated, base_prompt)。"""
    max_words = int(ch.suggested_words * 1.1)
    base = build_content_prompt(
        title=report.title,
        user_requirements=report.user_requirements,
        chapter_no=chapter_no,
        total=total,
        chapter=_chapter_task(ch),
        max_words=max_words,
        truth_data=truth.get("validated_data", {}),
        terminology=truth.get("global_terminology", []),
        chapter_summaries=summaries,
        last_ending=last_ending,
        context=context,
    )
    client.step = f"写章-第{chapter_no}章"
    draft = parse_draft(client.generate_json(base))
    truncated = False
    if count_words(draft.body) > max_words:
        # 压缩一次
        client.step = f"压缩-第{chapter_no}章"
        draft = parse_draft(
            client.generate_json(
                build_compress_prompt(
                    base,
                    previous_body=draft.body,
                    previous_words=count_words(draft.body),
                    max_words=max_words,
                    suggested_words=ch.suggested_words,
                )
            )
        )
        if count_words(draft.body) > max_words:
            draft.body = truncate_at_last_sentence(draft.body, max_words)
            truncated = True
    return draft, truncated, base


def write_chapter(
    client: ModelClient,
    *,
    db: Session,
    report: Report,
    ch: Chapter,
    chapter_no: int,
    total: int,
    truth: dict,
    summaries: list[dict],
    last_ending: str,
) -> WriteOutcome:
    """写一章完整链路，返回结果（不落库）。"""
    context = retrieve_chunks(db, ch.title + " " + " ".join(json.loads(ch.key_points or "[]")), k=6)
    draft, truncated, base = _generate_with_control(
        client, report, ch, chapter_no, total, truth, summaries, last_ending, "\n\n".join(context)
    )

    client.step = f"审计-第{chapter_no}章"
    audit = parse_audit(
        client.generate_json(
            build_audit_prompt(
                truth_data=truth.get("validated_data", {}),
                terminology=truth.get("global_terminology", []),
                chapter_no=chapter_no,
                body=draft.body,
            )
        )
    )

    rewrite_count = 0
    while _critical_issues(audit) and rewrite_count < 2:
        rewrite_count += 1
        client.step = f"重写-第{chapter_no}章"
        draft = parse_draft(
            client.generate_json(
                build_rewrite_prompt(
                    base,
                    previous_body=draft.body,
                    audit_report=json.dumps(audit.model_dump(), ensure_ascii=False),
                )
            )
        )
        # 重写后同样控字数
        max_words = int(ch.suggested_words * 1.1)
        if count_words(draft.body) > max_words:
            client.step = f"压缩-第{chapter_no}章"
            draft = parse_draft(
                client.generate_json(
                    build_compress_prompt(
                        base,
                        previous_body=draft.body,
                        previous_words=count_words(draft.body),
                        max_words=max_words,
                        suggested_words=ch.suggested_words,
                    )
                )
            )
            if count_words(draft.body) > max_words:
                draft.body = truncate_at_last_sentence(draft.body, max_words)
                truncated = True
        client.step = f"审计-第{chapter_no}章"
        audit = parse_audit(
            client.generate_json(
                build_audit_prompt(
                    truth_data=truth.get("validated_data", {}),
                    terminology=truth.get("global_terminology", []),
                    chapter_no=chapter_no,
                    body=draft.body,
                )
            )
        )

    return WriteOutcome(
        body=draft.body,
        summary=draft.summary,
        missing=draft.missing,
        user_notice=draft.user_notice,
        audit=audit,
        rewrite_count=rewrite_count,
        truncated=truncated,
        retrieved=[seg.split("\n", 1)[0].replace("【来源：", "").replace("】", "") for seg in context],
    )


def _save_chapter(db: Session, ch: Chapter, outcome: WriteOutcome, status: str) -> None:
    ch.body = outcome.body
    ch.original_body = outcome.body
    ch.status = status
    ch.audit = json.dumps(outcome.audit.model_dump(), ensure_ascii=False)
    ch.rewrite_count = outcome.rewrite_count
    ch.truncated = outcome.truncated
    ch.retrieved = json.dumps(outcome.retrieved, ensure_ascii=False)
    ch.missing = json.dumps(outcome.missing, ensure_ascii=False)
    ch.summary = outcome.summary
    ch.user_notice = outcome.user_notice if outcome.user_notice and outcome.user_notice.strip() else None


def run_writing_job(report_id: int) -> None:
    """后台写全文：提炼 truth_base → 逐章写。进程重启后从「从第 N 章继续」恢复。"""
    db = SessionLocal()
    try:
        report = db.get(Report, report_id)
        if report is None:
            return
        client = ModelClient()

        # 1. 提炼关键事实（每份报告只提炼一次；已有则沿用）
        report.writing_status = "提炼中"
        db.commit()
        if not report.truth_base:
            report.truth_base = json.dumps(extract_truth_base(db, report, client), ensure_ascii=False)
            db.commit()
        truth = json.loads(report.truth_base)

        chapters = db.scalars(
            select(Chapter).where(Chapter.report_id == report_id).order_by(Chapter.chapter_id)
        ).all()
        total = len(chapters)

        # 从已完成章节重建记忆（支持「从第 N 章继续」：已定稿章节不重写）
        summaries: list[dict] = []
        last_ending = ""
        notices: list[str] = []
        for ch in chapters:
            if ch.status in ("通过", "待人工") and ch.body:
                if ch.summary:
                    summaries.append({"chapter_id": ch.chapter_id, "summary": ch.summary})
                last_ending = last_sentence(ch.body)
                if ch.user_notice:
                    notices.append(ch.user_notice)

        report.status = "写作中"
        report.writing_status = "写作中"
        db.commit()

        for idx, ch in enumerate(chapters, start=1):
            if ch.status in ("通过", "待人工") and ch.body:
                continue  # 已定稿，不重写
            report.current_chapter = idx
            report.current_substep = "检索中"
            ch.status = "写作中"
            db.commit()

            outcome = write_chapter(
                client,
                db=db,
                report=report,
                ch=ch,
                chapter_no=idx,
                total=total,
                truth=truth,
                summaries=summaries,
                last_ending=last_ending,
            )

            status = "待人工" if _critical_issues(outcome.audit) else "通过"
            _save_chapter(db, ch, outcome, status)
            # 只有定稿版本写进记忆（通过 或 重写 2 次放弃的待人工 都算定稿）
            summaries.append({"chapter_id": idx, "summary": outcome.summary})
            last_ending = last_sentence(outcome.body)
            if outcome.user_notice and outcome.user_notice.strip():
                notices.append(outcome.user_notice.strip())
            db.commit()

        # 去重后的冲突提示，全文结束统一展示
        deduped: list[str] = []
        seen: set[str] = set()
        for n in notices:
            if n not in seen:
                seen.add(n)
                deduped.append(n)
        report.user_notices = json.dumps(deduped, ensure_ascii=False)
        report.writing_status = "完成"
        report.current_substep = None
        report.write_error = None
        db.commit()
        log.event("writing_done", report_id=report_id, chapters=total)
    except ModelError as exc:
        report.write_error = str(exc)
        report.writing_status = "失败"
        report.current_substep = None
        db.commit()
        log.event("writing_failed", report_id=report_id, error=type(exc).__name__)
    except Exception as exc:  # 兜底：任何异常都落库，不泄漏堆栈
        report.write_error = type(exc).__name__
        report.writing_status = "失败"
        report.current_substep = None
        db.commit()
        log.event("writing_failed", report_id=report_id, error=type(exc).__name__)
    finally:
        db.close()
