# Football Dynamic Knowledge - 项目架构文档

## 📋 项目概述

**项目名称**: Football Dynamic Knowledge (足球动态知识图谱系统)  
**技术架构**: Event-Centric Knowledge Graph + GraphRAG  
**核心功能**: 足球新闻采集 → 文本预处理 → 事实抽取 → 知识图谱构建 → 智能问答

**技术栈**:
- **图数据库**: Neo4j 5.x
- **LLM**: Ollama (llama3:latest, gemma3:12b)
- **NLP框架**: spaCy
- **编程语言**: Python 3.10+
- **Web框架**: FastAPI
- **异步任务**: Celery + Redis

---

## 🏗️ 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     数据采集层 (datasource/)                      │
│  Web爬虫 | API采集 | RSS订阅 → 原始足球新闻文本                   │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   文本预处理层 (preprocess/)                      │
│  句子分割 (spaCy) → 语义分块 (LLM Binary Classifier)             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                  知识抽取层 (extractor_v1/)                       │
│  事件分解 (LLM) → 锚点抽取 (结构化) → 扁平化JSON输出             │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│               知识图谱持久化层 (knowledge_graph/)                 │
│  Neo4j写入 | 约束索引 | 完整视图查询                              │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                      RAG问答层 (rag/)                            │
│  查询解析 → 图检索 → 上下文构建 → LLM生成答案                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 知识图谱设计 (knowledge_graph/)

### 1. 图谱Schema设计

#### 🔷 节点类型 (5种)

##### 1.1 Event (事件节点) - **核心节点**
**设计理念**: 采用Event-Centric建模，所有信息围绕事件组织

**属性**:
```python
{
    "event_id": str,              # 唯一标识 (主键)
    "event_description": str,     # 事件描述
    "fact_type": str,            # EVENT | RELATION | STATE
    "title_anchors": str,        # 标题锚点
    "event_date": Date,          # 事件日期 (Neo4j Date类型)
    "valid_from": Date,          # 有效期起始 (STATE类型使用)
    "valid_to": Date             # 有效期结束 (STATE类型使用)
}
```

**事实类型说明**:
- `EVENT`: 时间点事件 (进球、转会、比赛结果)
- `STATE`: 持续状态 (合同有效期、伤病状态)
- `RELATION`: 关系事实 (教练执教、球员隶属)

**示例**:
```cypher
(:Event {
  event_id: "block_1-1",
  event_description: "Arsenal defeated Crystal Palace 8-7 on penalties",
  fact_type: "EVENT",
  event_date: date("2025-01-14"),
  title_anchors: "Arsenal vs Palace EFL Cup"
})
```

##### 1.2 Entity (实体节点)
**设计理念**: 多标签分类，支持5种实体类型

**基础标签**: `:Entity`  
**子类型标签**: `:Person` | `:Club` | `:NationalTeam` | `:Competition` | `:Stadium`

**属性**:
```python
{
    "entity_id": str,    # 唯一标识 (从name生成，主键)
    "name": str,         # 实体名称
    "type": str          # 实体类型
}
```

**实体类型枚举**:
1. **Person**: 球员、教练、裁判、官员
2. **Club**: 俱乐部 (Arsenal, Manchester United)
3. **NationalTeam**: 国家队 (England, Brazil)
4. **Competition**: 赛事 (Premier League, Champions League)
5. **Stadium**: 体育场 (Old Trafford, Emirates Stadium)

**示例**:
```cypher
(:Entity:Person {
  entity_id: "bukayo_saka",
  name: "Bukayo Saka",
  type: "Person"
})

(:Entity:Club {
  entity_id: "arsenal",
  name: "Arsenal",
  type: "Club"
})
```

##### 1.3 Source (来源节点)
**设计理念**: 标识信息来源和可信度

**属性**:
```python
{
    "source_id": str,    # 唯一标识 (主键)
    "source": str,       # 来源名称
    "type": str          # OFFICIAL | MEDIA | USER_GENERATED | UNKNOWN
}
```

**来源类型说明**:
- `OFFICIAL`: 官方来源 (俱乐部官网、FIFA、UEFA)
- `MEDIA`: 媒体机构 (BBC Sport, Sky Sports, The Athletic)
- `USER_GENERATED`: 用户生成 (社交媒体、论坛)
- `UNKNOWN`: 未知来源

**示例**:
```cypher
(:Source {
  source_id: "bbc_sport",
  source: "BBC Sport",
  type: "MEDIA"
})
```

##### 1.4 ConstraintAnchor (约束锚点)
**设计理念**: 事件分类器，支持精确检索

