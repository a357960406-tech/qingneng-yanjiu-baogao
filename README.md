# 氢能研究报告

把氢能项目资料（PDF / Word / Markdown / TXT）写成 2 万字以内、关键数字前后一致的可研报告初稿。

## 目录
- `backend/`：Python 后端（FastAPI + SQLite），资料管理、大纲生成、写全文、审计。
- `frontend/`：Next.js 前端。
- `scripts/`：真实模型冒烟脚本、重启自检脚本。

## 启动方法

```bash
# 后端（http://127.0.0.1:8000）
cd backend
uv venv --python 3.12 .venv        # 首次
uv pip install --python .venv/bin/python -r requirements.txt   # 首次
cp .env.example .env               # 首次；然后填 MODEL_API_KEY
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端（http://127.0.0.1:3000）
cd frontend
npm install                        # 首次
npm run dev
```

浏览器打开 http://127.0.0.1:3000（前端把 `/api` 代理到后端 8000）。

## 验证方法

```bash
# 后端 mock 测试
cd backend && .venv/bin/python -m pytest -q

# 前端检查
cd frontend && npm run lint && npm run typecheck && npm test && npm run build

# 真实模型冒烟（需 backend/.env 已填 MODEL_API_KEY）
backend/.venv/bin/python scripts/smoke.py 阶段3-1
```

## 数据与密钥
- 本地数据（SQLite 库、上传文件）在 `data/`，已被 `.gitignore` 忽略，不进仓库。
- 密钥只填在 `backend/.env`，已被 `.gitignore` 忽略，不进仓库；模板见 `backend/.env.example`。
