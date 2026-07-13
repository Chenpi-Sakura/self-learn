"""AOP 基础设施：HookBus 单例 + 无侵入装饰器。

Stage 4 观测链的进程内地基（spec § 6.3 / § 6.4）：
- `hooks.HookBus`：进程内 RingBuffer，供 T5 的 /debug/state 路由 snapshot。
- `decorators.hook` / `decorators.hook_stream`：无侵入 AOP 装饰器，T4 用来装饰
  envelope publish / progress publish / LLM chat 三个横切点。

本包只是基础设施，不 import 任何业务模块，也不预埋使用点。
"""
