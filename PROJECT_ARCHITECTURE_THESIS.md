# Football Dynamic Knowledge：论文版系统架构说明

## 1. 系统目标与研究定位

`Football_Dynamic_Knowledge` 是一个面向足球新闻场景的动态知识系统，采用 **Event-Centric Knowledge Graph + GraphRAG** 技术路线，实现从非结构化新闻到可验证、可检索、可问答知识的自动化闭环。

系统核心目标：

1. 将新闻文本转换为统一、可追溯的数据对象。
2. 基于多来源一致性与冲突信号进行事实可信度建模。
3. 将知识图谱检索与大模型生成结合，提供可解释问答输出。

主流程：

`PostgreSQL(news) -> datasource -> preprocess -> extractor_v1 -> verifier -> Neo4j -> rag`

---

## 2. 分层架构与模块职责

### 2.1 数据采集与标准化层（`datasource/`）

核心组件：

- `PostgresNewsRepository`
- `DataSourceService`
- `preprocess_adapter`

主要实现：

1. 从 `news` 表读取原始新闻（支持分页、增量、按 ID 精确读取）。
2. 对 `publish_date` 文本进行标准化（`YYYY-MM-DD` 归一化）。
3. 将数据库行对象转换为下游统一文档对象，避免下游模块直接依赖表字段。

关键接口：

- `fetch_documents_for_preprocess(...)`
- `fetch_incremental_documents(...)`
- `fetch_documents_by_ids(ids)`

---

### 2.2 文本预处理层（`preprocess/`）

核心组件：

- `SentenceSplitter`
- `SemanticChunker`
- `contracts.py`

#### 2.2.1 句子切分

`SentenceSplitter` 采用 spaCy + 规则补偿：

1. spaCy 基础分句。
2. 引号尾部切分修正（避免引号与后句粘连）。
3. 报道体引语聚合（quote aggregation）。
4. 清洗与去重（长度过滤、空白归一化、重复句去除）。

#### 2.2.2 语义分块

`SemanticChunker` 使用“**LLM连续打分 + 阈值决策**”机制：

- 分数区间：$s \in [0, 1]$
- 阈值：由 `GranularityMode` 决定（fine/medium/coarse）
- 支持结构规则（统计段、引语、时间转折）和 orphan merge

该设计兼顾语义质量、可控性和可解释性。

---

### 2.3 知识抽取层（`extractor_v1/`）

核心组件：

- `EventDecomposer`
- `AnchorExtractor`
- `OllamaBackend`

#### 2.3.1 事件分解（Event Decomposition）

输入：语义块对象（含 `block_id/chunk_id`, `text`, `source_name`, `source_type`, `publish_date` 等）

输出：`EventUnit` 列表。

实现要点：

1. 一个语义块可分解为 1~N 个事件。
2. 系统后处理统一覆盖 `event_id`（避免模型自由生成不稳定）。
3. 自动补齐 `doc_id/chunk_id/event_index` 与来源字段。

#### 2.3.2 锚点抽取（Anchor Extraction）

输入：`EventUnit`

输出：`AnchoredEvent`（扁平化结构），核心包括：

- `participants`
- `fact_type`
- `constraints`
- `temporal_anchors`
- `sources`

---

### 2.4 真值验证层（`verifier/`）

核心组件：`MultiSourceVerifier`

采用四阶段流程：

1. **来源先验**：根据来源类型/名称计算初始置信度。
2. **候选筛选与关系判定**：按参与者、时间、标题锚点等检索候选，计算 support/conflict。
3. **双向传播**：新旧事件在支持/冲突关系下更新置信度。
4. **可解释输出**：输出 `validation` 结构（候选数、supports、conflicts、传播过程）。

支持传播公式：

$$
C_{new}^{+} = C_{new} + \alpha \cdot S \cdot C_{old} \cdot (1 - C_{new})
$$

$$
C_{old}^{+} = C_{old} + \alpha \cdot S \cdot C_{new} \cdot (1 - C_{old})
$$

冲突传播使用抑制机制（由 $\beta$ 与冲突分数控制）。

---

### 2.5 图谱持久化层（`knowledge_graph/`）

核心组件：`Neo4jWriter`

功能：

1. 建立唯一约束与索引。
2. Upsert 事件与关联节点（实体、来源、约束、标题锚点）。
3. 持久化验证输出：`initial_confidence/current_confidence/version/status`。
4. 持久化关系：`SUPPORTS`、`CONFLICTS`。

---

### 2.6 检索问答层（`rag/`）

核心组件：

- `QueryAnalyzer`
- `GraphRetriever`
- `ContextBuilder`
- `GraphRAG`

执行流程：

1. 将自然语言问题解析为结构化检索条件。
2. 生成 Cypher 进行事件检索。
3. 构建上下文（去重、排序、压缩、分组）。
4. 基于上下文调用 LLM 生成答案。

---

### 2.7 服务与调度层（`api/`, `workers/`）