**9种约束类型** (严格枚举):
```python
CONSTRAINT_TYPES = [
    "MATCH_ACTION",           # 比赛动作 (进球、助攻、红牌、扑救)
    "MATCH_OUTCOME",          # 比赛结果 (胜负平、比分)
    "MATCH_CONTEXT",          # 比赛背景 (赛前分析、战术)
    "PLAYER_MOVEMENT",        # 球员转会 (加盟、租借、离队)
    "CONTRACT_EVENT",         # 合同事件 (续约、签约)
    "AVAILABILITY_EVENT",     # 可用性变化 (伤病、停赛、复出)
    "APPOINTMENT_EVENT",      # 任命事件 (教练上任、下课)
    "PERFORMANCE_EVENT",      # 表现评估 (评分、荣誉)
    "ADMINISTRATIVE_EVENT"    # 管理事件 (官方声明、政策)
]
```

**属性**:
```python
{
    "type": str    # 约束类型 (主键)
}
```

**示例**:
```cypher
(:ConstraintAnchor {type: "MATCH_ACTION"})
(:ConstraintAnchor {type: "PLAYER_MOVEMENT"})
```

##### 1.5 TitleAnchor (标题锚点)
**设计理念**: 将同一事件的不同报道聚合

**属性**:
```python
{
    "title": str    # 标题文本 (主键)
}
```

**用途**:
- 同一比赛的不同角度报道
- 同一转会的多源验证
- 支持Multi-hop检索扩展

**示例**:
```cypher
(:TitleAnchor {
  title: "Arsenal vs Crystal Palace EFL Cup quarter-final"
})
```

---

### 2. 关系类型 (4种)

#### 2.1 INVOLVES (事件-实体)
```cypher
(Event)-[:INVOLVES]->(Entity)
```
**语义**: 实体参与了该事件

**示例**:
```cypher
(:Event {event_description: "Saka scored"})-[:INVOLVES]->(:Entity:Person {name: "Bukayo Saka"})
```

#### 2.2 REPORTED_BY (事件-来源)
```cypher
(Event)-[:REPORTED_BY]->(Source)
```
**语义**: 事件由该来源报道

**示例**:
```cypher
(:Event)-[:REPORTED_BY]->(:Source {source: "BBC Sport"})
```

#### 2.3 CONSTRAINS (约束-事件)
```cypher
(ConstraintAnchor)-[:CONSTRAINS]->(Event)
```
**语义**: 事件属于该类型约束

**示例**:
```cypher
(:ConstraintAnchor {type: "MATCH_ACTION"})-[:CONSTRAINS]->(:Event)
```

#### 2.4 HAS_TITLE_ANCHOR (事件-标题)
```cypher
(Event)-[:HAS_TITLE_ANCHOR]->(TitleAnchor)
```
**语义**: 事件关联到该标题

**示例**:
```cypher
(:Event)-[:HAS_TITLE_ANCHOR]->(:TitleAnchor {title: "Arsenal vs Palace"})
```

---

### 3. 索引和约束

#### 3.1 唯一性约束 (Uniqueness Constraints)
```cypher
-- Event节点
CREATE CONSTRAINT event_id_unique IF NOT EXISTS 
FOR (e:Event) REQUIRE e.event_id IS UNIQUE

-- Entity节点
CREATE CONSTRAINT entity_id_unique IF NOT EXISTS 
FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE

-- Source节点
CREATE CONSTRAINT source_id_unique IF NOT EXISTS 
FOR (s:Source) REQUIRE s.source_id IS UNIQUE

-- ConstraintAnchor节点
CREATE CONSTRAINT constraint_type_unique IF NOT EXISTS 
FOR (c:ConstraintAnchor) REQUIRE c.type IS UNIQUE

-- TitleAnchor节点
CREATE CONSTRAINT title_unique IF NOT EXISTS 
FOR (t:TitleAnchor) REQUIRE t.title IS UNIQUE
```

**作用**:
- ✅ 防止重复插入
- ✅ 自动创建索引 (加速查询)
- ✅ MERGE操作性能优化

#### 3.2 自动索引
Neo4j的唯一性约束会自动创建以下索引:
- `Event.event_id`
- `Entity.entity_id`
- `Source.source_id`
- `ConstraintAnchor.type`
- `TitleAnchor.title`

#### 3.3 额外推荐索引
```cypher
-- 加速时间范围查询
CREATE INDEX event_date_index IF NOT EXISTS FOR (e:Event) ON (e.event_date)

-- 加速实体名称查询
CREATE INDEX entity_name_index IF NOT EXISTS FOR (e:Entity) ON (e.name)

-- 加速事实类型过滤
CREATE INDEX fact_type_index IF NOT EXISTS FOR (e:Event) ON (e.fact_type)
```

---

### 4. 数据写入接口 (Neo4jWriter)

