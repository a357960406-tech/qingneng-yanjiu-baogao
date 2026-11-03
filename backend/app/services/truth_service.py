"""关键事实提炼（truth_base）。

PRD V2.2：开始写全文时按 11 个固定字段从资料库提炼一次，程序存下后不再改；
页面和导出文件里不出现 truth_base；多出的字段丢、缺的补 null、非字符串按 null、
有值没来源记「未标注」。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.services.model_client import ModelClient
from app.services.prompts.truth import FIELDS, build_truth_prompt
from app.services.retrieval import retrieve_chunks


def normalize_truth(raw: dict) -> dict:
    """按 11 个固定字段规整模型输出。返回 {validated_data, sources, global_terminology}。"""
    data = raw.get("validated_data") if isinstance(raw, dict) else None
    sources = raw.get("sources") if isinstance(raw, dict) else None
    if not isinstance(data, dict):
        data = {}
    if not isinstance(sources, dict):
        sources = {}

    validated: dict[str, str | None] = {}
    srcs: dict[str, str] = {}
    for name in FIELDS:
        value = data.get(name)
        if not isinstance(value, str) or not value.strip():
            validated[name] = None
        else:
            validated[name] = value.strip()
            s = sources.get(name)
            srcs[name] = s if isinstance(s, str) and s.strip() else "未标注"

    terminology = raw.get("global_terminology") if isinstance(raw, dict) else None
    if not isinstance(terminology, list):
        terminology = []
    terms = [t.strip() for t in terminology if isinstance(t, str) and t.strip()][:10]

    return {
        "validated_data": validated,
        "sources": srcs,
        "global_terminology": terms,
    }


def extract_truth_base(db: Session, report, client: ModelClient) -> dict:
    """按字段从资料库各检索 3 段、去重后提炼一次，返回规整后的 truth_base。"""
    context_parts: list[str] = []
    seen: set[str] = set()
    for meaning in FIELDS.values():
        for seg in retrieve_chunks(db, meaning, k=3):
            # 去重：按整段文本去重
            if seg not in seen:
                seen.add(seg)
                context_parts.append(seg)
    context = "\n\n".join(context_parts) or "（资料库为空）"
    client.step = "关键事实提炼"
    raw = client.generate_json(build_truth_prompt(title=report.title, context=context))
    return normalize_truth(raw)
