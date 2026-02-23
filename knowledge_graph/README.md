# Football Knowledge Graph - 知识图谱持久化层

## 📊 图谱结构设计

### 节点类型 (Node Types)

#### 1. Event (事件节点)
足球领域的核心事件，所有其他节点都围绕事件组织。

**属性:**
- `event_id` (唯一标识)
- `event_description` (事件描述)
- `fact_type` (事实类型: EVENT/RELATION/STATE)
- `title_anchors` (标题锚点)
- `event_date` (事件日期: Date)
- `valid_from` (有效期起始: Date)
- `valid_to` (有效期结束: Date)

**示例:**
```cypher
(:Event {
  event_id: "block_1-1",
  event_description: "Arsenal defeated Crystal Palace 8-7 on penalties",
  fact_type: "EVENT",
  event_date: date("2025-01-14")
})
```

---

#### 2. Entity (实体节点)
足球领域的参与者，包含5个子类型。

**子类型标签:**
- `Person` - 球员、教练、裁判等
- `Club` - 俱乐部
- `NationalTeam` - 国家队
- `Competition` - 赛事（英超、欧冠等）
- `Stadium` - 体育场

**属性:**
- `entity_id` (唯一标识，从name生成)
- `name` (实体名称)
- `type` (实体类型)

**示例:**
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

---

#### 3. Source (来源节点)
新闻来源，标识信息的可信度。

**属性:**
- `source_id` (唯一标识)
- `source` (来源名称)
- `type` (来源类型: OFFICIAL/MEDIA/USER_GENERATED/UNKNOWN)

**示例:**
```cypher
(:Source {
  source_id: "bbc_sport",
  source: "BBC Sport",
  type: "MEDIA"
})
```

---

#### 4. ConstraintAnchor (约束锚点)
事件的类型约束，用于分类和检索。

**类型 (9种):**
- `MATCH_ACTION` - 比赛行为（进球、助攻、红牌等）
- `MATCH_OUTCOME` - 比赛结果
- `MATCH_CONTEXT` - 比赛背景
- `PLAYER_MOVEMENT` - 球员转会
- `CONTRACT_EVENT` - 合同事件
- `AVAILABILITY_EVENT` - 可用性变化（伤病、停赛）
- `APPOINTMENT_EVENT` - 任命事件（教练上任）
- `PERFORMANCE_EVENT` - 表现评估
- `ADMINISTRATIVE_EVENT` - 管理事件

**属性:**
- `type` (约束类型，唯一)

**示例:**
```cypher
(:ConstraintAnchor {type: "MATCH_ACTION"})
(:ConstraintAnchor {type: "PLAYER_MOVEMENT"})
```

---

#### 5. TitleAnchor (标题锚点)
事件的标题描述，用于快速定位同一事件的不同报道。

**属性:**
- `title` (标题文本，唯一)

**示例:**
```cypher
(:TitleAnchor {
  title: "Arsenal vs Crystal Palace EFL Cup quarter-final"
})
```

---

### 关系类型 (Relationships)

#### 1. INVOLVES (事件-实体)
```cypher
(Event)-[:INVOLVES]->(Entity)
```
表示实体参与了该事件。

---

#### 2. REPORTED_BY (事件-来源)
```cypher
(Event)-[:REPORTED_BY]->(Source)
```
表示事件由该来源报道。

---

#### 3. CONSTRAINS (约束-事件)
```cypher
(ConstraintAnchor)-[:CONSTRAINS]->(Event)
```
表示事件属于该类型约束。

---

#### 4. HAS_TITLE_ANCHOR (事件-标题)
```cypher
(Event)-[:HAS_TITLE_ANCHOR]->(TitleAnchor)
```
表示事件关联到该标题。

---

## 🔧 使用方式

### 1. 初始化连接

```python
from knowledge_graph import Neo4jWriter

# 使用默认配置
with Neo4jWriter() as writer:
    writer.initialize_constraints()
```

**自定义配置:**
```python
writer = Neo4jWriter(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="your_password"
)
```

---

