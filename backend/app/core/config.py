"""应用配置：只从环境变量读取，不硬编码敏感信息。

真实 Key 只在 backend/.env 里填，由 python-dotenv 加载。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# backend/.env 优先于系统环境变量
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(_BACKEND_DIR / ".env")


@dataclass
class Settings:
    model_api_key: str = field(default_factory=lambda: os.getenv("MODEL_API_KEY", ""))
    model_base_url: str = field(default_factory=lambda: os.getenv("MODEL_BASE_URL", "https://api.deepseek.com"))
    model_name: str = field(default_factory=lambda: os.getenv("MODEL_NAME", "deepseek-chat"))
    model_timeout: float = field(default_factory=lambda: float(os.getenv("MODEL_TIMEOUT", "120")))

    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", str(_BACKEND_DIR / ".." / "data"))).resolve()
    )

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.data_dir / 'app.db'}"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()
