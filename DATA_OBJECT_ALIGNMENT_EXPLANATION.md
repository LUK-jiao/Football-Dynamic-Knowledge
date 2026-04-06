# DATA OBJECT ALIGNMENT EXPLANATION

## 1) 文档定位

本文档用于说明当前仓库中数据对象对齐的**已实现状态**，不是待办计划。

当前已落地链路：

`datasource -> preprocess(分句/分块) -> extractor_v1(分解/锚点) -> verifier -> knowledge_graph`

并由 `tests/integration_test_full_pipeline.py` 中的
`test_full_pipeline_single_fetch_from_postgresql` 做端到端验证（单次取数、全流程自动流转）。

---

## 2) 统一对象契约（当前实现）

### 2.1 `ArticleDocument`（datasource 输出 / preprocess 输入）

典型字段：

- `doc_id`（规则：`news-{source_record_id}`，例如 `news-10`）
- `source_record_id`
- `url`
- `title`
- `raw_text`
- `source_name` / `source_type`
- `publish_date`
- `author`
- `crawled_at`
- `metadata`

说明：

- 由 `datasource/preprocess_adapter.py` 统一构造。
- 数据源测试场景固定读取 `id=10`，并校验 `doc_id == news-10`。

### 2.2 `PreChunkInput`（分句输出）

典型字段：

- `sentence_id`（例如 `news-10-s001`）
- `sentence_order`
- `sentence_text`

说明：

- 由 `SentenceSplitter.split_document(article)` 生成。
- 作为 semantic chunker 的输入单元。

### 2.3 `SemanticChunkDocument`（分块输出 / 事件分解输入）

典型字段：

- `doc_id`
- `block_id`（例如 `news-10-block001`）
- `block_text`
- `title`
- `source_name` / `source_type`
- `publish_date`
- `author`
- `metadata`

说明：

- 由 `SemanticChunker.chunk_document(article, prechunk_inputs)` 生成。
- 通过 `to_event_decomposition_input()` 转换成 decomposition 输入。

### 2.4 `EventUnit`（事件分解输出 / 锚点抽取输入）

典型字段：

- `event_id`（例如 `news-10-block001:e001`）
- `doc_id`
- `chunk_id`（兼容 `block_id`）
- `event_index`
- `event_description`
- `block_text`
- `source_name` / `source_type`
- `publish_date`
- `author`

说明：

- decomposition 后处理会补齐/统一 `event_id`、`doc_id`、`chunk_id`、`event_index`。
- 新链路优先 `source_name/source_type`，兼容历史 `source`。

### 2.5 `AnchoredEvent`（锚点抽取输出）

典型字段：

- `event_id`
- `title_anchors`
- `event_description`
- `participants`
- `fact_type`
- `constraints`
- `temporal_anchors`
- `sources`（优先 `name`，兼容历史 `source`）
- `inference_time`

### 2.6 `ValidatedEvent`（verifier 输出 / knowledge_graph 输入）

新增验证信息：

- `validation.current_confidence`
- `validation.relation_analysis.candidate_count/supports/conflicts`
- 版本/状态相关字段（由写入层持久化）

---

## 3) `test_full_pipeline_single_fetch_from_postgresql` 的对象流转记录

该测试是当前对象对齐的“活文档”，执行流程如下：

1. **Step 0（Datasource）**
   - 调用 `DataSourceService.fetch_documents_by_ids([10])`
   - 输出 `ArticleDocument`（仅 1 条）

2. **Step 1（Sentence Split）**
   - `splitter.split_document(article)`
   - `ArticleDocument -> List[PreChunkInput]`

3. **Step 2（Semantic Chunk）**
   - `chunker.chunk_document(article, prechunk_inputs)`
   - `List[PreChunkInput] -> List[SemanticChunkDocument]`

4. **Step 3（Event Decomposition）**
   - 对每个 `SemanticChunkDocument` 调 `to_event_decomposition_input()` + `decompose_events(...)`
   - `List[SemanticChunkDocument] -> List[EventUnit]`

5. **Step 4（Anchor Extraction）**
   - `extract_anchors(event)`
   - `List[EventUnit] -> List[AnchoredEvent]`

6. **Step 5（Truth Validation）**
   - `verifier.validate_batch(...)`
   - `List[AnchoredEvent] -> List[ValidatedEvent]`

7. **Step 6（Knowledge Graph）**
   - `writer.upsert_validated_event(item)`
   - `ValidatedEvent -> Neo4j Event/Entity/Source/Anchor nodes & relations`

测试内有逐步打印（句子、分块、事件、锚点、置信度），用于排障和契约可视化。

---

## 4) 关键可追溯 ID 规则（当前）

- `doc_id`: `news-{source_record_id}`
- `block_id/chunk_id`: `{doc_id}-block{index:03d}`（对外兼容 `chunk_id`）
- `event_id`: `{block_id}:e{index:03d}`

回溯路径：

`event_id -> block_id/chunk_id -> doc_id -> source_record_id(news.id)`

---

## 5) 与历史字段的兼容策略

- 输入侧：优先 `source_name/source_type`，兼容旧 `source`。
- 输出侧：`sources[]` 优先 `name`，保留旧 `source` 兼容读取。
- 写库侧：`Source.type` 缺失时回退 `UNKNOWN`，避免脏数据导致写入失败。

---

## 6) 当前验收状态

- [x] datasource 不再把原始表结构直接暴露给下游
- [x] `doc_id -> block/chunk_id -> event_id` 全链路可追溯
- [x] 锚点输出结构与现有消费方兼容
- [x] `AnchoredEvent/ValidatedEvent` 可回溯到 `source_record_id`
- [x] 已有端到端测试覆盖对象流转与写库校验

---

## 7) 后续维护建议（轻量）

1. 新增字段时优先放在契约对象，不直接散落在业务函数入参。
2. 保持 `test_full_pipeline_single_fetch_from_postgresql` 的详细打印，作为回归排障入口。
3. 若未来彻底移除兼容层，可分阶段下线旧 `source` 字段读取。
