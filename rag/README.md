# GraphRAG System for Football Knowledge Graph

## 🎯 系统架构

基于Neo4j的Event-Centric足球知识图谱RAG系统，提供**时间感知**、**约束引导**、**可解释**的问答能力。

### 核心模块

```
rag/
├── query_analyzer.py      # 查询分析器 (LLM + 规则)
├── graph_retriever.py     # 图检索器 (参数化Cypher)
├── context_builder.py     # 上下文构建器 (格式化)
├── rag_engine.py          # RAG引擎 (编排器)
├── utils.py               # 工具函数
├── example_usage.py       # 使用示例
└── test_graphrag.py       # 单元测试
```

---

## 📦 四大核心组件

### 1️⃣ QueryAnalyzer - 查询分析器

**功能:** 将自然语言问题解析为结构化查询约束。

**解析策略:**
- **主策略:** LLM解析（Ollama）
- **备选策略:** 规则解析（关键词匹配）
- **容错:** 自动重试 + Fallback

**输出格式:**
```python
{
    "entities": ["Arsenal", "Bukayo Saka"],
    "time_range": {
        "start": "2025-01-01",
        "end": "2025-01-31"
    },
    "constraint_types": ["MATCH_ACTION", "MATCH_OUTCOME"],
    "intent": "fact",  # fact / summary / analysis
    "limit": 20
}
```

**识别能力:**
- ✅ 人名、俱乐部名
- ✅ 时间表达（"2025年"、"最近"、"上个月"）
- ✅ 事件类型（"进球"→MATCH_ACTION，"转会"→PLAYER_MOVEMENT）
- ✅ 查询意图（"总结"→summary，"为什么"→analysis）

**使用示例:**
```python
from rag import QueryAnalyzer

analyzer = QueryAnalyzer(model="llama3:latest")
result = analyzer.parse("Arsenal在2025年1月进了多少球？")

print(result['entities'])        # ['Arsenal']
print(result['time_range'])      # {'start': '2025-01-01', 'end': '2025-01-31'}
print(result['constraint_types']) # ['MATCH_ACTION']
print(result['intent'])          # 'fact'
```

---

### 2️⃣ GraphRetriever - 图检索器

**功能:** 根据结构化约束从Neo4j检索事件。

**检索维度:**
1. **实体过滤** - 按球员/俱乐部名称
2. **时间过滤** - 按事件日期范围
3. **约束过滤** - 按事件类型（9种）
4. **意图扩展** - analysis模式自动扩展子图

**查询特性:**
- ✅ 参数化Cypher（防注入）
- ✅ 完整事件上下文（实体+来源+约束+标题）
- ✅ 时间倒序排列
- ✅ Multi-hop扩展（相同标题锚点）

**返回格式:**
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

**使用示例:**
```python
from rag import GraphRetriever
from knowledge_graph import Neo4jWriter

writer = Neo4jWriter()
retriever = GraphRetriever(writer)

parsed_query = {
    "entities": ["Arsenal"],
    "time_range": {"start": "2025-01-01", "end": "2025-01-31"},
    "constraint_types": ["MATCH_ACTION"],
    "intent": "fact",
    "limit": 20
}

events = retriever.retrieve(parsed_query)
print(f"Retrieved {len(events)} events")
```

---

### 3️⃣ ContextBuilder - 上下文构建器

**功能:** 将事件列表格式化为LLM可读的文本。

**格式化策略:**
- **fact模式:** 标准列表（时间倒序）
- **summary模式:** 按约束类型分组
- **analysis模式:** 时间线排序（顺序）

**处理流程:**
1. 去重（event_id）
2. 排序（按日期）
3. 限制数量（默认30个）
4. 合并同日期事件
5. 格式化为文本

**输出格式:**
```
[Event 1]
Event ID: block_1-1
Date: 2025-01-14
Type: EVENT (MATCH_OUTCOME)
Title: Arsenal vs Palace EFL Cup
Description: Arsenal defeated Crystal Palace 8-7 on penalties
Entities: Arsenal, Crystal Palace
Source: BBC Sport

[Event 2]
...
```

**使用示例:**
```python
from rag import ContextBuilder

builder = ContextBuilder(max_events=30)

# 标准模式
context = builder.build(events)

# 总结模式（按类型分组）
summary_context = builder.build_summary_context(events)

# 分析模式（时间线）
analysis_context = builder.build_analysis_context(events)
```

---

### 4️⃣ GraphRAG - RAG引擎

**功能:** 完整RAG流程编排。

**执行流程:**
```
用户问题
    ↓
QueryAnalyzer (解析)
    ↓
GraphRetriever (检索)
    ↓
ContextBuilder (构建)
    ↓
LLM (生成答案)
    ↓
结构化响应
```

**返回格式:**
```python
{
    "parsed_query": {...},        # 解析结果
    "retrieved_events": [...],    # 检索的事件
    "answer": "..."               # 生成的答案
}
```

**使用示例:**
```python
from rag import QueryAnalyzer, GraphRetriever, ContextBuilder, GraphRAG
from knowledge_graph import Neo4jWriter
from extractor_v1.ollama_backend import OllamaBackend

# 初始化组件
analyzer = QueryAnalyzer(model="llama3:latest")
writer = Neo4jWriter()
retriever = GraphRetriever(writer)
builder = ContextBuilder()
llm = OllamaBackend(model="llama3:latest")

# 创建RAG引擎
rag = GraphRAG(analyzer, retriever, builder, llm)

# 提问
response = rag.answer("Arsenal在2025年1月的比赛结果如何？")

print(response['answer'])
print(f"基于 {len(response['retrieved_events'])} 个事件")
```

