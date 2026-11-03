"""内容生成（写章 / 重写 / 压缩）提示词。

提示词来自 PRD V2.2 第四节「内容生成」。
"""
from __future__ import annotations

import json


def build_content_prompt(
    *,
    title: str,
    user_requirements: str | None,
    chapter_no: int,
    total: int,
    chapter: str,
    max_words: int,
    truth_data: dict,
    terminology: list[str],
    chapter_summaries: list[dict],
    last_ending: str,
    context: str,
) -> str:
    extra = user_requirements.strip() if user_requirements else "（无）"
    summaries = "\n".join(
        f"第 {s['chapter_id']} 章：{s['summary']}" for s in chapter_summaries
    ) or "（暂无）"
    return f"""# Role
你是一名资深的氢能项目撰稿专家，负责撰写可行性研究报告的一章。

# Inputs
报告标题：{title}
文档风格：正式
用户额外要求：{extra}
本章任务（第 {chapter_no} / {total} 章）：{chapter}
本章字数上限：{max_words}
全局事实（truth_base）：{json.dumps(truth_data, ensure_ascii=False)}
标准术语：{json.dumps(terminology, ensure_ascii=False)}
前面各章摘要：
{summaries}
上一章最后一句：{last_ending or "（无）"}
本章参考资料（程序从资料库检索，每段开头标了【来源：文件名】）：
{context}

# Action Path
1. 读本章任务，明确必须写到的关键论点和数据。
2. 本章数据需要用到的数，先在全局事实里找；全局事实里没有，再从参考资料里找。
3. 如果"上一章最后一句"不为空，第一段要自然承接它。
4. 按建议字数和文档风格写正文，不超过字数上限。

# 数据优先级（冲突时听前面的）
全局事实 > 前面各章摘要 > 参考资料。

# Output
只输出 JSON：
{{
  "body": "本章正文，不含摘要和提示",
  "summary": "本章摘要，100 字以内，写清本章用到的关键数字",
  "missing": ["标了 [待补充] 的数据名称"],
  "user_notice": "用户额外要求与全局事实冲突时写在这里，没有冲突写空字符串"
}}

# Constraints
- 事实锁死：描述本项目自身的投资、规模、压力等级、工期、技术路线时，只用全局事实里的数，不改动、不换算。
- 禁止幻觉：全局事实和参考资料里都没有的数，写成"[待补充：需要××数据]"，并记入 missing。不要自己推算。
- 冲突处理：用户额外要求与全局事实冲突时，正文照全局事实写，在 user_notice 里写"你要求的 ××× 与项目资料里的 ××× 不一致，本章按项目资料撰写"。不要在提示里出现"全局事实""truth_base"。
- 溯源：引用参考资料的句子，句末用方括号标注来源文件名。参考资料只用于政策依据、行业现状、同类项目对比，不能当作本项目的数。
- 正文不超过本章字数上限。
- 术语只用标准术语里的写法。
- 风格为"正式"时，不出现"我认为""可能""大概"。
- 禁止输出任何 JSON 之外的文字。"""


def build_rewrite_prompt(base_prompt: str, *, previous_body: str, audit_report: str) -> str:
    return f"""{base_prompt}

上一版正文：{previous_body}
审计结果：{audit_report}

# Rewrite Rules
- 逐条修改审计结果里 CRITICAL 点名的句子，改成审计给出的正确值。
- 没被点名的句子原样保留；其他数字和 [待补充] 一个字不动。
- 输出格式不变，summary 按改后的正文重写。"""


def build_compress_prompt(base_prompt: str, *, previous_body: str, previous_words: int, max_words: int, suggested_words: int) -> str:
    return f"""{base_prompt}

上一版正文：{previous_body}
上一版字数：{previous_words}，超过了本章上限 {max_words}。

# Shorten Rules
- 压缩到 {suggested_words} 字左右，不超过 {max_words} 字。
- 删重复和铺陈的句子，不加新内容。
- 所有数字、[待补充] 和句末 [文件名] 原样保留。
- 输出格式不变，summary 按改后的正文重写。"""