#### 4.1 核心方法

```python
class Neo4jWriter:
    def __init__(self, uri, user, password):
        """初始化Neo4j连接"""
    
    def initialize_constraints(self):
        """创建所有唯一性约束"""
    
    def upsert_event(self, event_data: Dict[str, Any]):
        """写入单个事件 (包含所有关系)"""
    
    def upsert_events(self, events: List[Dict[str, Any]]):
        """批量写入事件 (高性能)"""
    
    def get_event_full_view(self, event_id: str):
        """查询事件完整视图"""
    
    def get_entity_events(self, entity_id: str):
        """查询实体相关的所有事件"""
    
    def get_constraint_events(self, constraint_type: str):
        """查询指定约束类型的所有事件"""
```

#### 4.2 输入数据格式
```python
event_data = {
    "event_id": "001",
    "event_description": "Saka scored a goal",
    "fact_type": "EVENT",
    "title_anchors": "Arsenal vs Palace",
    
    "participants": [
        {"name": "Bukayo Saka", "type": "Person"},
        {"name": "Arsenal", "type": "Club"}
    ],
    
    "temporal_anchors": [{
        "event_date": "2025-01-14"
    }],
    
    "sources": [{
        "source": "BBC Sport",
        "type": "MEDIA"
    }],
    
    "constraints": [{
        "type": "MATCH_ACTION"
    }]
}
```

---

## 🔧 文本预处理层 (preprocess/)

### 1. 系统架构

**设计理念**: 简单可靠 + 可控确定 + 容错健壮

```
原始文本 → [句子分割] → 句子列表 → [语义分块] → 语义块
```

---

### 2. 核心模块

#### 2.1 句子分割器 (Sentence Splitter)

**实现方式**: spaCy NLP Pipeline  
**文件位置**: `sentence_splitter/splitter.py`

**核心功能**:
```python
from preprocess.sentence_splitter import SentenceSplitter

splitter = SentenceSplitter(model_name="en_core_web_sm")
sentences = splitter.split(raw_text)
```

**处理流程**:
1. spaCy分句 (语言模型边界检测)
2. 引用聚合 (合并引号内多句)
3. 清洗过滤 (空白、重复、短句)

**技术规格**:

| 项目 | 说明 |
|------|------|
| 依赖模型 | `en_core_web_sm` |
| 处理能力 | 缩写、引号、列表、编号 |
| 最小长度 | 10字符 |
| 性能 | ~1000句/秒 |

**特殊处理**:
- ✅ 引用聚合: `"Sent1." "Sent2."` → `"Sent1. Sent2."`
- ✅ 缩写识别: `Dr. Smith` 不会错误分割
- ✅ 列表处理: 保持编号结构完整

---

#### 2.2 语义分块器 (Semantic Chunker)

**实现方式**: LLM连续评分 + 阈值决策 (v2.0)  
**文件位置**: `semantic_blocker/semantic_chunker.py`

##### 核心算法架构

```
句子对 → LLM评分(0.0-1.0) → 阈值判断 → 强制规则 → 孤儿合并 → 语义块
```

**v2.0改进** (相比v1.0二元决策):
- ✅ 连续评分 (0.0-1.0) 替代二元输出
- ✅ 可调阈值控制粒度
- ✅ 结构化强制规则
- ✅ 孤儿句合并
- ✅ 可追溯的分数日志

##### 使用示例

```python
from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

backend = OllamaBackend(model="gemma3:12b")
chunks = semantic_chunk(
    sentences=["Sent1", "Sent2", "Sent3"],
    llm_backend=backend,
    granularity="medium"  # fine | medium | coarse
)
```

##### 粒度配置

| 模式 | 阈值 | 适用场景 |
|------|------|----------|
| `fine` | 0.45 | 细粒度，独立事件分离 |
| `medium` | 0.55 | **推荐**，平衡准确度 |
| `coarse` | 0.65 | 粗粒度，保持连贯性 |

##### 高级配置

```python
from preprocess.semantic_blocker import ChunkerConfig, GranularityMode

config = ChunkerConfig(
    granularity=GranularityMode.MEDIUM,
    break_threshold=0.55,              # 自定义阈值
    max_sentences_per_chunk=5,         # 最大句子数
    context_window=2,                  # 上下文窗口
    enable_structural_rules=True,      # 结构化规则
    enable_orphan_merge=True,          # 孤儿合并
    log_scores=True                    # 日志记录
)
```

##### 评分机制

**LLM评分规则**:
- `0.0-0.3`: 同一主题 (继续累积)
- `0.4-0.6`: 相关但区分 (软边界)
- `0.7-1.0`: 完全不同主题 (硬切分)

