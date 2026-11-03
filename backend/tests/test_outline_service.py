"""大纲生成与校验的测试（用假模型客户端，不联网）。"""
from __future__ import annotations

import pytest

from app.services import outline_service as os_
from app.services.outline_service import Chapter, RawChapter


def _chapters(n: int, words: int = 1000) -> list[dict]:
    return [
        {
            "chapter_id": i + 1,
            "title": f"第{i + 1}章",
            "key_points": ["论点1", "论点2"],
            "data_needed": ["总投资"],
            "suggested_words": words,
        }
        for i in range(n)
    ]


class FakeClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.calls = 0

    def generate_json(self, prompt: str) -> dict:
        idx = min(self.calls, len(self.responses) - 1)
        self.calls += 1
        return self.responses[idx]


def test_normalize_renumbers():
    raw = [
        RawChapter(chapter_id=7, title="甲", key_points=[], data_needed=[], suggested_words=100),
        RawChapter(chapter_id=99, title="乙", key_points=[], data_needed=[], suggested_words=200),
    ]
    out = os_._normalize(raw)
    assert [c.chapter_id for c in out] == [1, 2]
    assert [c.title for c in out] == ["甲", "乙"]


def test_adjust_words_sums_to_target():
    chapters = [Chapter(1, "a", [], [], 1000), Chapter(2, "b", [], [], 3000)]
    out = os_._adjust_words(chapters, 8000)
    assert sum(c.suggested_words for c in out) == 8000


def test_generate_outline_within_range():
    client = FakeClient([{"full_outline": _chapters(10, 1200)}])
    result = os_.generate_outline(client, title="t", target_words=12000, user_requirements=None)
    assert result.chapter_count == 10
    assert result.notice is None
    assert result.total_words == 12000
    assert client.calls == 1


def test_generate_outline_out_of_range_regenerates():
    client = FakeClient([{"full_outline": _chapters(3, 1200)}, {"full_outline": _chapters(9, 1200)}])
    result = os_.generate_outline(client, title="t", target_words=12000, user_requirements=None)
    assert result.chapter_count == 9
    assert result.regenerated is True
    assert client.calls == 2


def test_generate_outline_still_out_of_range_returns_notice():
    client = FakeClient([{"full_outline": _chapters(3, 1000)}, {"full_outline": _chapters(3, 1000)}])
    result = os_.generate_outline(client, title="t", target_words=12000, user_requirements=None)
    assert result.chapter_count == 3
    assert result.notice is not None
    assert client.calls == 2


def test_generate_outline_invalid_structure_raises():
    client = FakeClient([{"wrong_key": []}])
    with pytest.raises(ValueError):
        os_.generate_outline(client, title="t", target_words=12000, user_requirements=None)
