# Verifier Guide（真实性验证模块使用指南）

本指南介绍 `verifier` 模块（`MultiSourceVerifier`）的功能与用法。

---

## 1. 模块定位

`MultiSourceVerifier` 位于知识抽取层与图谱持久化层之间，用于在事件入库前做真实性与一致性验证。

它实现了你设计中的“四阶段验证机制”：

1. **来源初始置信建模**：根据来源权威性计算事件初始置信度。
2. **图谱一致性关系检测**：检测与已有事件的支持/冲突关系。
3. **双向置信传播**：在支持/冲突关系下，更新新旧事件置信度。
4. **结构化输出**：生成可解释 `validation` 结果，供持久化层写入。

---

## 2. 主要能力

### 2.1 来源初始置信度（Stage 1）

- 单来源：$C_0 = w_i$
- 多来源：$C_0 = 1 - \prod_i (1 - w_i)$

内置权重（可覆盖）：

- official: `1.00`
- romano/fabrizio_romano: `0.90`
- sky_sports: `0.80`
- media: `0.55`
- blog: `0.30`
- unknown: `0.45`

### 2.2 支持/冲突检测（Stage 2）

候选事件筛选条件（满足任一）：

- 参与者重叠
- 时间接近/重叠
- `title_anchors` 一致

仅在同一事件槽位下做关系判定：

`(EventType, Actor, Context, TimeScope)`

- 支持分：$S = 0.4P + 0.4A + 0.2T$
  - $P$: 参与者重叠度
  - $A$: 行为语义匹配度
  - $T$: 时间重合度
- 冲突分：$F = \min(0.7N + 0.6V + 0.6U, 1.0)$
  - $N$: 否定冲突
  - $V$: 数值冲突
  - $U$: 唯一性冲突

### 2.3 双向置信传播（Stage 3）

设：

- $C_{new}$：新事件置信度
- $C_{old}$：旧事件置信度
- $\alpha,\beta$：传播系数

支持传播：

- $C'_{new}=C_{new}+\alpha S C_{old}(1-C_{new})$
- $C'_{old}=C_{old}+\alpha S C_{new}(1-C_{old})$

冲突传播（高置信压制低置信）：

- 若 $C_{new}>C_{old}$：
  - $C'_{old}=C_{old}-\beta F C_{new} C_{old}$
- 否则：
  - $C'_{new}=C_{new}-\beta F C_{old} C_{new}$

所有置信度被约束在 `[0, 1]`。

### 2.4 结构化输出（Stage 4 前）

`validate_event` 返回原事件 + 增强字段：

- `confidence_score`
- `validation.initial_confidence`
- `validation.current_confidence`
- `validation.relation_analysis.supports/conflicts`
- `validation.propagation.steps/updated_existing_events`
- `validation.version/status/validated_at`

---

## 3. 输入输出契约

### 3.1 最小输入字段（新事件）

推荐至少包含：

- `event_id`
- `event_description`
- `fact_type`
- `participants`: `[{"name": "..."}]`
- `constraints`: `[{"type": "..."}]`
- `temporal_anchors`: `[{"event_date": "YYYY-MM-DD"}]`
- `sources`: `[{"source": "...", "type": "..."}]`
- `title_anchors`（推荐）

### 3.2 已有事件字段

`existing_events` 结构与新事件基本一致，若已有 `confidence_score` 或 `validation.current_confidence` 会直接参与传播。

---

## 4. 快速使用

### 4.1 单事件验证

```python
from verifier.multi_source_verifier import MultiSourceVerifier

verifier = MultiSourceVerifier(
    alpha=0.30,
    beta=0.40,
    support_threshold=0.45,
    conflict_threshold=0.40,
)

new_event = {
    "event_id": "e_new_001",
    "event_description": "Arsenal won 2-1 against Chelsea.",
    "fact_type": "EVENT",
    "title_anchors": "Arsenal vs Chelsea",
    "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
    "constraints": [{"type": "MATCH_OUTCOME"}],
    "temporal_anchors": [{"event_date": "2025-01-14"}],
    "sources": [{"source": "Sky Sports", "type": "MEDIA"}],
}

existing_events = [
    {
        "event_id": "e_old_001",
        "event_description": "Arsenal defeated Chelsea 2-1.",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Chelsea",
        "participants": [{"name": "Arsenal"}, {"name": "Chelsea"}],
        "constraints": [{"type": "MATCH_OUTCOME"}],
        "temporal_anchors": [{"event_date": "2025-01-14"}],
        "sources": [{"source": "BBC Sport", "type": "MEDIA"}],
        "confidence_score": 0.6,
    }
]

validated = verifier.validate_event(new_event, existing_events, version=1)
print(validated["validation"]["current_confidence"])
print(validated["validation"]["relation_analysis"])
```

### 4.2 批量验证

```python
validated_events = verifier.validate_batch(
    new_events=[new_event_1, new_event_2, new_event_3],
    existing_events=existing_events,
    start_version=10,
)
```

`validate_batch` 会顺序验证：前一个新事件的结果会进入后一个新事件的候选池。

---

## 5. 与图谱持久化层对接

`knowledge_graph.neo4j_writer.Neo4jWriter` 已提供：

- `upsert_validated_event(validated_event)`

该方法会：

1. 写入新 `Event`（含 `initial_confidence/current_confidence/confidence_version`）
2. 更新旧事件置信度（来自传播结果）
3. 建立 `SUPPORTS` / `CONFLICTS` 关系
4. 记录版本与更新时间

示例：

```python
from verifier.multi_source_verifier import MultiSourceVerifier
from knowledge_graph.neo4j_writer import Neo4jWriter

verifier = MultiSourceVerifier()
validated = verifier.validate_event(new_event, existing_events, version=3)

with Neo4jWriter() as writer:
    writer.upsert_validated_event(validated)
```

---

## 6. 可调参数建议

`MultiSourceVerifier(...)` 常用参数：

- `alpha`: 支持传播强度（默认 `0.30`）
- `beta`: 冲突抑制强度（默认 `0.40`）
- `support_threshold`: 判定支持关系阈值
- `conflict_threshold`: 判定冲突关系阈值
- `candidate_time_window_days`: 时间候选窗口
- `acceptance_threshold`: 自动接收阈值
- `review_threshold`: 人工复核阈值

建议：

- 先固定 `alpha/beta`，通过验证集调 `support_threshold/conflict_threshold`
- 对不同来源策略可自定义 `source_weights`

---

## 7. 测试

当前模块对应测试文件：`tests/test_truth_validation.py`，覆盖：

- 单/多来源置信计算
- 支持传播提升
- 冲突传播抑制
- 输出结构完整性

在项目根目录运行：

```bash
pytest tests/test_truth_validation.py -q
```

---

## 8. 注意事项

- 该模块当前为“局部传播、非递归扩散”，避免置信爆炸。
- 冲突检测使用规则法（否定/数值/唯一性），后续可替换为 NLI 或语义匹配模型。
- 若输入事件字段不完整（特别是 `participants` / `temporal_anchors`），关系检测质量会明显下降。