**决策阈值**:
- `score < threshold`: 继续当前块
- `score ≥ threshold`: 开始新块

##### 后处理规则

**1. 强制分割** (Structural Rules):
- 引号边界: `"..." → 切分`
- 统计标记: `Statistics:` → 切分
- 列表编号: `1)`, `2)` → 切分

**2. 孤儿合并** (Orphan Merge):
- 单句块向前合并到上一块

**3. 长度限制**:
- 达到`max_sentences_per_chunk`时强制切分

##### 容错机制

**三层Fallback**:
1. LLM评分失败 → 返回0.7 (保守切分)
2. LLM超时 → 重试1次
3. LLM不可用 → 规则分块器 (关键词)

---

### 3. 完整Pipeline示例

```python
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

# 原始新闻
text = """
Arsenal won 2-1 against Palace. Saka scored the winner. 
Manager Arteta praised the team.

In other news, United signed a striker for £50m.
"""

# 句子分割
splitter = SentenceSplitter()
sentences = splitter.split(text)
# → ["Arsenal won 2-1...", "Saka scored...", "Manager Arteta...", "In other news..."]

# 语义分块
backend = OllamaBackend(model="gemma3:12b")
chunks = semantic_chunk(sentences, backend, granularity="medium")
# → [
#     ["Arsenal won 2-1...", "Saka scored...", "Manager Arteta..."],
#     ["In other news...", "United signed..."]
#   ]
```

---

### 4. 技术规格

**性能指标**:

| 指标 | 数值 |
|------|------|
| 句子分割速度 | ~1000句/秒 |
| 语义分块速度 | ~0.5秒/对 (LLM) |
| 内存占用 | ~500MB (spaCy模型) |
| 批处理能力 | 100篇/分钟 |

**推荐模型**:

| 模型 | 参数 | 速度 | 准确度 |
|------|------|------|--------|
| `gemma3:12b` | 12B | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ (推荐) |
| `llama3:latest` | 8B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**依赖项**:
```bash
pip install spacy requests
python -m spacy download en_core_web_sm
ollama pull gemma3:12b
```

---

### 5. 设计决策

**为什么用spaCy而不是正则?**
- ✅ 处理复杂边界 (缩写、引号)
- ✅ 基于语言模型，准确率高
- ✅ 成熟稳定，社区支持好

**为什么v2.0改用连续评分?**
- ❌ v1.0二元决策在边界模糊时不稳定
- ✅ v2.0连续分数可调阈值
- ✅ 更确定、可控、可追溯

**为什么需要后处理规则?**
- ❌ 纯LLM可能产生孤儿块
- ✅ 规则保证输出质量基线
- ✅ 处理特殊结构 (引用、列表)

---

## 🎯 知识抽取层 (extractor_v1/)

### 1. 两阶段抽取架构

```
语义块 → [事件分解层] → 事件单元 → [锚点抽取层] → 结构化JSON
```

#### 阶段1: 事件分解 (Event Decomposition)
**功能**: 将复杂语义块拆分为独立事件

**实现文件**: `event_decomposition.py`

**核心方法**:
```python
from extractor_v1 import decompose_semantic_block

events = decompose_semantic_block(
    semantic_block="Arsenal won 2-1. Saka scored the winner.",
    model="llama3:latest"
)
# 输出: [
#   "Arsenal won 2-1.",
#   "Saka scored the winner."
# ]
```

**LLM任务**: 判断语义块是否包含多个独立事件，如果是则拆分

---

#### 阶段2: 锚点抽取 (Anchor Extraction)
**功能**: 从事件描述中抽取结构化锚点

**实现文件**: `anchor_extractor.py`

**核心方法**:
```python
from extractor_v1 import extract_event_anchors

result = extract_event_anchors(
    event_description="Bukayo Saka scored a goal for Arsenal",
    block_id="001",
    source_metadata={
        "source": "BBC Sport",
        "publish_date": "2025-01-14"
    },
    model="llama3:latest"
)
```

---

### 2. 输出格式 (扁平化结构 v2.0)

```json
{
  "event_id": "001-1",
  "event_description": "Bukayo Saka scored a goal for Arsenal",
  "title_anchors": "Arsenal vs Palace",
  "event_date": "2025-01-14"（could be null）
  
  "participants": [
    {"type": "Person", "name": "Bukayo Saka"},
    {"type": "Club", "name": "Arsenal"}
  ],
  
  "sources": [{
    "type": "MEDIA",
    "source": "BBC Sport",
    "publish_date": "2025-01-14"（not null）
  }],
  
  "constraints": [（>=1)
    {"type": "MATCH_ACTION"}
  ],
  
  "inference_time": 1.234
}
```

---

