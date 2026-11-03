"""结构化运行日志。

遵守 AGENTS.md 底线第 6 条：日志不记密钥、密码、完整用户文档。
只记元信息（哪一步/第几章/第几次/模型/字数/token/耗时/文件名），
不落完整正文与资料原文。
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any


class JsonLogger:
    def __init__(self, name: str = "app") -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)

    def event(self, event: str, **fields: Any) -> None:
        payload = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "event": event, **fields}
        self._logger.info(json.dumps(payload, ensure_ascii=False, default=str))


log = JsonLogger()
