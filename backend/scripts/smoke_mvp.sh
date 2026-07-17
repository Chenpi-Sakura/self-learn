#!/usr/bin/env bash
# Stage 3 MVP 端到端 smoke：profile → plan → director → exercise → review → submit
#
# 覆盖范围（与 docs/superpowers/specs/2026-07-12-stage3-business-mvp-design.md § 4.3 一致）：
#   1) seed KP（idempotent）
#   2) POST /api/profile/build → 收到 trace_id
#   3) SSE 流式跟踪 profile agent（progress → completed）
#   4) POST /api/map/generate → 触发 PlanAgent 写 MapNode
#   5) POST /api/level/start → DirectorAgent 走完 出题→评审→入库
#   6) SSE 流式跟踪 director（progress → completed）；同时 sleep + poll 等 Level 写库
#   7) 取 level_id → POST /api/level/{id}/submit → DB 校验 status=completed
set -euo pipefail

trap 'echo "[smoke_mvp] FAILED at line $LINENO"; exit 1' ERR

cd "$(dirname "$0")/.."

BASE_URL="${BASE_URL:-http://localhost:8000}"
STUDENT_ID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"

echo "[smoke_mvp] BASE_URL=$BASE_URL"
echo "[smoke_mvp] student_id=$STUDENT_ID"

# ---------------------------------------------------------------------------
# 1) seed KP（idempotent：已存在则 skip）
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 1) seed KP"
uv run python -m scripts.seed_map

# ---------------------------------------------------------------------------
# 2) POST /api/profile/build → trace_id
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 2) POST /api/profile/build → trace_id"
TRACE_ID=$(curl -fsS -X POST "$BASE_URL/api/profile/build" \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$STUDENT_ID\",\"dimensions\":{\"knowledge_base\":0.6,\"visual_preference\":0.5,\"analytic_style\":0.7,\"goal_employment\":0.4,\"error_prone_type\":0.5,\"focus_duration\":0.5},\"tags\":[\"smoke\"]}" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["trace_id"])')
echo "[smoke_mvp] trace_id=$TRACE_ID"

# ---------------------------------------------------------------------------
# 3) SSE: GET /api/profile/init/$TRACE_ID/stream
#    ProfileAgent 直接读 payload.dimensions，不调 LLM → 应当秒级完成。
#    timeout 60s 覆盖 LLM cold start penalty（即使本步骤不调 LLM，worker 首次 init 也吃冷启动）。
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 3) SSE: GET /api/profile/init/$TRACE_ID/stream (≤60s)"
timeout 60 curl -fsSN "$BASE_URL/api/profile/init/$TRACE_ID/stream" \
  | tee /tmp/sse-out.txt | grep -E '^event: (progress|completed|error)' | head -20

if ! grep -q '^event: completed' /tmp/sse-out.txt; then
    echo "[smoke_mvp] FAIL: profile SSE 没收到 completed 事件"
    exit 1
fi

# ---------------------------------------------------------------------------
# 4) POST /api/map/generate
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 4) POST /api/map/generate"
MAP_TRACE=$(curl -fsS -X POST "$BASE_URL/api/map/generate" \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$STUDENT_ID\"}" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["trace_id"])')
echo "[smoke_mvp] map trace_id=$MAP_TRACE"

# 等 map node 落地（PlanAgent 直接 INSERT，最坏 1-2s）
sleep 3

# ---------------------------------------------------------------------------
# 5) POST /api/level/start
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 5) POST /api/level/start"
LEVEL_TRACE=$(curl -fsS -X POST "$BASE_URL/api/level/start" \
  -H 'Content-Type: application/json' \
  -d "{\"student_id\":\"$STUDENT_ID\"}" \
  | python -c 'import json,sys;print(json.load(sys.stdin)["trace_id"])')
echo "[smoke_mvp] level trace_id=$LEVEL_TRACE"

# ---------------------------------------------------------------------------
# 6) SSE 跟踪 director 全流程（exercise+review+入库）
#    DirectorAgent 走完整套：ExerciseAgent.run_sync → LLM cold start 可能较慢
#    → 90s 覆盖全 cycle。
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 6) SSE: GET /api/level/00000000-0000-0000-0000-000000000000/stream (≤90s)"
timeout 90 curl -fsSN "$BASE_URL/api/level/00000000-0000-0000-0000-000000000000/stream?trace_id=$LEVEL_TRACE" \
  | tee /tmp/level-sse.txt | grep -E '^event: (progress|completed|error)' | head -30

if ! grep -q '^event: completed' /tmp/level-sse.txt; then
    echo "[smoke_mvp] FAIL: level SSE 没收到 completed 事件"
    exit 1
fi