### 3. 四类锚点详解

#### 3.1 Participants (参与实体)
**类型枚举**:
- `Person`: 球员、教练、官员
- `Club`: 俱乐部
- `NationalTeam`: 国家队
- `Competition`: 赛事
- `Stadium`: 球场

**抽取规则**:
- ✅ 只从event_description提取
- ✅ 使用原始名称 (不做别名扩展)
- ✅ 忽略代词 (he, they)

#### 3.2 Temporal Anchors (时间锚点)
**字段说明**:
- `event_date`: 事件发生时间 (仅EVENT类型)
- `valid_from`: 状态开始时间 (仅STATE类型)
- `valid_to`: 状态结束时间 (仅STATE类型)

**日期格式**: `YYYY-MM-DD` | `YYYY-MM` | `YYYY`

**示例**:
```json
// EVENT类型
{"event_date": "2025-01-14", "valid_from": null, "valid_to": null}

// STATE类型
{"event_date": null, "valid_from": "2024-07-01", "valid_to": "2029-06-30"}
```

#### 3.3 Sources (信息来源)
**字段**:
- `type`: OFFICIAL | MEDIA | USER_GENERATED | UNKNOWN
- `source`: 来源名称
- `publish_date`: 发布日期

**类型判定规则**:
- 官方网站、俱乐部公告 → `OFFICIAL`
- BBC, Sky Sports, ESPN → `MEDIA`
- Twitter, Reddit → `USER_GENERATED`
- 无法确定 → `UNKNOWN`

#### 3.4 Constraints (约束类型)
**9种严格分类**: (只有type字段)
1. `MATCH_ACTION` - 比赛动作
2. `MATCH_OUTCOME` - 比赛结果
3. `MATCH_CONTEXT` - 比赛背景
4. `PLAYER_MOVEMENT` - 球员转会
5. `CONTRACT_EVENT` - 合同事件
6. `AVAILABILITY_EVENT` - 可用性变化
7. `APPOINTMENT_EVENT` - 任命事件
8. `PERFORMANCE_EVENT` - 表现评估
9. `ADMINISTRATIVE_EVENT` - 管理事件

**分类规则**:
- 一个事件可以有多个约束
- 必须从9种中选择
- 不能自定义新类型

---

### 4. LLM后端 (OllamaBackend)

**实现文件**: `ollama_backend.py`

**核心功能**:
```python
from extractor_v1 import OllamaBackend

backend = OllamaBackend(
    model="llama3:latest",
    base_url="http://localhost:11434"
)

# 结构化生成
response = backend.generate_structured(
    prompt="Extract entities from: Saka scored",
    temperature=0.1
)
```

**特性**:
- ✅ 支持流式输出
- ✅ 自动重试机制
- ✅ 超时控制
- ✅ 温度参数调节

**推荐模型**: `llama3:latest` (8B参数)

---

## 🤖 GraphRAG问答层 (rag/)

### 1. 系统架构

```
自然语言问题 → [QueryAnalyzer] → 结构化约束 
                     ↓
              [GraphRetriever] → 检索事件
                     ↓
              [ContextBuilder] → 格式化上下文
                     ↓
              [RAGLLMBackend] → 生成答案
```

---

### 2. 核心组件

#### 2.1 QueryAnalyzer (查询分析器)

**功能**: 将自然语言问题解析为结构化查询

**实现策略**:
1. **主策略**: LLM解析 (Ollama)
2. **容错**: 自动重试1次
3. **备选**: 规则解析 (关键词匹配)

**输出格式** (直接使用LLM输出，无转换):
```json
{
  "entities": [
    {"name": "Bukayo Saka", "entity_type": "Person"}
  ],
  "time_filter": {
    "mode": "event_date",
    "start": "2025-01-01",
    "end": "2025-01-31"
  },
  "constraint_types": ["MATCH_ACTION"],
  "fact_types": ["EVENT"],
  "intent": "fact",
  "limit": 20
}
```

**intent类型**:
- `fact`: 查询具体事实 (limit=20)
- `summary`: 总结概览 (limit=50)
- `analysis`: 深度分析 (limit=50 + 子图扩展)

**使用示例**:
```python
from rag import QueryAnalyzer

analyzer = QueryAnalyzer(model="llama3:latest")
result = analyzer.parse("How many goals did Saka score in 2025?")

print(result['entities'])        # [{"name": "Bukayo Saka", "entity_type": "Person"}]
print(result['time_filter'])     # {"mode": "event_date", "start": "2025-01-01", ...}
print(result['intent'])          # "fact"
```

**LLM Prompt结构**:
- 系统角色: 结构化查询解析助手
- 输出要求: 严格JSON格式
- Schema定义: 详细的字段说明
- 解析规则: 实体类型、时间格式、意图判定

