"""写章链路测试（C04/C05/C07/C10 的纯函数与假模型循环）。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import writing_service as ws


class ScriptedClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, prompt: str) -> dict:
        idx = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return self.responses[idx]


def _report_and_chapter():
    report = SimpleNamespace(title="测试项目", user_requirements=None)
    ch = SimpleNamespace(
        title="第一章 概述",
        key_points='["论点1"]',
        data_needed='["总投资"]',
        suggested_words=1000,
    )
    truth = {"validated_data": {"total_investment": "25000万元"}, "global_terminology": [], "sources": {}}
    return report, ch, truth


def _content(body="正常正文", summary="摘要", user_notice=""):
    return {"body": body, "summary": summary, "missing": [], "user_notice": user_notice}


def _audit(severity="WARNING", critical=False):
    if critical:
        return {
            "critical_count": 1,
            "warning_count": 0,
            "issues": [{"severity": "CRITICAL", "quote": "30000万元", "expected": "25000万元", "basis": "total_investment"}],
            "unverifiable": [],
        }
    return {"critical_count": 0, "warning_count": 1, "issues": [{"severity": "WARNING", "quote": "x", "expected": "y", "basis": "z"}], "unverifiable": []}


def _audit_ok():
    return {"critical_count": 0, "warning_count": 0, "issues": [], "unverifiable": []}


def test_count_words_ignores_whitespace():
    assert ws.count_words(" 一二 三\n四 ") == 4


def test_last_sentence_from_body():
    assert ws.last_sentence("第一句。第二句！") == "第二句"
    assert ws.last_sentence("   ") == ""


def test_truncate_at_last_sentence():
    text = "短句。" * 500
    out = ws.truncate_at_last_sentence(text, 50)
    assert ws.count_words(out) <= 50


def test_warning_only_no_rewrite(monkeypatch):
    monkeypatch.setattr(ws, "retrieve_chunks", lambda db, query, k=6: [])
    report, ch, truth = _report_and_chapter()
    client = ScriptedClient([_content(), _audit("WARNING")])
    outcome = ws.write_chapter(client, db=None, report=report, ch=ch, chapter_no=1, total=3, truth=truth, summaries=[], last_ending="")
    assert outcome.rewrite_count == 0
    assert not ws._critical_issues(outcome.audit)


def test_critical_rewrites_then_pass(monkeypatch):
    monkeypatch.setattr(ws, "retrieve_chunks", lambda db, query, k=6: [])
    report, ch, truth = _report_and_chapter()
    client = ScriptedClient([
        _content(body="总投资 30000万元"),
        _audit(critical=True),
        _content(body="总投资 25000万元"),
        _audit_ok(),
    ])
    outcome = ws.write_chapter(client, db=None, report=report, ch=ch, chapter_no=1, total=3, truth=truth, summaries=[], last_ending="")
    assert outcome.rewrite_count == 1
    assert not ws._critical_issues(outcome.audit)


def test_critical_twice_then_manual(monkeypatch):
    monkeypatch.setattr(ws, "retrieve_chunks", lambda db, query, k=6: [])
    report, ch, truth = _report_and_chapter()
    client = ScriptedClient([
        _content(body="总投资 30000万元"),
        _audit(critical=True),
        _content(body="总投资 30000万元"),
        _audit(critical=True),
        _content(body="总投资 30000万元"),
        _audit(critical=True),
    ])
    outcome = ws.write_chapter(client, db=None, report=report, ch=ch, chapter_no=1, total=3, truth=truth, summaries=[], last_ending="")
    assert outcome.rewrite_count == 2
    assert ws._critical_issues(outcome.audit)


def test_notice_dedup():
    # C08：冲突提示去重（run_writing_job 内的逻辑，这里测等价的核心）
    notices = ["冲突A", "冲突A", "冲突B"]
    deduped = list(dict.fromkeys(notices))
    assert deduped == ["冲突A", "冲突B"]
