# 第5章 事实验证与知识图谱构建

## 5.1 引言

在足球新闻知识抽取场景中，单纯依赖大模型直接输出结构化结果存在两个关键问题：其一，不同来源之间的叙述可能相互矛盾；其二，即使同一事件被多次报道，系统也需要区分“支持信息”与“冲突信息”，并持续更新事件可信度。为此，本系统在抽取层（`extractor_v1`）与图谱持久化层（`knowledge_graph`）之间引入独立的真实性验证模块（`verifier`），并将验证结果作为图谱的一等属性进行版本化管理。

本章聚焦两部分核心内容：

1. **多源真实性验证模块**：基于来源权威、事件相似性与冲突信号进行置信度建模与传播；
2. **知识图谱持久化机制**：将事件、实体、来源与验证关系写入 Neo4j，并保存置信度版本演化信息。

第一部分讨论多源事实验证如何将“抽取事实”转化为“可信事实”；第二部分讨论这些可信事实如何在图谱中进行结构化落库与版本化管理，从而支持后续检索问答阶段的稳定推理。

---

## 5.2 多源真实性验证模块

真实性验证采用四阶段流程：

1. 来源初始置信建模（Stage 1）
2. 候选事件筛选与支持/冲突检测（Stage 2）
3. 双向置信传播（Stage 3）
4. 可解释结构化输出（Stage 4）

模块输入为抽取后的事件事实对象（参与者、约束锚点、时间锚点、来源信息等），输出为包含验证结果的“已验证事件”。

### 5.2.1 来源初始置信建模

系统首先根据来源类型与来源名称估计事件先验可信度。本文将来源划分为官方、专业记者、主流媒体、一般媒体与未知来源等层级，并为不同层级分配不同权重：

- `official / official_club`：1.00
- `fabrizio_romano / romano`：0.90
- `sky_sports`：0.80
- `media`：0.55
- `blog`：0.30
- `unknown`：0.45

来源权重采用“名称线索 + 类型标签”的混合判定。例如：

- 来源名含 `official` 或类型为 `official` → 1.00
- 来源名含 `romano` → 0.90
- 来源名含 `sky sports` → 0.80
- 类型为 `media/news` → 0.55
- 未命中规则 → 0.45

对于多来源事件，初始置信度采用独立累积模型：

$$
C_0 = 1 - \prod_i (1 - w_i)
$$

其中 $w_i$ 为第 $i$ 个来源权重。该公式意味着：

- 多个中高可信来源可显著提高先验置信度；
- 即便单一来源置信有限，多源叠加仍可体现“交叉佐证”价值。

系统会同步保留来源分解结果，记录每个来源对应的类型与权重，用于后续解释、审计与人工复核。

### 5.2.2 支持/冲突关系检测

在 Stage 2 中，系统先进行候选召回，再进行关系判定。

#### （1）候选事件召回

若上游未显式提供候选历史事件，系统将自动从图中检索候选。候选召回以“参与者重叠 + 时间窗口约束”为核心：

- 参与者命中（名字交集）
- 时间窗口命中（基于事件日期/有效期/发布日期，默认 ±30 天）

返回结果映射为 verifier 可直接消费的结构（含 `participants`、`constraints`、`sources`、`temporal_anchors`、`confidence_score`）。

#### （2）同槽位判定（slot alignment）

即使候选被召回，也需通过同槽位判定：

- 事件类型一致（约束类型优先，否则看 `fact_type`）
- 参与者有重叠
- 语境相似度足够（标题/描述）
- 时间重叠度大于 0

该步骤避免将无关事件错误纳入支持/冲突计算。

#### （3）支持关系评分

支持分数采用加权相似度计算：

$$
S = 0.4 \cdot P + 0.4 \cdot A + 0.2 \cdot T
$$

其中：

- $P$：参与者重叠（Jaccard）
- $A$：动作语义相似（约束类型 + 事实类型 + 描述词汇）
- $T$：时间重叠/时间衰减分数

达到 `support_threshold`（默认 0.45）即记为支持关系，并记录：

- `participant_overlap`
- `action_similarity`
- `time_overlap`

#### （4）冲突关系评分

冲突分数融合三类冲突信号：

1. **否定冲突**（事实极性相反）
2. **数值冲突**（比分、金额等关键数值不一致）
3. **互斥语义冲突**（同一语义槽内出现互斥结果）

综合公式：

$$
K = \min(0.7N + 0.6M + 0.6U,\ 1.0)
$$

其中 $N, M, U$ 分别对应否定、数值与互斥冲突信号。若 $K$ 超过 `conflict_threshold`（默认 0.40）即记为冲突关系，并保留冲突信号明细，增强可解释性。

### 5.2.3 双向置信传播机制

在传播阶段，系统对新事件与历史事件进行联合更新，而非仅更新新事件。

#### （1）支持传播

当支持分数超过阈值时，采用双向增强：

$$
C_{new}^{+} = C_{new} + \alpha S C_{old}(1-C_{new})
$$

$$
C_{old}^{+} = C_{old} + \alpha S C_{new}(1-C_{old})
$$

其中：

- $\alpha$ 默认 0.30
- $S$ 为支持分数