- API：FastAPI（路由已完成骨架，部分业务实现为 `TODO`）。
- 异步：Celery + Redis（任务接口已预留，当前为占位实现）。

---

## 3. 核心数据结构与对象契约

### 3.1 `ArticleDocument`（datasource -> preprocess）

关键字段：

- `doc_id`
- `source_record_id`
- `title`
- `raw_text`
- `source_name`, `source_type`
- `publish_date`
- `author`
- `metadata`

`doc_id` 规则：`news-{source_record_id}`

---

### 3.2 `PreChunkInput`（splitter 输出）

关键字段：

- `sentence_id`
- `sentence_order`
- `sentence_text`

---

### 3.3 `SemanticChunkDocument`（chunker 输出）

关键字段：

- `doc_id`
- `block_id`
- `block_text`
- `title`
- `source_name`, `source_type`
- `publish_date`
- `author`
- `metadata`

---

### 3.4 `EventUnit`（decomposition 输出）

关键字段：

- `event_id`
- `doc_id`
- `chunk_id/block_id`
- `event_index`
- `event_description`
- `block_text`
- `source_name`, `source_type`
- `publish_date`
- `author`

---

### 3.5 `AnchoredEvent`（anchor extraction 输出）

关键字段：

- `event_id`
- `participants`
- `fact_type`
- `constraints`
- `temporal_anchors`
- `sources`

---

### 3.6 `ValidatedEvent`（verifier 输出 / 入图库）

关键字段：

- `validation.initial_confidence`
- `validation.current_confidence`
- `validation.relation_analysis`
- `validation.propagation`

---

## 4. 可追溯ID设计

当前实现使用分层 ID 体系：

1. `doc_id = news-{source_record_id}`
2. `block_id = {doc_id}-block{index:03d}`
3. `event_id = {block_id}:e{index:03d}`

回溯路径：

`event_id -> block_id/chunk_id -> doc_id -> source_record_id(news.id)`

该机制保证：

- 全链路可追踪
- 跨模块调试可定位
- 图谱事实可回源到原始新闻记录

---

## 5. 图谱模式设计（Neo4j）

### 5.1 节点

- `Event`
- `Entity`
- `Source`
- `ConstraintAnchor`
- `TitleAnchor`

### 5.2 关系

- `(:Event)-[:INVOLVES]->(:Entity)`
- `(:Event)-[:REPORTED_BY]->(:Source)`
- `(:Event)-[:CONSTRAINS]->(:ConstraintAnchor)`
- `(:Event)-[:HAS_TITLE_ANCHOR]->(:TitleAnchor)`
- `(:Event)-[:SUPPORTS]->(:Event)`
- `(:Event)-[:CONFLICTS]->(:Event)`

### 5.3 约束

系统在初始化时创建唯一约束：

- `Event.event_id`
- `Entity.entity_id`
- `Source.source_id`
- `ConstraintAnchor.type`
- `TitleAnchor.title`

---

## 6. 关键实现策略

1. **边界适配而非全量重写**：在 datasource/preprocess/extractor 边界做契约收敛。
2. **兼容优先**：新字段优先（如 `source_name`），兼容历史字段（如 `source`）。
3. **模型输出后处理**：关键标识（尤其 `event_id`）由系统统一生成。
4. **可解释验证**：置信度、支持/冲突与传播过程显式记录。

---

## 7. 实验与验证路径

### 7.1 核心端到端测试

`tests/integration_test_full_pipeline.py::test_full_pipeline_single_fetch_from_postgresql`

验证特征：

1. 仅在开头从 PostgreSQL 获取一次数据（当前为 `id=10`）。
2. 后续不手工补充数据。
3. 全链路自动流转：

`ArticleDocument -> PreChunkInput -> SemanticChunkDocument -> EventUnit -> AnchoredEvent -> ValidatedEvent -> Neo4j`

4. 测试中输出每一步中间对象，用于契约对齐与排障。

### 7.2 验证结论维度

- 对象字段完整性
- ID 链路一致性
- 验证信息落库完整性
- 图谱写入幂等性（重复执行可清理重建）

---

## 8. 工程化实现现状

### 已完成

- 主链路对象契约统一
- truth validation 与图谱关系写入
- GraphRAG 基础检索与上下文拼接
- 端到端单次取数集成测试

### 在建/待扩展

- API 路由中的部分业务实现（当前包含 `TODO`）
- Celery 异步任务实逻辑填充
- 更系统的性能基准与大规模压测

---

## 9. 论文可用贡献点总结

1. 提出并工程化实现了足球新闻场景下的**事件中心知识抽取与验证流水线**。
2. 建立了贯穿采集、抽取、验证、入图的**统一对象契约与可追溯ID体系**。
3. 通过 `MultiSourceVerifier` 引入了可解释的**支持/冲突驱动置信传播机制**。
4. 在图谱层实现了事实、来源、约束、标题锚点与验证关系的联合持久化。
5. 构建了 GraphRAG 闭环，支持基于结构化约束的检索增强问答。
