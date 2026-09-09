# 阶段 3 FakeClient 评测基线

这是一次**冻结集回归快照**，不是生产通过率，也不是上线门槛。
换 Embedding、重入库、改 Prompt 后数字会变，不要写进对外指标。

## 怎么跑

在 `python/` 目录：

```text
.\.venv\Scripts\python.exe scripts\run_eval.py --backend fake
```

- 默认且唯一后端：`FakeClient`（脚本化 `tool_use` / 终态，**零真实聊天模型 HTTP 请求**）。
- 工具观察走真实 `invoke_tool`：`retrieve_knowledge` / `calculator` / `get_current_time` / `find_indexed_file`。
- 规划器只看问题文本启发式，**不读取** `expected_actions`。
- 知识库为空时会先 `ingest_directory()` 样例 Markdown。本仓冻结集已去掉 PDF 金标。

## 本轮快照

| 项 | 值 |
|----|----|
| UTC 日期 | 2026-09-09 |
| 题量 | 29（R01–R12 / T01–T05 / H01–H04 / X01–X04 / F01–F04） |
| 后端 | FakeClient |
| 本轮通过 | 26 / 29 |
| 本轮通过率（冻结集，非生产） | 89.7% |
| 动作序列符合 | 29 / 29（100%） |
| 状态符合（含拒答等价） | 29 / 29（100%） |
| Embedding | 智谱 `embedding-3` 返回 HTTP 429 / 业务码 1113（余额不足），**fail-open 到 Chroma DefaultEmbeddingFunction（ONNX MiniLM）** |
| Rerank | 未配置 Cohere/Jina，fail-open 跳过 |
| 命令 | `python/scripts/run_eval.py --backend fake` |

详细分题表生成本机 `python/tests/eval_results.md`（已 gitignore，不入库）。

## 未通过的 3 题（检索/忠实度，不是动作规划）

1. **R09**「AlphaCore-7」：要点和金标芯片文档都命中，但 Top-5 里仍混入 `hr_kpi_q3.md`，脚注触发 `must_not_cite`。短查询 + MiniLM 降级后的精确词干扰。
2. **H01** 额定功耗 ×3：动作是 retrieve → calculator，但 MiniLM/RRF 的 Top-5 停在产品定位段，观察里抽不到 `35W`，要点 35/105 未命中。
3. **F04** 申诉天数 + 额定功耗相加：动作正确，单次 retrieve 没有同时稳定拿到 `5 个工作日` 与 `35W`，计算器拿不到 `40`。

换回 embedding-3 并重新入库后应重跑本冻结集，不要拿本表对比上线质量。

## Trace

评测与线上聊天都会写 `python/traces/{id}.json` 和 `traces/index.jsonl`（gitignore）。
侧栏 **Traces** 打开回放页；提问结束后列表顶部应出现该轮记录。
