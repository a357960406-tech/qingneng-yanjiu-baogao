"""关键事实提炼规整逻辑测试（C09：字段固定、多删缺补、非字符串按 null、来源缺失记未标注）。"""
from __future__ import annotations

from app.services.truth_service import normalize_truth


def test_normalize_drops_extra_fills_missing():
    raw = {
        "validated_data": {"total_investment": "25000万元", "extra_field": "应被丢弃"},
        "sources": {"total_investment": "立项批复.pdf"},
        "global_terminology": ["PEM 电解槽"],
    }
    out = normalize_truth(raw)
    assert "extra_field" not in out["validated_data"]
    # 11 个固定字段都出现
    assert len(out["validated_data"]) == 11
    assert out["validated_data"]["total_investment"] == "25000万元"
    assert out["validated_data"]["financial"] is None


def test_normalize_non_string_to_null():
    raw = {"validated_data": {"total_investment": 25000, "financial": None}, "sources": {}, "global_terminology": []}
    out = normalize_truth(raw)
    assert out["validated_data"]["total_investment"] is None


def test_normalize_missing_source_marks_未标注():
    raw = {"validated_data": {"total_investment": "25000万元"}, "sources": {}, "global_terminology": []}
    out = normalize_truth(raw)
    assert out["sources"]["total_investment"] == "未标注"


def test_normalize_terminology_limit_10():
    terms = [f"术语{i}" for i in range(15)]
    out = normalize_truth({"validated_data": {}, "sources": {}, "global_terminology": terms})
    assert len(out["global_terminology"]) == 10
