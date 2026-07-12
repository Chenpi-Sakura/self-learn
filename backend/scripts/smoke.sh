#!/usr/bin/env bash
# 端到端 smoke：起 gateway + worker → curl POST → 轮询 status → 校验 reply
set -euo pipefail
cd "$(dirname "$0")/.."

cleanup() {
    docker compose down 2>/dev/null || true
}
trap cleanup EXIT

echo "[smoke] starting infrastructure..."
docker compose up -d postgres redis qdrant minio rabbitmq jaeger

echo "[smoke] waiting for services healthy..."
for i in {1..30}; do
    if docker compose ps | grep -q "(healthy)"; then sleep 1; fi
    [ "$(docker compose ps --format '{{.Health}}' | grep -c unhealthy)" = "0" ] && break
    sleep 2
done

echo "[smoke] running migrations..."
uv run alembic upgrade head

echo "[smoke] seeding demo student..."
uv run python -m scripts.seed_dev

echo "[smoke] starting gateway + worker..."
docker compose up -d --build gateway worker
sleep 5

echo "[smoke] calling POST /api/profile/init..."
RESP=$(curl -fsS -X POST http://localhost:8000/api/profile/init \
    -H "Content-Type: application/json" \
    -d '{"student_id":"00000000-0000-0000-0000-000000000001","topic":"smoke"}')
TRACE_ID=$(echo "$RESP" | python -c "import sys,json; print(json.load(sys.stdin)['trace_id'])")
echo "[smoke] trace_id=$TRACE_ID"

echo "[smoke] polling status (max 10s)..."
S=""
for i in {1..20}; do
    S=$(curl -fsS "http://localhost:8000/api/profile/init/$TRACE_ID/status" | python -c "import sys,json; print(json.load(sys.stdin)['status'])")
    echo "[smoke] status=$S"
    [ "$S" = "completed" ] && break
    [ "$S" = "failed" ] && { echo "[smoke] FAILED"; exit 1; }
    sleep 0.5
done

if [ "$S" != "completed" ]; then
    echo "[smoke] TIMEOUT after 10s"; exit 1
fi

REPLY=$(curl -fsS "http://localhost:8000/api/profile/init/$TRACE_ID/status" | python -c "import sys,json; print(json.load(sys.stdin).get('reply') or '')")
echo "[smoke] reply=$REPLY"
if ! echo "$REPLY" | grep -qi "pong"; then
    echo "[smoke] reply missing 'pong'"; exit 1
fi

echo "[smoke] SSE check..."
SSE_OUT=$(curl -fsSN "http://localhost:8000/api/profile/init/$TRACE_ID/stream" | head -5)
echo "$SSE_OUT"
if ! echo "$SSE_OUT" | grep -q "completed"; then
    echo "[smoke] SSE missing 'completed' event"; exit 1
fi

echo "[smoke] ✓ PASSED"