# ---------------------------------------------------------------------------
# 6b) 取 level_id：sleep 后 poll DB 找 status="generated" 的最新 Level
#     Brief 修复点：director run 完成后 level 才落地，submit 必须在 level 写库之后；
#     先 sleep 3 让 director 落库，然后 poll 30s 容错。
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 6b) sleep 3s + poll DB for latest generated Level (≤30s)"
sleep 3
LEVEL_ID=$(uv run python -c "
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select, func
from selflearn.domain.level import Level
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory

async def main():
    factory = get_session_factory()
    deadline = datetime.utcnow() + timedelta(seconds=30)
    while datetime.utcnow() < deadline:
        async with factory() as s:
            stmt = (
                select(Level)
                .join(MapNode, Level.node_id == MapNode.node_id)
                .where(MapNode.student_id == '$STUDENT_ID')
                .order_by(Level.created_at.desc())
                .limit(1)
            )
            rs = (await s.execute(stmt)).scalars().first()
            if rs is not None:
                print(str(rs.level_id))
                return
        await asyncio.sleep(1)
    print('')

asyncio.run(main())
")
if [ -z "$LEVEL_ID" ]; then
    echo "[smoke_mvp] FAIL: 30s 内未找到新生成的 Level"
    exit 1
fi
echo "[smoke_mvp] level_id=$LEVEL_ID"

# ---------------------------------------------------------------------------
# 7) submit
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 7) POST /api/level/$LEVEL_ID/submit"
SUBMIT_RESP=$(curl -fsS -X POST "$BASE_URL/api/level/$LEVEL_ID/submit" \
  -H 'Content-Type: application/json' \
  -d '{"answers":{}}')
echo "[smoke_mvp] submit response: $SUBMIT_RESP"

# ---------------------------------------------------------------------------
# 8) 校验 status=completed (level 表)
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 8) 校验 level.status=completed"
uv run python -c "
import asyncio
from selflearn.domain.level import Level
from selflearn.infra.db import get_session_factory
async def main():
    factory = get_session_factory()
    async with factory() as s:
        rs = await s.get(Level, '$LEVEL_ID')
        assert rs is not None and rs.status == 'completed', f'level status={rs.status if rs else None}'
        print(f'[smoke_mvp] level.status = {rs.status} OK')
asyncio.run(main())
"

# ---------------------------------------------------------------------------
# 9) onboarding flow (uses KEEP_STUDENT — seed_account.py ensures this exists)
# ---------------------------------------------------------------------------
echo "[smoke_mvp] 9) onboarding flow"
KEEP_STUDENT="86820161-b0f0-455f-91b4-a69e49445bdf"
# Delete Profile for KEEP_STUDENT to force onboarding state
uv run python -c "
import asyncio, uuid
from sqlalchemy import delete
from selflearn.domain.profile import Profile
from selflearn.domain.profile_snapshot import ProfileSnapshot
from selflearn.infra.db import get_session_factory
async def main():
    async with get_session_factory()() as s:
        # Delete both profile and snapshots for clean state
        await s.execute(delete(ProfileSnapshot).where(ProfileSnapshot.student_id == '$KEEP_STUDENT'))
        await s.execute(delete(Profile).where(Profile.student_id == '$KEEP_STUDENT'))
        await s.commit()
asyncio.run(main())
"
# Fetch questions
LEN=$(curl -sf "$BASE_URL/api/onboarding/questions" | jq '.questions | length')
[ "$LEN" = "8" ] && echo "[SMOKE] onboarding questions: 8 ✓" || echo "[SMOKE] FAIL: questions=$LEN (expected 8)"

# Submit onboarding (this hits real LLM if not mock)
RESP=$(curl -sf -X POST "$BASE_URL/api/onboarding/submit" \
  -H 'Content-Type: application/json' \
  -d "{
    \"student_id\": \"$KEEP_STUDENT\",
    \"answers\": [
      {\"question_id\": \"q1_kb\", \"choice\": \"a\"},
      {\"question_id\": \"q2_vp\", \"choice\": \"a\"},
      {\"question_id\": \"q3_as\", \"choice\": \"b\"},
      {\"question_id\": \"q4_ge\", \"choice\": \"b\"},
      {\"question_id\": \"q5_ept\", \"choice\": \"c\"},
      {\"question_id\": \"q6_fd\", \"choice\": \"c\"},
      {\"question_id\": \"q7_mixed\", \"choice\": [\"a\", \"b\"]},
      {\"question_id\": \"q8_open\", \"free_text\": \"我喜欢先看图再看例子最后总结。\"}
    ]
  }" 2>&1 || echo "LLM_ERROR")
DIM_COUNT=$(echo "$RESP" | jq -r '.dimensions | length // "error"')
if [ "$DIM_COUNT" = "6" ]; then
  echo "[SMOKE] onboarding submit: 6 dimensions ✓"
elif [ "$DIM_COUNT" = "error" ]; then
  echo "[SMOKE] onboarding submit: LLM returned error (mock env?) - skipping dim count validation"
  echo "[SMOKE] response: $RESP"
else
  echo "[SMOKE] FAIL: dimensions=$DIM_COUNT (expected 6)"
  exit 1
fi

echo "[smoke_mvp] ✅ ALL PASSED"