### 2. 写入单个事件

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
    "temporal_anchors": [
        {"event_date": "2025-01-14"}
    ],
    "sources": [
        {"source": "BBC Sport", "type": "MEDIA"}
    ],
    "constraints": [
        {"type": "MATCH_ACTION"}
    ]
}

with Neo4jWriter() as writer:
    writer.upsert_event(event_data)
```

---

### 3. 批量写入事件

```python
events = [event_data1, event_data2, event_data3]

with Neo4jWriter() as writer:
    writer.upsert_events(events)  # 高效批量写入
```

---

### 4. 查询事件完整视图

```python
with Neo4jWriter() as writer:
    # 查询单个事件及其所有关系
    result = writer.get_event_full_view("001")
    
    print(result['event'])        # 事件节点
    print(result['entities'])     # 相关实体
    print(result['sources'])      # 来源
    print(result['constraints'])  # 约束类型
    print(result['titles'])       # 标题锚点
```

---

### 5. 按实体查询事件

```python
# 查询某球员参与的所有事件
events = writer.get_entity_events("bukayo_saka")

for event in events:
    print(f"{event['event_id']}: {event['event_description']}")
```

---

### 6. 按约束类型查询

```python
# 查询所有转会事件
transfer_events = writer.get_events_by_anchor("PLAYER_MOVEMENT")

# 查询所有进球/助攻事件
match_actions = writer.get_events_by_anchor("MATCH_ACTION")
```

---

### 7. 按标题查询

```python
# 查询同一新闻主题的所有事件
events = writer.get_events_by_title_anchor("Arsenal vs Palace")
```

---

### 8. 时间范围查询

```python
# 查询某时间段内的事件
events = writer.get_events_by_time_range(
    start_date="2025-01-01",
    end_date="2025-01-31"
)
```

---

## 🚀 命令行工具

### 加载单个JSON文件
```bash
python knowledge_graph/load_to_neo4j.py extractor_v1/output/result.json
```

### 批量加载目录
```bash
python knowledge_graph/load_to_neo4j.py extractor_v1/output/
```

---

## 📈 Neo4j Browser 可视化

### 启动Neo4j Browser
```bash
# 访问浏览器界面
http://localhost:7474
```

### 常用Cypher查询

#### 查看所有节点类型统计
```cypher
MATCH (n)
RETURN labels(n), count(*) as count
ORDER BY count DESC
```

#### 查看某球员的所有关联
```cypher
MATCH (e:Entity {name: "Bukayo Saka"})-[r]-(other)
RETURN e, r, other
```

#### 查看某事件的完整关系网
```cypher
MATCH (event:Event {event_id: "001"})
OPTIONAL MATCH (event)-[r1:INVOLVES]->(entity:Entity)
OPTIONAL MATCH (event)-[r2:REPORTED_BY]->(source:Source)
OPTIONAL MATCH (constraint:ConstraintAnchor)-[r3:CONSTRAINS]->(event)
OPTIONAL MATCH (event)-[r4:HAS_TITLE_ANCHOR]->(title:TitleAnchor)
RETURN event, r1, entity, r2, source, r3, constraint, r4, title
```

#### 查找转会新闻
```cypher
MATCH (c:ConstraintAnchor {type: "PLAYER_MOVEMENT"})-[:CONSTRAINS]->(e:Event)
MATCH (e)-[:INVOLVES]->(entity:Entity)
RETURN e.event_description, collect(entity.name) as players
LIMIT 10
```

#### 查找某俱乐部的所有事件
```cypher
MATCH (club:Entity:Club {name: "Arsenal"})<-[:INVOLVES]-(e:Event)
RETURN e.event_date, e.event_description
ORDER BY e.event_date DESC
LIMIT 20
```

#### 按来源统计事件数量
```cypher
MATCH (s:Source)<-[:REPORTED_BY]-(e:Event)
RETURN s.source, s.type, count(e) as event_count
ORDER BY event_count DESC
```

---

## 📊 完整流程示例

### 从抽取到入库的完整流程

```python
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig
from extractor_v1.anchor_extractor import AnchorExtractor
from knowledge_graph import Neo4jWriter

# 1. 文本预处理
raw_text = "Arsenal defeated Crystal Palace 8-7 on penalties..."
splitter = SentenceSplitter()
sentences = splitter.split(raw_text)

