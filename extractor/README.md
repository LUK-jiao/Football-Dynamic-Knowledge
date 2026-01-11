# 足球领域锚点抽取器 (Football Anchor Extractor)

## 📖 概述

**FootballAnchorExtractor** 是一个专门用于足球领域文本的实体和锚点抽取器。它从语义分块（由 `preprocess/semantic_blocker/` 模块生成）中提取四类锚点，用于知识图谱构建。

## 🎯 四类锚点

### 1. **参与者锚点 (Participant Anchors)**
识别文本中的实体：
- **Player**: 球员（如 "De Ligt", "Cristiano Ronaldo"）
- **Club**: 俱乐部（如 "Manchester United", "Bayern Munich"）
- **Coach**: 教练（如 "Pep Guardiola", "Erik ten Hag"）
- **Team**: 国家队/球队（如 "England national team"）
- **Stadium**: 球场（如 "Old Trafford Stadium"）
- **Tournament**: 赛事（如 "Champions League", "Premier League"）
- **Referee**: 裁判
- **Other**: 其他实体

### 2. **时间锚点 (Temporal Anchors)**
提取事件时间信息：
- **event_date**: 事件发生日期
- **valid_from**: 有效开始日期
- **valid_to**: 有效结束日期

支持的日期格式：
- 明确日期：`2025-09-01`, `September 1, 2025`, `1 September 2025`
- 相对日期：`today`, `tomorrow`, `yesterday`, `next week`

### 3. **来源锚点 (Source Anchors)**
识别信息来源及其类型：
- **Media**: 媒体来源（BBC, Sky Sports, ESPN 等）
- **Official**: 官方声明（俱乐部公告、联赛官方等）
- **Social**: 社交媒体（Twitter, Instagram 等）
- **Other**: 其他来源

### 4. **约束锚点 (Constraint Anchors)**
提取事件相关的状态约束：
- **TRANSFER_STATUS**: 转会状态
  - `transfer_possible`: 可能转会（agreed, sign, join）
  - `transfer_completed`: 转会完成（signed, joined）
  - `transfer_rumored`: 转会传闻（linked, interested）
  - `transfer_rejected`: 转会拒绝（rejected, refused）

- **SCORE_STATUS**: 比分状态
  - `score_3-2`: 比分记录

- **CONTRACT_STATUS**: 合同状态
  - `contract_active`: 合同有效
  - `contract_expired`: 合同到期
  - `contract_extended`: 合同续约

- **MATCH_STATUS**: 比赛状态
  - `match_scheduled`: 比赛安排
  - `match_completed`: 比赛完成
  - `match_postponed`: 比赛延期
  - `match_cancelled`: 比赛取消

- **INJURY_STATUS**: 伤病状态
  - `injured`: 受伤
  - `recovering`: 恢复中
  - `fit`: 健康/可用

- **SUSPENSION_STATUS**: 停赛状态
  - `suspended`: 停赛
  - `available`: 可用

## 🚀 使用方法

### 基本使用

```python
from extractor.ner import FootballAnchorExtractor

# 初始化抽取器
extractor = FootballAnchorExtractor()

# 输入语义分块
chunk = {
    "block_id": "001",
    "text": "De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
    "source": "BBC",
    "publish_date": "2025-08-23"
}

# 提取锚点
result = extractor.extract_anchors(chunk)

# 输出包含四类锚点
print(result)
```

### 输出格式

```json
{
  "block_id": "001",
  "text": "De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
  "source": "BBC",
  "publish_date": "2025-08-23",
  "anchors": {
    "participants": [
      {"type": "Player", "name": "De Ligt"},
      {"type": "Club", "name": "Manchester United"},
      {"type": "Club", "name": "Bayern Munich"}
    ],
    "temporal_anchors": [
      {"event_date": "2025-09-01", "valid_from": "2025-09-01", "valid_to": "2025-09-01"}
    ],
    "sources": [
      {"name": "BBC", "type": "Media"}
    ],
    "constraints": [
      {"type": "TRANSFER_STATUS", "subject": "De Ligt", "expected_state": "transfer_possible"}
    ]
  },
  "fact_type": {"event":} 
}
```

### 批量处理

```python
from extractor.ner import FootballAnchorExtractor

extractor = FootballAnchorExtractor()

chunks = [
    {"block_id": "001", "text": "...", "source": "BBC", "publish_date": "2025-11-20"},
    {"block_id": "002", "text": "...", "source": "ESPN", "publish_date": "2025-11-21"},
    {"block_id": "003", "text": "...", "source": "Official", "publish_date": "2025-11-22"}
]

results = [extractor.extract_anchors(chunk) for chunk in chunks]
```

## 🔗 数据流整合

### 与 semantic_blocker 集成

