#!/usr/bin/env python3
"""真实模型冒烟脚本（按阶段跑对应链路）。

用法：cd projects/<产品名> && backend/.venv/bin/python scripts/smoke.py 阶段2-1
- 阶段2-1：生成大纲链路。
- 阶段2-2：关键事实提炼 → 写一章 → 审计（完整写作链路的一章）。
- 从 backend/.env 读 MODEL_API_KEY；无 Key 时不跑、不造记录。
- 用临时数据目录，不污染真实数据；每次真实调用追加一行到 docs/evidence/<阶段>/冒烟记录.md。
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PRODUCT = SCRIPT_DIR.parent
BACKEND = PRODUCT / "backend"
PRODUCT_NAME = PRODUCT.name

SAMPLE_TEXT = (
    "攀枝花市钒钛高新区制氢加氢一体化示范项目（一期）。"
    "项目总投资约25000万元，其中建设投资22800万元。资本金比例30%。"
    "技术路线为碱性电解水制氢，配套光伏电源。电解槽共6台，单台1000标方，合计制氢规模6000标方/小时，年产氢量约4200吨。"
    "直流电耗4.3kWh/Nm³。加氢站加注压力35MPa。项目占地约12000平方米，建设期18个月，计划2026年3月开工、2027年8月底投运。"
    "制氢成本约17元/kg，对应电价0.35元/kWh。内部收益率7.2%，投资回收期11.6年。"
)


def _load_env() -> bool:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
    return bool(os.getenv("MODEL_API_KEY", "").strip())


def _write_header(ev: Path, stage: str, model: str, now: str) -> None:
    with open(ev, "a", encoding="utf-8") as f:
        f.write("# 冒烟记录（冒烟脚本自动写入，不得手填）\n")
        f.write(f"- 产品：{PRODUCT_NAME}\n")
        f.write(f"- 阶段：{stage}\n")
        f.write(f"- 模型：DeepSeek / {model}\n")
        f.write(f"- 写入时间：{now}\n\n")
        f.write("| 时间 | 链路 | 请求 ID | 输入 token | 输出 token | 首字耗时 | 总耗时 | 结构校验 | 重试次数 | 结果 |\n")
        f.write("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n")


def _append_row(ev: Path, step: str, m, now: str, ok: bool) -> None:
    struct = "首测合规" if (m and m.parse_ok_first_try) else ("重试后合规" if ok else "失败")
    with open(ev, "a", encoding="utf-8") as f:
        f.write(
            f"| {now} | {step} | {m.request_id if m else '-'} | {m.in_tokens if m else 0} | "
            f"{m.out_tokens if m else 0} | - | {f'{m.elapsed_s}s' if m else '-'} | {struct} | "
            f"{(m.attempts - 1) if m else 0} | {'通过' if ok else '失败'} |\n"
        )


def smoke_outline(stage: str, ev: Path) -> int:
    from app.core.config import settings
    from app.models.database import SessionLocal, init_db
    from app.models.report import Report
    from app.services.model_client import ModelClient
    from app.services.outline_service import generate_outline

    init_db()
    db = SessionLocal()
    title = "攀枝花市钒钛高新区制氢加氢一体化示范项目（一期）"
    report = Report(title=title, target_words=12000, user_requirements=None)
    db.add(report)
    db.commit()
    db.refresh(report)

    client = ModelClient()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_header(ev, stage, settings.model_name, now)
    try:
        result = generate_outline(client, title=title, target_words=12000, user_requirements=None)
        ok = len(result.chapters) >= 1
        _append_row(ev, "生成大纲", client.last_metrics, now, ok)
        db.close()
        return 0 if ok else 1
    except Exception as exc:
        _append_row(ev, "生成大纲", client.last_metrics, now, False)
        print(f"冒烟失败：{type(exc).__name__}: {exc}")
        db.close()
        return 1


def smoke_writing(stage: str, ev: Path) -> int:
    import json

    from app.core.config import settings
    from app.models.database import SessionLocal, init_db
    from app.models.document import Chunk, Document
    from app.models.report import Chapter, Report
    from app.services.model_client import ModelClient
    from app.services.truth_service import extract_truth_base
    from app.services.writing_service import write_chapter

    init_db()
    db = SessionLocal()
    doc = Document(filename="样例资料.txt", stored_name="", file_type="txt", status="可用", chunk_count=1, char_count=len(SAMPLE_TEXT))
    db.add(doc)
    db.flush()
    db.add(Chunk(document_id=doc.id, chunk_index=1, text=SAMPLE_TEXT))
    report = Report(title="攀枝花市钒钛高新区制氢加氢一体化示范项目（一期）", target_words=12000, outline_confirmed=True)
    db.add(report)
    db.flush()
    db.add(
        Chapter(
            report_id=report.id, chapter_id=1, title="概述",
            key_points=json.dumps(["项目概况", "主要技术经济指标"], ensure_ascii=False),
            data_needed=json.dumps(["总投资", "制氢规模"], ensure_ascii=False),
            suggested_words=1200,
        )
    )
    db.commit()

    client = ModelClient()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _write_header(ev, stage, settings.model_name, now)
    try:
        truth = extract_truth_base(db, report, client)
        outcome = write_chapter(
            client, db=db, report=report, ch=db.query(Chapter).first(),
            chapter_no=1, total=1, truth=truth, summaries=[], last_ending="",
        )
        for m in client.call_log:
            _append_row(ev, m.step, m, now, True)
        ok = bool(outcome.body)
        db.close()
        return 0 if ok else 1
    except Exception as exc:
        if client.last_metrics:
            _append_row(ev, client.last_metrics.step, client.last_metrics, now, False)
        print(f"冒烟失败：{type(exc).__name__}: {exc}")
        db.close()
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", nargs="?", default="阶段2-1")
    args = parser.parse_args()
    stage = args.stage

    if not _load_env():
        print("无 MODEL_API_KEY：不跑冒烟、不造记录，如实记「待验」。")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="smoke-"))
    os.environ["DATA_DIR"] = str(tmp)
    sys.path.insert(0, str(BACKEND))

    ev = PRODUCT / "docs" / "evidence" / stage / "冒烟记录.md"
    ev.parent.mkdir(parents=True, exist_ok=True)

    try:
        if stage == "阶段2-1" or stage == "阶段3-1":
            rc = smoke_outline(stage, ev)
        elif stage == "阶段2-2":
            rc = smoke_writing(stage, ev)
        else:
            print(f"阶段 {stage} 暂无冒烟脚本。")
            rc = 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if rc == 0:
        print(f"冒烟通过：已写入 {ev}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
