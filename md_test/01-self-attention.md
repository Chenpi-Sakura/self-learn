# 自注意力机制详解

## 什么是自注意力

自注意力（Self-Attention）是 Transformer 架构的核心机制，它让序列中**每一个位置**都能直接看到序列中所有其他位置，并根据相关性分配不同的注意力权重。给定输入序列 $\mathbf{X} \in \mathbb{R}^{n \times d}$，自注意力通过三个可学习矩阵 $\mathbf{W}_Q$、$\mathbf{W}_K$、$\mathbf{W}_V$ 投影得到 Query、Key、Value 三个向量：

$$\mathbf{Q} = \mathbf{X} \mathbf{W}_Q,\quad \mathbf{K} = \mathbf{X} \mathbf{W}_K,\quad \mathbf{V} = \mathbf{X} \mathbf{W}_V$$

## 注意力分数计算

第 $i$ 个位置对第 $j$ 个位置的注意力分数计算方式为 Query 与 Key 的内积，并通过 $\sqrt{d_k}$ 缩放，再做 softmax：

$$\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{softmax}\!\left(\frac{\mathbf{Q} \mathbf{K}^\top}{\sqrt{d_k}}\right) \mathbf{V}$$

缩放因子 $\sqrt{d_k}$ 防止内积过大造成梯度消失。直观上，这个机制让"我"（Query）去找所有"关键词"（Key），权重最高的 Key 对应的 Value 给出最相关的信息。

## 因果掩码

在自回归语言模型中，**第 $i$ 个位置只能看到 $\le i$ 的位置**，因此需要一个上三角掩码矩阵把未来位置的注意力分数设为 $-\infty$。这一约束让 GPT 系列模型在生成时保持因果性。

## 复杂度

自注意力的时间和空间复杂度都是 $\mathcal{O}(n^2)$，与序列长度平方成正比。这是它与 RNN 系列（$\mathcal{O}(n)$）的最大区别，也因此催生了 FlashAttention、Linear Attention、Longformer 等优化方向。
