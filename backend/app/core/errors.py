"""统一错误结构：{"error": {"code", "message"}}，不泄露堆栈。"""
from __future__ import annotations


class AppError(RuntimeError):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}
