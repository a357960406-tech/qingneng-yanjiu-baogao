#!/usr/bin/env bash
# 重启恢复检查钩子（verify.sh 调用，契约见通用手册第十节）。
# 支持子命令：start / write <标记> / read <ID> / stop
# 临时数据放 $RESTART_CHECK_DIR；不调真实模型；不碰真实数据。
set -u
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$SCRIPT_DIR/../backend"
PORT="${RESTART_CHECK_PORT:-8011}"
BASE="http://127.0.0.1:${PORT}"
LOG="$RESTART_CHECK_DIR/server.log"
PY="$BACKEND/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

port_busy() { lsof -i ":$PORT" -sTCP:LISTEN >/dev/null 2>&1; }

case "${1:-}" in
  start)
    [ -n "${RESTART_CHECK_DIR:-}" ] || { echo "缺 RESTART_CHECK_DIR" >&2; exit 1; }
    if port_busy; then echo "端口 $PORT 被占用，不杀别人的进程" >&2; exit 1; fi
    mkdir -p "$RESTART_CHECK_DIR/data"
    (
      cd "$BACKEND" || exit 1
      DATA_DIR="$RESTART_CHECK_DIR/data" MODEL_API_KEY="" \
        nohup "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" > "$LOG" 2>&1 &
    )
    # 等待端口可响应
    for _ in $(seq 1 60); do
      if curl -sf "$BASE/api/v1/health" >/dev/null 2>&1; then break; fi
      sleep 0.5
    done
    curl -sf "$BASE/api/v1/health" >/dev/null 2>&1 || { echo "服务未能在端口 $PORT 响应" >&2; exit 1; }
    # 最后一行只打印 PID
    lsof -ti ":$PORT" -sTCP:LISTEN | head -1
    ;;

  write)
    MARK="${2:-}"
    [ -n "$MARK" ] || { echo "缺标记" >&2; exit 1; }
    RESP="$(curl -sf -X POST "$BASE/api/v1/reports" -H 'Content-Type: application/json' \
      -d "{\"title\":\"${MARK}\",\"target_words\":12000}")" || { echo "写入失败" >&2; exit 1; }
    printf '%s' "$RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin)["id"])'
    ;;

  read)
    ID="${2:-}"
    [ -n "$ID" ] || { echo "缺 ID" >&2; exit 1; }
    RESP="$(curl -sf "$BASE/api/v1/reports/$ID")" || { echo "读取失败" >&2; exit 1; }
    printf '%s' "$RESP" | "$PY" -c 'import sys,json; print(json.load(sys.stdin)["title"])'
    ;;

  stop)
    PID="$(lsof -ti ":$PORT" -sTCP:LISTEN 2>/dev/null | head -1)"
    [ -n "$PID" ] && kill "$PID" 2>/dev/null
    echo ok
    ;;

  *) echo "用法：$0 start|write <标记>|read <ID>|stop" >&2; exit 2 ;;
esac