---

#### 2.2 GraphRetriever (图检索器)

**功能**: 根据结构化约束从Neo4j检索事件

**检索维度**:
1. **实体过滤**: 按球员/俱乐部名称
2. **时间过滤**: 按事件日期范围
3. **约束过滤**: 按事件类型 (9种)
4. **意图扩展**: analysis模式自动扩展相关事件

**核心方法**:
```python
from rag import GraphRetriever
from knowledge_graph import Neo4jWriter

writer = Neo4jWriter()
retriever = GraphRetriever(writer)

events = retriever.retrieve(parsed_query)
```

**查询特性**:
- ✅ 参数化Cypher (防SQL注入)
- ✅ 完整事件上下文 (实体+来源+约束+标题)
- ✅ 时间倒序排列
- ✅ Multi-hop扩展 (通过TitleAnchor)

**返回格式**:
```python
[
    {
        "event_id": "block_1-1",
        "event_description": "Arsenal defeated Palace 8-7 on penalties",
        "event_date": "2025-01-14",
        "fact_type": "EVENT",
        "title_anchors": "Arsenal vs Palace EFL Cup",
        "entities": ["Arsenal", "Crystal Palace"],
        "sources": ["BBC Sport"],
        "constraints": ["MATCH_OUTCOME"],
        "titles": ["Arsenal vs Palace EFL Cup"]
    }
]
```

---

#### 2.3 ContextBuilder (上下文构建器)

**功能**: 将检索的事件格式化为LLM可读的上下文

**三种格式化模式**:

##### 模式1: Standard (标准格式)
用途: fact查询  
排序: 时间倒序 (最新在前)

```
Event 1 [2025-01-14]:
Arsenal defeated Crystal Palace 8-7 on penalties
- Entities: Arsenal, Crystal Palace
- Type: MATCH_OUTCOME
- Source: BBC Sport

Event 2 [2025-01-10]:
...
```

##### 模式2: Summary (摘要格式)
用途: summary查询  
排序: 按事件类型分组

```
=== MATCH_OUTCOME Events ===
1. Arsenal defeated Palace (2025-01-14)
2. Arsenal drew with Brighton (2025-01-10)

=== MATCH_ACTION Events ===
1. Saka scored a goal (2025-01-14)
...
```

##### 模式3: Analysis (分析格式)
用途: analysis查询  
排序: 时间正序 (时间线叙事)

```
Timeline of Events:

[2025-01-10] Arteta appointed as manager
[2025-01-14] Arsenal won first match
[2025-01-20] Saka scored hat-trick
...
```

**使用示例**:
```python
from rag import ContextBuilder

builder = ContextBuilder(max_events=50)

# 标准格式
context = builder.build(events)

# 摘要格式
summary_context = builder.build_summary_context(events)

# 分析格式
analysis_context = builder.build_analysis_context(events)
```

---

#### 2.4 RAGLLMBackend (LLM后端)

**功能**: 专用于RAG的LLM接口 (独立于extractor)

**核心方法**:
```python
from rag import RAGLLMBackend

llm = RAGLLMBackend(model="llama3:latest")

# 生成结构化输出
structured = llm.generate_structured(prompt, temperature=0.1)

# 生成自然语言答案
answer = llm.generate_answer(
    question="How many goals did Saka score?",
    context="Event 1: Saka scored...",
    temperature=0.7
)
```

**与extractor_v1的区别**:
- 独立的后端实例
- 不同的默认temperature
- 针对问答优化的prompt

---

#### 2.5 GraphRAG (主编排器)

**功能**: 整合所有组件，提供统一的问答接口

**核心方法**:
```python
from rag import GraphRAG
from knowledge_graph import Neo4jWriter

writer = Neo4jWriter()
rag = GraphRAG(neo4j_writer=writer, model="llama3:latest")

# 单个问题
response = rag.answer("How many goals did Saka score in 2025?")
print(response['answer'])
print(response['retrieved_events'])

# 批量问题
questions = ["Question 1", "Question 2"]
responses = rag.batch_answer(questions)

# 交互模式
rag.interactive_mode()
```

**完整流程**:
1. QueryAnalyzer解析问题
2. GraphRetriever检索事件
3. ContextBuilder格式化上下文
4. RAGLLMBackend生成答案
5. 返回答案+检索证据

---

### 3. GraphRAG特性

#### 3.1 时间感知 (Temporal-Aware)
- ✅ 支持年份、月份、日期范围
- ✅ "最近"、"上个月"等自然语言
- ✅ 时间倒序排列 (最新优先)

#### 3.2 约束引导 (Constraint-Guided)
- ✅ 9种事件类型精确过滤
- ✅ 组合约束支持
- ✅ 自动推断约束类型

