"""FastAPI 入口。

提供资料上传解析、报告创建/列表、大纲生成/确认、写全文等 API。
阶段 3 起由前端（Next.js）提供界面，本服务只提供 /api/v1/* 接口。
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api import documents, reports, writing
from app.core.errors import AppError, error_body
from app.core.logging import log
from app.models.database import init_db

app = FastAPI(title="可研报告生成Agent", version="0.1.0")

app.include_router(documents.router)
app.include_router(reports.router)
app.include_router(writing.router)


@app.on_event("startup")
def _startup() -> None:
    init_db()
    log.event("app_startup")


@app.exception_handler(AppError)
async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content=error_body("validation_error", "请求参数不合法"))


@app.exception_handler(Exception)
async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    log.event("unhandled_error", error=type(exc).__name__)
    return JSONResponse(status_code=500, content=error_body("internal_error", "服务器内部错误"))


@app.get("/api/v1/health")
def health() -> dict:
    return {"ok": True}

