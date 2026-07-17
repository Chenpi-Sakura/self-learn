# Transformer 位置编码

## 为什么需要位置编码

自注意力是**置换不变**的——把序列打乱重排，自注意力的输出集合不变。这对于"语言"是灾难：句子"猫吃鱼"和"鱼吃猫"算出来一样的注意力分布。因此必须显式注入位置信息。

## 绝对位置编码（Sinusoidal）

原始 Transformer 用正弦/余弦给每个位置生成固定向量：

$$PE_{(pos, 2i)} = \sin\!\left(\frac{pos}{10000^{2i/d}}\right),\quad PE_{(pos, 2i+1)} = \cos\!\left(\frac{pos}{10000^{2i/d}}\right)$$

低维度变化快（捕捉短距），高维度变化慢（捕捉长距）。但生成时位置无限，没法 hardcode。

## 可学习位置编码

BERT、GPT-2 采用：把位置当作可训练 embedding 加到 token embedding 上。优点是简单，缺点是**不能外推到训练长度**。

## 相对位置编码

只关心"两个 token 距离多远"。代表 T5（bucketized bias）：用一个相对位置偏置加到注意力分数上。后续 RoPE、ALiBi 都是这个家族的延伸。

## RoPE（Rotary Position Embedding）

RoPE 通过对 Query/Key 向量应用"位置相关旋转让内积天然依赖相对距离"。数学上：

$$\mathbf{q}_i^\top \mathbf{k}_j = (\mathbf{R}(i) \mathbf{q})^\top (\mathbf{R}(j) \mathbf{k}) = \mathbf{q}^\top \mathbf{R}(i-j) \mathbf{k}$$

这让注意力分数只与 $i-j$ 有关，**天然支持长度外推**——训练 4K 上下文，推理能到 32K 甚至更长（结合 NTK-aware 缩放）。LLaMA、Qwen、ChatGLM 都用它。