#### 3.3 可解释性 (Explainable)
- ✅ 返回完整检索证据
- ✅ 显示来源和实体
- ✅ 支持溯源验证

#### 3.4 Multi-hop检索
- ✅ 通过TitleAnchor关联事件
- ✅ analysis模式自动扩展
- ✅ 发现事件间因果关系

---

## 📁 项目目录结构

```
Football_Dynamic_Knowledge/
│
├── datasource/                  # 数据采集层
│   └── crawler.py              # Web爬虫
│
├── preprocess/                  # 文本预处理层
│   ├── sentence_splitter/      # 句子分割器 (spaCy)
│   │   └── splitter.py
│   ├── semantic_blocker/       # 语义分块器 (LLM)
│   │   ├── semantic_chunker.py
│   │   └── ollama_backend.py
│   └── integration_test.py     # 完整流程测试
│
├── extractor_v1/               # 知识抽取层 (生产版本)
│   ├── event_decomposition.py  # 事件分解
│   ├── anchor_extractor.py     # 锚点抽取
│   ├── ollama_backend.py       # LLM后端
│   └── integrate_test_extractor.py
│
├── knowledge_graph/            # 知识图谱持久化层
│   ├── neo4j_writer.py        # Neo4j写入器
│   ├── load_to_neo4j.py       # 批量加载
│   ├── config.py              # 配置管理
│   └── README.md
│
├── rag/                        # GraphRAG问答层
│   ├── query_analyzer.py      # 查询分析器 (LLM + 规则)
│   ├── graph_retriever.py     # 图检索器 (Cypher)
│   ├── context_builder.py     # 上下文构建器
│   ├── rag_engine.py          # RAG主引擎
│   ├── llm_backend.py         # RAG专用LLM后端
│   ├── utils.py               # 工具函数
│   ├── example_usage.py       # 使用示例
│   ├── test_graphrag.py       # 单元测试
│   └── README.md
│
├── api/                        # FastAPI接口层
│   ├── main.py
│   └── routers/
│       ├── datasource.py
│       └── rag.py
│
├── tests/                      # 集成测试
│   └── integration_test_full_pipeline.py
│
├── configs/                    # 配置文件
│   └── dev.yaml
│
├── core/                       # 核心工具
│   ├── config.py
│   └── logging.py
│
├── docker/                     # Docker部署
│   └── entrypoint.sh
│
├── requirements.txt            # 依赖列表
├── pyproject.toml             # 项目配置
├── Dockerfile
├── docker-compose.yaml
└── README.md
```

---

## 🔄 完整数据流

### 端到端Pipeline

```
1. 数据采集
   └─> BBC Sport新闻原文

2. 文本预处理
   └─> 句子分割 (spaCy)
   └─> 语义分块 (LLM: gemma3:12b)

3. 知识抽取
   └─> 事件分解 (LLM: llama3)
   └─> 锚点抽取 (LLM: llama3)
   └─> 输出扁平化JSON

4. 知识图谱
   └─> Neo4j写入 (upsert_event)
   └─> 创建5种节点 + 4种关系
   └─> 建立索引和约束

5. GraphRAG问答
   └─> QueryAnalyzer解析问题
   └─> GraphRetriever检索事件
   └─> ContextBuilder格式化
   └─> RAGLLMBackend生成答案
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install -r requirements.txt

# 下载spaCy模型
python -m spacy download en_core_web_sm

# 启动Ollama
ollama serve
ollama pull llama3:latest
ollama pull gemma3:12b

# 启动Neo4j
docker run -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5.15
```

### 2. 初始化知识图谱

```python
from knowledge_graph import Neo4jWriter

with Neo4jWriter() as writer:
    writer.initialize_constraints()
```

### 3. 运行完整Pipeline

```python
# 从新闻文本到知识图谱
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_chunk, OllamaBackend
from extractor_v1 import extract_all_events
from knowledge_graph import Neo4jWriter

# 1. 预处理
text = "Arsenal won 2-1. Saka scored the winner."
splitter = SentenceSplitter()
sentences = splitter.split(text)

backend = OllamaBackend(model="gemma3:12b")
chunks = semantic_chunk(sentences, backend)

# 2. 抽取
events = extract_all_events(chunks, source_metadata={"source": "BBC"})

# 3. 写入图谱
writer = Neo4jWriter()
writer.upsert_events(events)
```

### 4. GraphRAG问答

```python
from rag import GraphRAG
from knowledge_graph import Neo4jWriter

writer = Neo4jWriter()
rag = GraphRAG(neo4j_writer=writer)

response = rag.answer("How many goals did Saka score in 2025?")
print(response['answer'])
```

