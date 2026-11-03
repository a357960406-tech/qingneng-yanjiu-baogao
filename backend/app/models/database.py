"""数据库连接、建表与轻量迁移。

阶段 2-2 起 schema 有新增列。SQLite MVP 用轻量迁移：对已存在的表，
用 PRAGMA table_info 检查缺列，缺就 ALTER TABLE ADD COLUMN（带默认值），
不删已有数据。正式多环境迁移再切换到 Alembic。
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings
from app.core.logging import log


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# 轻量迁移：表 -> {列名: (SQL 类型, 默认值常量)}
_MIGRATIONS: dict[str, dict[str, tuple[str, str]]] = {
    "chapters": {
        "body": ("TEXT", "NULL"),
        "original_body": ("TEXT", "NULL"),
        "status": ("VARCHAR(32)", "'等待'"),
        "audit": ("TEXT", "NULL"),
        "rewrite_count": ("INTEGER", "0"),
        "truncated": ("BOOLEAN", "0"),
        "retrieved": ("TEXT", "NULL"),
        "missing": ("TEXT", "NULL"),
        "summary": ("TEXT", "NULL"),
        "user_notice": ("TEXT", "NULL"),
    },
    "reports": {
        "truth_base": ("TEXT", "NULL"),
        "writing_status": ("VARCHAR(32)", "'未开始'"),
        "current_chapter": ("INTEGER", "0"),
        "current_substep": ("VARCHAR(64)", "NULL"),
        "user_notices": ("TEXT", "NULL"),
        "write_error": ("VARCHAR(255)", "NULL"),
    },
}


def _migrate() -> None:
    with engine.begin() as conn:
        for table, cols in _MIGRATIONS.items():
            existing = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            }
            for col, (col_type, default) in cols.items():
                if col not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default}"))
                    log.event("migrate_add_column", table=table, column=col)


def init_db() -> None:
    import app.models.document  # noqa: F401  确保模型注册
    import app.models.report  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