# 2. 语义分块
chunker = SemanticChunker(...)
chunks = chunker.chunk(sentences)

# 3. 事件分解与锚点提取
extractor = AnchorExtractor()
events = []
for chunk in chunks:
    result = extractor.extract_anchors(chunk)
    events.append(result)

# 4. 写入知识图谱
with Neo4jWriter() as writer:
    writer.initialize_constraints()
    writer.upsert_events(events)
    
    # 查询验证
    stats = writer.get_event_full_view(events[0]['event_id'])
    print(f"写入成功: {len(stats['entities'])} 个实体")
```

---

## 🎯 核心特性

### ✅ 幂等性保证
所有写入操作使用 `MERGE`，重复执行不会创建重复节点。

### ✅ 参数化查询
所有Cypher查询使用参数化，防止注入攻击。

### ✅ 事务管理
批量操作在单个事务中执行，保证数据一致性。

### ✅ 自动ID生成
- `entity_id`: 从name自动生成 (小写+下划线)
- `source_id`: 从source自动生成
- 无需手动管理ID

### ✅ 灵活的日期处理
支持多种日期格式:
- `YYYY` (年)
- `YYYY-MM` (年月)
- `YYYY-MM-DD` (完整日期)

---

## 📁 项目结构

```
knowledge_graph/
├── __init__.py           # 包导出
├── config.py             # 配置管理
├── neo4j_writer.py       # 核心写入/查询类 (410行)
├── example_usage.py      # 使用示例
├── load_to_neo4j.py      # 命令行加载工具
└── README.md             # 本文档
```

---

## ⚙️ 环境配置

### 环境变量
```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
```

### Python依赖
```bash
pip install neo4j
```

### Neo4j启动
```bash
# Docker方式
docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5

# 或本地安装
neo4j start
```

---

## 🧪 测试

### 运行完整流程测试
```bash
PYTHONPATH=. python tests/integration_test_full_pipeline.py
```

### 运行示例代码
```bash
PYTHONPATH=. python knowledge_graph/example_usage.py
```

---

## 📝 数据格式说明

### 输入格式 (extractor_v1输出)
```json
{
  "event_id": "block_1-1",
  "event_description": "Arsenal won 8-7 on penalties",
  "fact_type": "EVENT",
  "title_anchors": "Arsenal vs Palace EFL Cup",
  "participants": [
    {"name": "Arsenal", "type": "Club"},
    {"name": "Bukayo Saka", "type": "Person"}
  ],
  "temporal_anchors": [
    {"event_date": "2025-01-14"}
  ],
  "sources": [
    {"source": "BBC Sport", "type": "MEDIA"}
  ],
  "constraints": [
    {"type": "MATCH_OUTCOME"}
  ]
}
```

### 图谱存储格式
输入的扁平化JSON自动转换为图结构，节点和关系按上述schema存储。

---

## 🔍 高级用法

### 自定义Cypher查询
```python
with Neo4jWriter() as writer:
    with writer.driver.session() as session:
        result = session.run("""
            MATCH (e:Event)-[:INVOLVES]->(p:Entity:Person)
            WHERE e.event_date >= date($start)
            RETURN p.name, count(e) as appearances
            ORDER BY appearances DESC
            LIMIT 10
        """, start="2025-01-01")
        
        for record in result:
            print(f"{record['name']}: {record['appearances']} 次出场")
```

---

## 💡 最佳实践

1. **始终使用上下文管理器** - 自动管理连接关闭
2. **批量写入优先** - `upsert_events()` 比循环调用 `upsert_event()` 快10倍+
3. **定期备份** - Neo4j提供 `neo4j-admin dump` 命令
4. **监控性能** - 使用 `PROFILE` 关键字分析Cypher查询
5. **合理使用索引** - 已为所有唯一属性创建约束索引

---

## 📚 参考资源

- [Neo4j Cypher手册](https://neo4j.com/docs/cypher-manual/)
- [Neo4j Python驱动文档](https://neo4j.com/docs/python-manual/)
- [项目完整文档](../README.md)
