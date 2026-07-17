# 多头注意力机制

## 动机

单头自注意力只能在一个子空间里建模相关性；**多头注意力**让模型并行学习 $h$ 套不同的 Q/K/V 投影，每一套关注不同的语义维度（如语法、语义、远距离依赖）。最后把各头的输出拼接并线性投影回去。

## 数学形式

设 head 数为 $h$，每头维度 $d_k = d / h$：

$$\text{MultiHead}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{Concat}(\text{head}_1, \dots, \text{head}_h) \mathbf{W}_O$$

$$\text{head}_i = \text{Attention}(\mathbf{Q} \mathbf{W}_Q^{(i)}, \mathbf{K} \mathbf{W}_K^{(i)}, \mathbf{V} \mathbf{W}_V^{(i)})$$

## 直觉解释

- 一组头可能专门捕捉局部短语结构；
- 另一组可能负责长距离指代；
- 还有一组可能学到句法依存。

这就像 CNN 多通道滤波器——每个头都是一个独立的注意力"视角"，组合后表达力远超单头。

## 实现技巧

实际训练中常用 **KV Cache**：对生成阶段，每次只算新一个 token 的 Query，但复用之前所有 Key、Value。这把自回归推理的复杂度从 $\mathcal{O}(n^2 d)$ 降到 $\mathcal{O}(n d)$，是 LLM 服务能跑得起大 batch 的关键。

## 位置编码的影响

RoPE（旋转位置编码）是当前主流 LLaMA/Qwen 的选择，它把相对位置信息嵌入到 Query/Key 的内积中，让注意力分数自然依赖相对距离。这相比绝对位置编码有更好的长度外推能力。
