"""大纲生成与程序校验。

PRD V2.2 第四节「大纲生成」程序校验：
- chapter_id 按顺序从 1 重新编号；
- suggested_words 加总不等于目标字数时按比例调平并记日志提醒；
- 章数不在 8–13 之间自动重新生成一次，仍不对照样返回并提示手动增删。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field, ValidationError

from app.core.logging import log
from app.services.model_client import ModelClient
from app.services.prompts.outline import build_outline_prompt

MIN_CHAPTERS = 8
MAX_CHAPTERS = 13


class RawChapter(BaseModel):
    chapter_id: int
    title: str = Field(min_length=1, max_length=255)
    key_points: list[str] = Field(default_factory=list)
    data_needed: list[str] = Field(default_factory=list)
    suggested_words: int = Field(gt=0)


class RawOutline(BaseModel):
    full_outline: list[RawChapter]


@dataclass
class Chapter:
    chapter_id: int
    title: str
    key_points: list[str]
    data_needed: list[str]
    suggested_words: int


@dataclass
class OutlineResult:
    chapters: list[Chapter]
    notice: str | None = None
    total_words: int = 0
    regenerated: bool = False
    parse_ok_first_try: bool = True
    attempts: int = 1

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)


def _parse(data: dict) -> list[RawChapter]:
    try:
        parsed = RawOutline.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"模型输出结构不合法：{exc.errors()[0]}") from exc
    chapters = parsed.full_outline
    if not chapters:
        raise ValueError("模型输出章节为空")
    return chapters


def _normalize(chapters: list[RawChapter]) -> list[Chapter]:
    """重新编号 1..n，清洗空白。"""
    out: list[Chapter] = []
    for i, ch in enumerate(chapters, start=1):
        out.append(
            Chapter(
                chapter_id=i,
                title=ch.title.strip(),
                key_points=[p.strip() for p in ch.key_points if p and p.strip()],
                data_needed=[d.strip() for d in ch.data_needed if d and d.strip()],
                suggested_words=max(1, ch.suggested_words),
            )
        )
    return out


def _adjust_words(chapters: list[Chapter], target: int) -> list[Chapter]:
    """各章字数加总不等于目标时按比例调平。"""
    total = sum(c.suggested_words for c in chapters)
    if total == target or total <= 0:
        return chapters
    log.event("outline_words_adjust", total=total, target=target)
    scaled: list[int] = []
    for c in chapters:
        scaled.append(max(1, round(c.suggested_words * target / total)))
    diff = target - sum(scaled)
    # 差额补到最后一章
    scaled[-1] += diff
    if scaled[-1] < 1:
        scaled[-1] = 1
    for c, w in zip(chapters, scaled):
        c.suggested_words = w
    return chapters


def generate_outline(
    client: ModelClient,
    *,
    title: str,
    target_words: int,
    user_requirements: str | None,
) -> OutlineResult:
    """调用模型生成大纲，含章数重试一次与字数调平。"""
    prompt = build_outline_prompt(
        title=title,
        target_words=target_words,
        user_requirements=user_requirements,
    )
    data = client.generate_json(prompt)
    chapters = _normalize(_parse(data))

    regenerated = False
    if not (MIN_CHAPTERS <= len(chapters) <= MAX_CHAPTERS):
        regenerated = True
        data = client.generate_json(prompt)
        chapters = _normalize(_parse(data))

    chapters = _adjust_words(chapters, target_words)
    notice = None
    if not (MIN_CHAPTERS <= len(chapters) <= MAX_CHAPTERS):
        notice = f"章数不在 8–13（当前 {len(chapters)} 章），请手动增删"

    return OutlineResult(
        chapters=chapters,
        notice=notice,
        total_words=sum(c.suggested_words for c in chapters),
        regenerated=regenerated,
        attempts=2 if regenerated else 1,
    )
