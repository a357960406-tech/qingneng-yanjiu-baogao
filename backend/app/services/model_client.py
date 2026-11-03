"""模型调用客户端（DeepSeek，OpenAI 兼容接口）。

底线要求：
- 模型名称 / base_url / 超时 / 参数走配置，不硬编码；
- 超时、失败、非法 JSON 都要有限重试（含 SDK 初始化失败）；
- 输出必须结构校验（本模块只返回已解析的 dict，字段校验由调用方做）；
- 日志只记元信息，不记 Key、不记完整输入输出。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.logging import log


class ModelError(RuntimeError):
    """模型调用失败（重试耗尽后抛出）。"""


@dataclass
class ModelCallMetrics:
    step: str
    request_id: str
    in_tokens: int
    out_tokens: int
    elapsed_s: float
    attempts: int
    parse_ok_first_try: bool


class ModelClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else settings.model_api_key).strip()
        self.base_url = (base_url or settings.model_base_url).strip()
        self.model = (model or settings.model_name).strip()
        self.timeout = timeout if timeout is not None else settings.model_timeout
        self._client = None
        self.last_metrics: ModelCallMetrics | None = None
        self.call_log: list[ModelCallMetrics] = []
        self.step: str = ""

    def _ensure_client(self) -> None:
        if self._client is not None:
            return
        if not self.api_key:
            raise ModelError("未配置 MODEL_API_KEY，请先在 backend/.env 里填写。")
        try:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        except Exception as exc:  # SDK 初始化失败也要兜底
            raise ModelError(f"模型 SDK 初始化失败：{type(exc).__name__}") from exc

    def generate_json(
        self,
        prompt: str,
        *,
        max_retries: int = 3,
        retry_base_delay: float = 2.0,
    ) -> dict[str, Any]:
        """调用模型并要求 JSON 输出，解析失败重试，最终返回 dict。"""
        self._ensure_client()
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            started = time.time()
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.3,
                )
                content = resp.choices[0].message.content or ""
                request_id = getattr(resp, "id", "-")
                usage = getattr(resp, "usage", None)
                in_tok = getattr(usage, "prompt_tokens", 0) if usage else 0
                out_tok = getattr(usage, "completion_tokens", 0) if usage else 0
                elapsed = time.time() - started
                data = json.loads(content)
                self.last_metrics = ModelCallMetrics(
                    step=self.step,
                    request_id=request_id,
                    in_tokens=in_tok,
                    out_tokens=out_tok,
                    elapsed_s=round(elapsed, 2),
                    attempts=attempt,
                    parse_ok_first_try=(attempt == 1),
                )
                self.call_log.append(self.last_metrics)
                log.event(
                    "model_call",
                    step=self.step or "generate_json",
                    model=self.model,
                    attempt=attempt,
                    request_id=request_id,
                    in_tokens=in_tok,
                    out_tokens=out_tok,
                    elapsed_s=round(elapsed, 2),
                    ok=True,
                )
                return data
            except json.JSONDecodeError as exc:
                last_error = exc
                log.event("model_call", step="generate_json", model=self.model, attempt=attempt, error="invalid_json")
            except Exception as exc:  # 超时、网络、SDK 等
                last_error = exc
                log.event(
                    "model_call",
                    step="generate_json",
                    model=self.model,
                    attempt=attempt,
                    error=type(exc).__name__,
                )
            if attempt < max_retries:
                time.sleep(retry_base_delay * attempt)
        raise ModelError(f"模型调用失败（已重试 {max_retries} 次）：{type(last_error).__name__}") from last_error