---

## 🚀 快速开始

### 基本使用

```python
from rag import QueryAnalyzer, GraphRetriever, ContextBuilder, GraphRAG
from knowledge_graph import Neo4jWriter
from extractor_v1.ollama_backend import OllamaBackend

# 初始化
analyzer = QueryAnalyzer()
writer = Neo4jWriter()
retriever = GraphRetriever(writer)
builder = ContextBuilder()
llm = OllamaBackend(model="llama3:latest")

rag = GraphRAG(analyzer, retriever, builder, llm)

# 单次问答
response = rag.answer("Bukayo Saka最近有什么表现？")
print(response['answer'])

# 批量问答
queries = ["Arsenal的比赛结果", "转会新闻", "球员伤病情况"]
responses = rag.batch_answer(queries)

# 交互模式
rag.interactive_mode()
```

---

## 📊 三种查询意图

### 1. Fact Query (事实查询)

**特征:** 询问具体事件

**示例:**
- "Arsenal在2025年1月14日的比赛结果是什么？"
- "Bukayo Saka进了多少球？"

**处理:**
- 检索精确匹配事件
- 返回事实性答案
- 引用event_id

---

### 2. Summary Query (总结查询)

**特征:** "总结"、"表现如何"、"状态"

**示例:**
- "总结一下Arsenal在2025年1月的表现"
- "Crystal Palace最近的比赛情况怎么样？"

**处理:**
- 检索更多事件（limit=50）
- 按类型分组
- 提供统计和趋势

---

### 3. Analysis Query (分析查询)

**特征:** "为什么"、"影响"、"原因"

**示例:**
- "为什么Thomas Frank被Tottenham解雇？"
- "分析Bukayo Saka对Arsenal的影响"

**处理:**
- 扩展子图（相关事件）
- 时间线排序
- 深度分析
- 因果推理

---

## 🧪 测试

### 运行完整测试

```bash
PYTHONPATH=. python rag/test_graphrag.py
```

**测试覆盖:**
1. QueryAnalyzer - 3种意图识别
2. GraphRetriever - 多维度检索
3. ContextBuilder - 3种格式化模式
4. GraphRAG - 端到端流程
5. 具体场景 - 进球、比赛、转会

---

## 📋 使用示例

### 示例1: 简单问答

```bash
PYTHONPATH=. python rag/example_usage.py --mode simple
```

### 示例2: 批量查询

```bash
PYTHONPATH=. python rag/example_usage.py --mode batch
```

### 示例3: 交互模式

```bash
PYTHONPATH=. python rag/example_usage.py --mode interactive
```

### 示例4: 自定义检索

```bash
PYTHONPATH=. python rag/example_usage.py --mode custom
```

### 示例5: 实体聚焦

```bash
PYTHONPATH=. python rag/example_usage.py --mode entity
```

---

## 🎓 系统特性

### ✅ Event-Centric (事件中心)

所有信息围绕事件节点组织，天然支持时序推理。

### ✅ Temporal-Aware (时间感知)

- 事件按时间排序
- 支持时间范围过滤
- 时间线分析

### ✅ Constraint-Guided (约束引导)

- 9种事件类型约束
- 精确过滤
- 类型统计

### ✅ Explainable (可解释)

- 返回完整检索过程
- 引用event_id
- 显示数据来源

---

## 🔧 配置

### Neo4j连接

```python
writer = Neo4jWriter(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="your_password"
)
```

### LLM模型

```python
analyzer = QueryAnalyzer(model="llama3:latest")
llm = OllamaBackend(model="llama3:latest")
```

### 上下文限制

```python
builder = ContextBuilder(max_events=30)  # 最多30个事件
```

---

## 📈 性能优化

### 1. 参数化查询
所有Cypher查询使用参数，避免SQL注入和提升缓存命中率。

### 2. 批量检索
一次查询获取完整事件上下文（实体+来源+约束+标题）。

### 3. 智能限制
- fact查询: 20个事件
- summary/analysis: 50个事件

### 4. 子图扩展
analysis模式自动扩展相关事件（相同标题锚点）。

---

## 🛡️ 错误处理

### QueryAnalyzer
- LLM失败 → 自动重试1次
- 再次失败 → Fallback到规则解析
- JSON解析错误 → 返回空结构

### GraphRetriever
- 参数化查询防注入
- 空结果返回空列表

### ContextBuilder
- 空事件返回 "No relevant events found."
- 自动去重和限制数量

---

## 📚 API参考

### QueryAnalyzer.parse()
```python
def parse(query: str) -> Dict[str, Any]
```

### GraphRetriever.retrieve()
```python
def retrieve(parsed_query: Dict[str, Any]) -> List[Dict[str, Any]]
```

### ContextBuilder.build()
```python
def build(events: List[Dict[str, Any]]) -> str
```

### GraphRAG.answer()
```python
def answer(query: str, return_context: bool = False) -> Dict[str, Any]
```

---

## 🎯 适用场景

### 本科毕设
- **完整系统架构**
- **可解释性强**
- **模块化设计**

### 论文实验
- **支持多种查询类型**
- **可量化指标**
- **完整测试覆盖**

### 实际应用
- **足球新闻问答**
- **球员数据查询**
- **赛事分析**

---

## 🔗 依赖

```python
neo4j              # Neo4j Python驱动
ollama             # LLM后端
knowledge_graph    # 图谱持久化层
extractor_v1       # 事件抽取层
```

---

## 📄 许可

本项目为学术研究项目，遵循MIT许可证。