---

## 📊 系统性能指标

### LLM推理时间

| 模块 | 模型 | 平均耗时 |
|------|------|----------|
| 语义分块 | gemma3:12b | ~0.5s/对 |
| 事件分解 | llama3:latest | ~1.0s/块 |
| 锚点抽取 | llama3:latest | ~2.0s/事件 |
| 查询解析 | llama3:latest | ~1.5s/问题 |
| 答案生成 | llama3:latest | ~3.0s/答案 |

### Neo4j查询性能

| 查询类型 | 平均耗时 |
|---------|----------|
| 单事件查询 | <10ms |
| 实体事件查询 | ~50ms |
| 时间范围查询 | ~100ms |
| Multi-hop扩展 | ~200ms |

### 端到端Pipeline

- **单篇新闻处理**: ~30s (包含所有LLM调用)
- **批量写入**: ~1000 events/min
- **RAG问答**: ~5s (检索+生成)

---

## 🔧 技术决策记录

### 为什么选择Event-Centric建模？

**优势**:
1. ✅ 自然匹配新闻报道结构
2. ✅ 支持时序推理和因果分析
3. ✅ 易于处理矛盾和多源验证
4. ✅ 灵活扩展新事件类型

**对比传统Entity-Centric**:
- 传统: `(Saka)-[:SCORED]->(Goal)-[:IN_MATCH]->(Arsenal vs Palace)`
- Event-Centric: `(Event {description: "Saka scored"})-[:INVOLVES]->(Saka, Arsenal, Palace)`

### 为什么使用扁平化JSON？

**原因**:
1. ✅ 直接映射到Neo4j节点属性
2. ✅ 减少嵌套层级，简化解析
3. ✅ 方便批量写入
4. ✅ LLM生成更稳定

### 为什么分离RAG的LLM Backend？

**原因**:
1. ✅ 不同的温度参数需求 (抽取0.1 vs 问答0.7)
2. ✅ 不同的prompt策略
3. ✅ 独立的错误处理
4. ✅ 避免模块耦合

### 为什么使用Ollama而不是OpenAI？

**原因**:
1. ✅ 本地部署，数据隐私
2. ✅ 无API费用
3. ✅ 可控的推理时间
4. ✅ 支持自定义模型

---

## 🎯 未来优化方向

### 短期优化 (1-3个月)

1. **性能优化**
   - [ ] Neo4j查询缓存
   - [ ] LLM并行推理
   - [ ] 批量事件写入优化

2. **准确度提升**
   - [ ] Few-shot示例优化
   - [ ] 规则+LLM混合解析
   - [ ] 多源验证机制

3. **功能增强**
   - [ ] 支持中文查询
   - [ ] 实体消歧和链接
   - [ ] 反馈学习机制

### 中期规划 (3-6个月)

1. **向量检索集成**
   - [ ] 混合检索 (图+向量)
   - [ ] Embedding相似度
   - [ ] Re-ranking机制

2. **多模态支持**
   - [ ] 视频片段抽取
   - [ ] 图片理解
   - [ ] 统计数据整合

3. **生产环境**
   - [ ] FastAPI完整接口
   - [ ] Celery异步任务
   - [ ] 监控和日志系统

### 长期愿景 (6-12个月)

1. **智能体系统**
   - [ ] 主动信息搜集
   - [ ] 多轮对话
   - [ ] 推理和预测

2. **知识演化**
   - [ ] 时序知识图谱
   - [ ] 版本控制
   - [ ] 矛盾检测和解决

3. **社区生态**
   - [ ] 用户标注平台
   - [ ] 知识贡献机制
   - [ ] 开放API

---

## 📚 相关文档

- [知识图谱设计](knowledge_graph/README.md)
- [文本预处理](preprocess/README.md)
- [知识抽取](extractor_v1/README_ANCHOR_EXTRACTION.md)
- [GraphRAG系统](rag/README.md)
- [项目重组说明](REORGANIZATION.md)

---

## 👥 贡献指南

### 开发规范

1. **代码风格**: PEP 8
2. **类型注解**: 强制使用Type Hints
3. **文档字符串**: Google风格
4. **测试覆盖**: 核心模块>80%

### 提交流程

1. Fork项目
2. 创建Feature分支
3. 编写测试用例
4. 提交Pull Request
5. 代码Review

---

## 📄 License

本项目采用 MIT License

---

## 📧 联系方式

- **项目维护**: LUK-jiao
- **GitHub**: https://github.com/LUK-jiao/football_knowledge_crawler
- **问题反馈**: 通过GitHub Issues

---

**最后更新**: 2026年2月26日
**文档版本**: v1.0
**系统版本**: Production-ready
