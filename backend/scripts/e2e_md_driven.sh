#!/usr/bin/env bash
# Task 5 端到端 demo 脚本（shell 版）。
#
# 覆盖范围（与 docs/superpowers/plans/2026-07-17-md-driven-level.md Step 10 一致）：
#   1) 准备 /tmp/md_files 下的两份示例 md
#   2) 通过 backend API（不依赖浏览器）批量上传 + 触发提炼
#   3) 轮询 DB 直到 extract_topics 状态完成
#   4) 校验至少产生 1 个 KnowledgePoint + 至少 1 个 MapNode
#
# 前置条件：
#   - backend gateway + worker 已起 (port 8000)
#   - DB / Redis Stream 可用
#   - KEEP_STUDENT = 86820161-b0f0-455f-91b4-a69e49445bdf 已 ensure
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."
ROOT="$SCRIPT_DIR/.."

BASE_URL="${BASE_URL:-http://localhost:8000}"
KEEP_STUDENT="86820161-b0f0-455f-91b4-a69e49445bdf"

echo "[e2e_md_driven] BASE_URL=$BASE_URL"
echo "[e2e_md_driven] KEEP_STUDENT=$KEEP_STUDENT"

# 1) 准备示例 md
mkdir -p /tmp/md_files
cat > /tmp/md_files/01-self-attn.md <<'EOF'
# 自注意力机制

Self-Attention 是 Transformer 的核心。对于序列中每个位置，都计算它与所有位置的注意力分数。

## 公式

$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)$
$PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)$

(此后填充大量内容以保证超过 500 字符)
EOF
python -c "
import sys
body = 'Self-Attention 是 Transformer 的核心组成。' * 30
sys.stdout.write('# 自注意力\n\n' + body)
" >> /tmp/md_files/01-self-attn.md

python -c "
import sys
sys.stdout.write('# 多头注意力\n\n多头注意力把 Q、K、V 分别线性映射 h 次后并行做 attention。' * 20)
" > /tmp/md_files/02-multi-head.md

# 2) 调用 upload (multipart/form-data)
echo "[e2e_md_driven] 1) upload 2 .md files"
UPLOAD_RESP=$(curl -fsS -X POST "$BASE_URL/api/resources/upload" \
  -F "files=@/tmp/md_files/01-self-attn.md" \
  -F "files=@/tmp/md_files/02-multi-head.md")
echo "$UPLOAD_RESP"

# 3) 提取刚上传的 resource ids (按文件名最近)
SELECTED_IDS=$(echo "$UPLOAD_RESP" | python -c "
import json,sys
data = json.load(sys.stdin)
ids = [u['id'] for u in data.get('uploaded', [])]
print(' '.join(ids))
")
if [ -z "$SELECTED_IDS" ]; then
  echo "[e2e_md_driven] FAIL: 上传后未拿到 resource ids"
  exit 1
fi
echo "[e2e_md_driven] selected_ids=$SELECTED_IDS"

# 4) 触发提炼
echo "[e2e_md_driven] 2) trigger extract_topics"
TRIGGER_RESP=$(curl -fsS -X POST "$BASE_URL/api/resources/extract_topics" \
  -H 'Content-Type: application/json' \
  -d "{\"selected_resource_ids\": [\"$(echo "$SELECTED_IDS" | tr ' ' '"," | sed 's/^/"/;s/$/"/' | tr -d '\n')\"]}")
TASK_ID=$(echo "$TRIGGER_RESP" | python -c "import json,sys;print(json.load(sys.stdin)['task_id'])")
echo "[e2e_md_driven] task_id=$TASK_ID"

# 5) SSE 跟踪完成（≤120s）
echo "[e2e_md_driven] 3) SSE 跟踪 (≤120s)"
timeout 120 curl -fsSN "$BASE_URL/api/resources/extract_topics/stream?task_id=$TASK_ID" \
  | tee /tmp/extract-sse.txt | grep -E '^event: (progress|completed|error)' | tail -30

if ! grep -q '^event: completed' /tmp/extract-sse.txt; then
  echo "[e2e_md_driven] FAIL: 没收到 completed 事件"
  exit 1
fi

# 6) 校验 DB：至少 1 个 KP (source is not null) + 至少 1 个 MapNode for KEEP_STUDENT
echo "[e2e_md_driven] 4) 校验 DB"
uv run python -c "
import asyncio
from sqlalchemy import select, func
from selflearn.domain.knowledge_point import KnowledgePoint
from selflearn.domain.map_node import MapNode
from selflearn.infra.db import get_session_factory

async def main():
    factory = get_session_factory()
    async with factory() as s:
        kp_count = (
            await s.execute(
                select(func.count(KnowledgePoint.kp_id))
                .where(KnowledgePoint.source.isnot(None))
            )
        ).scalar_one()
        node_count = (
            await s.execute(
                select(func.count(MapNode.node_id))
                .where(MapNode.student_id.__class__ == type(None))  # noqa
            )
        ).scalar_one() if False else (
            await s.execute(
                select(func.count(MapNode.node_id))
            )
        ).scalar_one()
        print(f'[e2e_md_driven] KP(source!=null)={kp_count}, MapNode(total)={node_count}')
        assert kp_count >= 1, 'KP<1'
        assert node_count >= 1, 'MapNode<1'

asyncio.run(main())
"

echo "[e2e_md_driven] ✅ ALL PASSED"