```python
from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, GranularityMode
from extractor.ner import FootballAnchorExtractor

# 1. 语义分块
chunker = SemanticChunker(
    config=ChunkerConfig(granularity=GranularityMode.MEDIUM)
)
chunks = chunker.chunk_text(
    text="原始足球新闻文本...",
    metadata={"source": "BBC", "publish_date": "2025-09-01"}
)

# 2. 锚点抽取
extractor = FootballAnchorExtractor()
enriched_chunks = []

for i, chunk in enumerate(chunks):
    chunk_data = {
        "block_id": f"chunk_{i:03d}",
        "text": chunk.text,
        "source": "BBC",
        "publish_date": "2025-09-01"
    }
    result = extractor.extract_anchors(chunk_data)
    enriched_chunks.append(result)

# 3. 输出到知识图谱构建
# enriched_chunks 现在可以传递给 knowledge_graph/ 模块
```

### 与知识图谱集成

```python
from knowledge_graph.neo4j_service import Neo4jService

# 假设已有带锚点的分块
enriched_chunk = {
    "block_id": "001",
    "text": "...",
    "anchors": {
        "participants": [...],
        "temporal_anchors": [...],
        "sources": [...],
        "constraints": [...]
    }
}

# 构建图谱节点
neo4j = Neo4jService(uri="bolt://localhost:7687", user="neo4j", password="password")
await neo4j.connect()

# 创建参与者节点
for participant in enriched_chunk["anchors"]["participants"]:
    await neo4j.create_node(
        label=participant["type"],
        properties={"name": participant["name"]}
    )

# 创建事件节点（绑定时间和来源）
for temporal in enriched_chunk["anchors"]["temporal_anchors"]:
    await neo4j.create_node(
        label="Event",
        properties={
            "text": enriched_chunk["text"],
            "event_date": temporal["event_date"],
            "block_id": enriched_chunk["block_id"]
        }
    )
```

## 🧪 测试

运行测试套件：

```bash
# 使用虚拟环境
.venv/bin/python test_anchor_extractor.py
```

测试涵盖：
1. ✅ 转会新闻（球员、俱乐部、转会状态）
2. ✅ 比赛报道（比分、球场、球员表现）
3. ✅ 伤病新闻（伤病状态、官方来源）
4. ✅ 合同续约（合同状态、引用来源）
5. ✅ 锦标赛比赛（赛事、球场、比赛状态）
6. ✅ 复杂场景（多实体、多约束）
7. ✅ 批量处理

## 📊 性能特点

| 特性 | 说明 |
|------|------|
| **实时处理** | 无需预训练模型，基于规则和模式匹配 |
| **领域适配** | 专门针对足球领域优化（俱乐部名、赛事名等） |
| **可扩展** | 支持添加 LLM 后端进行智能识别 |
| **零依赖** | 仅需 Python 标准库（datetime, re, json） |
| **高准确率** | 针对常见足球新闻场景优化 |

## 🔧 自定义配置

### 添加已知实体

```python
extractor = FootballAnchorExtractor()

# 添加更多俱乐部
extractor.known_clubs.update([
    "Newcastle United", "Aston Villa", "West Ham"
])

# 添加更多媒体
extractor.known_media.update([
    "FourFourTwo", "TalkSport", "Football365"
])
```

### 使用 LLM 后端（可选）

```python
from preprocess.semantic_blocker import OllamaBackend

# 使用 LLM 辅助识别
llm_backend = OllamaBackend()
extractor = FootballAnchorExtractor(llm_backend=llm_backend)
```

## 📝 注意事项

1. **日期格式**：所有日期统一为 `YYYY-MM-DD` 格式
2. **去重机制**：同一实体在同一分块中只出现一次
3. **约束绑定**：约束锚点的 `subject` 字段关联到具体的参与者
4. **空数组处理**：如果某类锚点不存在，返回空数组 `[]`
5. **JSON 输出**：所有输出严格遵循 JSON 格式，可直接解析

## 🌟 优势

相比通用 NER 系统：
- ✅ **领域专注**：专门为足球文本优化
- ✅ **结构化输出**：四类锚点清晰分类
- ✅ **KG 就绪**：输出格式直接用于图谱构建
- ✅ **上下文感知**：利用发布日期推理相对时间
- ✅ **约束识别**：提取状态约束用于知识验证

## 📂 项目定位

```
Football_Dynamic_Knowledge/
├── preprocess/semantic_blocker/    ← 语义分块（输入）
│   └── semantic_chunker.py
├── extractor/                      ← 📍 当前模块（锚点抽取）
│   ├── ner.py                      ← FootballAnchorExtractor
│   └── README.md                   ← 本文档
└── knowledge_graph/                ← 知识图谱构建（输出）
    └── neo4j_service.py
```

## 🔄 版本历史

- **v1.0.0** (2026-01-07)
  - ✅ 实现四类锚点抽取
  - ✅ 支持足球领域实体识别
  - ✅ 时间锚点解析（明确日期 + 相对日期）
  - ✅ 来源分类（Media/Official/Social/Other）
  - ✅ 六种约束类型识别
  - ✅ 完整测试套件

## 📧 支持

如需帮助或建议，请查看：
- 测试文件：`test_anchor_extractor.py`
- 集成测试：`preprocess/integration_test.py`
- 主文档：项目根目录 `README.md`