该机制体现“高可信历史事实可提升新事实可信度；高可信新事实也可反向增强旧事实”。

#### （2）冲突传播

当冲突分数超过阈值时，采用“高置信抑制低置信”策略：

- 若新事件置信更高，则衰减旧事件；
- 否则衰减新事件；

衰减强度受 $\beta$（默认 0.40）与冲突分数共同控制。

#### （3）状态决策与可解释输出

传播完成后，系统执行：

- 置信度裁剪到 `[0,1]`
- 状态判定：
	- `accepted`（≥ 0.55）
	- `needs_review`（≥ 0.35 且 < 0.55）
	- `rejected`（< 0.35）

最终输出 `validation` 字段，包括：

- `version`, `validated_at`
- `initial_confidence`, `current_confidence`, `status`
- `source_breakdown`
- `relation_analysis`（candidates/supports/conflicts）
- `propagation`（alpha/beta/steps/updated_existing_events）

该结构为图谱入库与审计提供直接依据。

---

## 5.3 知识图谱持久化（knowledge_graph）

知识图谱持久化阶段负责将“已验证事实”与“验证关系”统一收敛到图数据库，使事实与可信度能够共同被检索和追踪。

### 5.3.1 图谱模式设计（Neo4j Schema）

系统在图谱初始化时创建以下唯一约束：

1. `Event.event_id`
2. `Entity.entity_id`
3. `Source.source_id`
4. `ConstraintAnchor.type`
5. `TitleAnchor.title`

该设计具有三点作用：

- 保证节点唯一性，避免重复写入；
- 支持 `MERGE` 幂等更新；
- 自动获得核心字段索引，提高查询效率。

### 5.3.2 节点与关系设计

#### （1）基础事件持久化

基础事件持久化完成事件主数据写入：

- `Event` 节点属性：
	- `event_id`
	- `title`（由 `title_anchors` 映射）
	- `description`（由 `event_description` 映射）
	- `fact_type`
	- `event_date/valid_from/valid_to`
	- `inference_time`
	- `confidence_score`
	- `created_at`

并写入四类关系：

1. `(:Event)-[:INVOLVES]->(:Entity)`
2. `(:Event)-[:REPORTED_BY]->(:Source)`
3. `(:Event)-[:CONSTRAINS]->(:ConstraintAnchor)`
4. `(:Event)-[:HAS_TITLE_ANCHOR]->(:TitleAnchor)`

实现细节：

- `entity_id` 与 `source_id` 由名称归一化生成（小写 + 空格转下划线）。
- 来源字段兼容 `name` 与历史 `source`。
- 来源类型缺失时回退 `UNKNOWN`。

#### （2）批量持久化

批量持久化采用集合展开策略写入事件主节点，并补齐实体、来源、约束与标题关系，从而兼顾吞吐性能与结构完整性。

### 5.3.3 置信度版本管理

“已验证事件”持久化是本章核心机制，承担“验证结果入库 + 版本化更新”双重任务。

#### （1）新事件版本落库

对新事件写入以下验证字段：

- `initial_confidence`
- `current_confidence`
- `confidence_score`（与当前置信同步）
- `confidence_version`
- `validation_status`
- `validated_at`

#### （2）历史事件置信更新

根据 `validation.propagation.updated_existing_events`，对受影响旧事件更新：

- `current_confidence`
- `confidence_score`
- `confidence_version`
- `validated_at`

#### （3）验证关系版本化

根据 `relation_analysis` 写入：

- `SUPPORTS` 关系：`score`, `participant_overlap`, `action_similarity`, `time_overlap`, `version`, `updated_at`
- `CONFLICTS` 关系：`score`, `negation_signal`, `numeric_signal`, `uniqueness_signal`, `version`, `updated_at`

这意味着系统不仅保存“当前值”，还通过 `version` 与时间戳记录关系演化痕迹，满足可追踪与可审计需求。

#### （4）实现有效性证据

在系统集成验证中，真实性验证与图谱持久化的一体化流程得到了完整验证：

1. 新旧冲突事件能生成 `CONFLICTS` 边；
2. 新事件 `current_confidence/initial_confidence/validation_status/confidence_version` 被正确持久化；
3. 旧事件的 `current_confidence` 会按传播结果被更新。

该测试构成了“验证-持久化一体化”机制的有效性证据。

---

## 5.4 本章小结

本章围绕“事实可信性”与“图谱可持续演化”两个目标，介绍了系统在真实性验证与图谱持久化层面的关键实现。

1. 在真实性验证方面，系统建立了来源先验、支持/冲突检测与双向传播机制，能够在多源信息中动态调整事件可信度，并输出可解释验证轨迹。
2. 在图谱持久化方面，系统将验证结果作为一等信息写入 Neo4j，不仅维护事件与实体关系，还显式记录支持/冲突关系及置信度版本。
3. 通过集成测试，验证了冲突检测、置信传播与版本化落库流程的端到端可执行性。

综上，事实验证模块与知识图谱构建模块共同构成了系统的“可信知识核心”，为后续检索增强问答（RAG）提供了高质量、可追溯、可解释的结构化知识基础。
