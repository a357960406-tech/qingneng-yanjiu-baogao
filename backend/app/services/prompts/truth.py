"""关键事实提炼（truth_base）提示词与固定字段。

提示词来自 PRD V2.2 第四节「关键事实提炼」；11 个固定字段按下表。
"""
from __future__ import annotations

# 字段名 -> 含义（含义同时用作检索词）
FIELDS: dict[str, str] = {
    "total_investment": "总投资及构成（建设投资、建设期利息、流动资金）",
    "capital_ratio": "资本金比例和金额、贷款安排",
    "technology_route": "制氢技术路线、电源",
    "electrolyzer_config": "电解槽台数和单台规模、合计制氢规模、年产氢量",
    "dc_power_consumption": "直流电耗",
    "pressure_level": "加氢站加注压力等级、站内储氢压力（电解槽出口压力不算）",
    "project_scope": "站点构成、各站加注能力、氢气运输方式",
    "site_area": "各站占地面积",
    "construction_period": "建设期、开工和投运时间",
    "hydrogen_cost": "制氢成本及对应电价",
    "financial": "内部收益率、投资回收期",
}


def build_truth_prompt(*, title: str, context: str) -> str:
    fields_lines = "\n".join(f"- {name}：{meaning}" for name, meaning in FIELDS.items())
    return f"""# Role
你是一名氢能项目可研报告的数据核对员，负责从项目资料里找出本项目的关键事实。

# Inputs
报告标题：{title}
要找的字段（字段名：含义）：
{fields_lines}
项目资料（程序按字段从资料库检索，每段开头标了【来源：文件名】）：
{context}

# Action Path
1. 逐个字段，在项目资料里找描述本项目的句子。
2. 同一字段找到几个不同的数，按取数规则选一个。
3. 找不到的字段填 null。

# 取数规则（冲突时听前面的）
- 立项批复、合同等正式文件 > 参数表、报价单 > 会议纪要。
- 会上已明确作废或更正的数不取；远期预留、比选方案不取，只取一期方案。
- 只取本项目的数。政策规划、行业统计、其他项目的数不取。

# Output
只输出 JSON：
{{
  "validated_data": {{"total_investment": "资料原文里的值", "dc_power_consumption": null}},
  "sources": {{"total_investment": "文件名"}},
  "global_terminology": ["标准写法"]
}}

# Constraints
- validated_data 只用给定的字段名，不加、不删、不改名，每个字段都要出现。
- 值照资料原文的数字和单位写，不换算、不推算、不用常识补。
- sources 写每个有值字段出自哪份文件。
- global_terminology 列资料里本项目设备、站点、工艺的标准写法，10 个以内。
- 禁止输出任何 JSON 之外的文字。"""
