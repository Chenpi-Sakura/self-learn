# Transformer 训练与推理优化

## 大模型训练三件套

训练一个现代 LLM 通常需要：

1. **混合精度（AMP）**：fp16/bf16 前向反向上文，fp32 维护主权重副本。V100/A100/H100 都配 Tensor Core，bf16 是当下首选。
2. **ZeRO 数据并行**：把 optimizer state、gradient、parameter 三组分片到 N 张卡，把显存消耗降到单卡的 1/N。DeepSpeed / FSDP 都实现这一思路。
3. **梯度累积**：单卡 batch 放不下大 batch 时，把多个 micro-batch 的梯度累加后再 sync，等价于大 batch。

## 注意力优化

| 方法 | 复杂度 | 适用场景 |
|------|--------|---------|
| FlashAttention | $\mathcal{O}(n^2)$ 但常数小很多 | 训练 4K-32K |
| PagedAttention | 同上 | vLLM 推理 |
| Linear Attention | $\mathcal{O}(n)$ | 长序列但损失质量 |
| Sparse Attention | $\mathcal{O}(n \sqrt{n})$ | 长文本窗口化 |

FlashAttention 通过把 attention 中间结果写回 HBM 的次数从 $\mathcal{O}(n^2)$ 降到 $\mathcal{O}(n)$，对训练加速明显。

## 推理优化

- **KV Cache**：每个 token 复用前序 K/V。
- **Quantization**：fp16 → int8/int4，模型体积 -75%、推理延迟 -50%。
- **Speculative Decoding**：用小模型先生成 K 个候选，大模型一次 verify 全部，可加速 2-3x。
- **PagedAttention**（vLLM）：把 KV cache 按页分配，碎片 0，batch 容量 +24x。

## RLHF 三阶段

1. **SFT**：高质量对话数据监督微调。
2. **Reward Model**：人类偏好对训一个奖励模型。
3. **PPO**：用 reward 作信号做策略梯度，KL 散度约束不让模型偏离 SFT 太远。

DPO、IPO、SimPO 等新算法把三阶段合并成两阶段甚至单阶段，是 2024 后的主流方向。
