# Football Event Taxonomy - 设计文档

## 📚 总览

本文档详细说明了足球新闻事件分类体系（Event Taxonomy）的设计原则、分类标准和使用方法。

---

## 🎯 设计目标

### 核心原则

1. **事件独立性** - 每个事件类型必须能独立识别，不依赖其他上下文
2. **知识图谱友好** - 每个事件可直接映射为KG中的节点或关系
3. **互斥性** - 顶层事件类型在语义上互斥（不重叠）
4. **可扩展性** - 支持后续添加新的事件类型

### 应用场景

- ✅ 事实抽取（Fact Extraction）
- ✅ 知识图谱构建（Knowledge Graph Construction）
- ✅ 事件时间线生成（Event Timeline）
- ✅ 语义搜索（Semantic Search）

---

## 🏗️ 分类体系

### 层级结构

```
顶层（Top Level）
├── 核心比赛事件（Core Match Events）
│   ├── MATCH_RESULT - 比赛结果
│   ├── GOAL - 进球
│   ├── ASSIST - 助攻
│   ├── PENALTY_SHOOTOUT - 点球大战
│   ├── PENALTY_AWARD - 点球判罚
│   ├── OWN_GOAL - 乌龙球
│   ├── SAVE - 扑救
│   └── MISS - 射失
│
├── 纪律事件（Disciplinary Events）
│   ├── YELLOW_CARD - 黄牌
│   ├── RED_CARD - 红牌
│   └── VAR_DECISION - VAR判罚
│
├── 球队事件（Team Events）
│   ├── SUBSTITUTION - 换人
│   ├── TACTICAL_CHANGE - 战术调整
│   └── FORMATION_CHANGE - 阵型变化
│
├── 球员事件（Player Events）
│   ├── INJURY - 伤病
│   ├── RETURN_FROM_INJURY - 伤愈复出
│   ├── DEBUT - 首秀
│   └── MILESTONE - 里程碑
│
├── 赛事事件（Competition Events）
│   ├── FIXTURE - 赛程安排
│   ├── QUALIFICATION - 晋级
│   ├── ELIMINATION - 淘汰
│   └── DRAW_CEREMONY - 抽签
│
├── 转会事件（Transfer & Contract）
│   ├── TRANSFER - 转会
│   ├── CONTRACT_EXTENSION - 续约
│   └── LOAN - 租借
│
├── 引语事件（Quotes & Statements）
│   ├── MANAGER_QUOTE - 主帅发言
│   ├── PLAYER_QUOTE - 球员发言
│   └── OFFICIAL_STATEMENT - 官方声明
│
├── 统计事件（Statistics & Records）
│   ├── STATISTIC - 统计数据
│   ├── RECORD_BREAK - 破纪录
│   └── HISTORICAL_COMPARISON - 历史对比
│
└── 元事件（Meta Events）
    ├── MATCH_PREVIEW - 赛前预测
    ├── MATCH_REVIEW - 赛后总结
    ├── CONTEXT_BACKGROUND - 背景信息
    └── GENERAL_NARRATIVE - 一般叙述
```

---

## 🔍 事件类型详解

### 1. MATCH_RESULT（比赛结果）

**定义**：描述比赛最终胜负的事件

**典型句式**：
- "Arsenal won 3-2."
- "The match ended 1-1."
- "City advanced on penalties."

**触发特征**：
- 动词：won, lost, drew, beat, defeated
- 比分模式：`\d+-\d+`
- 特殊短语：on penalties, after extra time

**必需实体**：
- 主队（TEAM）
- 客队（TEAM）
- 比分（SCORE）
- 赛事（COMPETITION）

**KG映射**：
```cypher
(Team1)-[:DEFEATED {score: "3-2"}]->(Team2)
(Match)-[:RESULT {winner: Team1}]
```

---

### 2. GOAL（进球事件）

**定义**：描述进球动作和过程的事件

**典型句式**：
- "Haaland scored in the 45th minute."
- "Saka found the net from 25 yards."
- "The opener came from a corner."

**触发特征**：
- 动词：scored, netted, converted, struck
- 名词：goal, strike, finish, header
- 时间模式：`in the \d+th minute`

**必需实体**：
- 射手（PLAYER）
- 时间（TIME）
- 进球类型（GOAL_TYPE）

**KG映射**：
```cypher
(Player)-[:SCORED {minute: 45, type: "header"}]->(Goal)
(Goal)-[:IN_MATCH]->(Match)
```

**常见子类型**：
- Opening goal（开场球）
- Equaliser（扳平球）
- Winner（制胜球）
- Brace（梅开二度）
- Hat-trick（帽子戏法）

---

### 3. PENALTY_SHOOTOUT（点球大战）

**定义**：描述点球大战整体过程的事件

**典型句式**：
- "Arsenal won 5-4 on penalties."
- "A penalty shootout decided the tie."
- "Kepa saved the decisive spot-kick."

**触发特征**：
- 关键词：penalty shootout, spot-kicks
- 模式：`\d+-\d+ on penalties`

**必需实体**：
- 两队（TEAM, TEAM）
- 点球比分（SCORE）
- 关键球员（PLAYER）

**与其他事件的关系**：
- 可包含多个 SAVE 事件
- 可包含多个 MISS 事件
- 通常跟随 MATCH_RESULT

---

### 4. MANAGER_QUOTE（主帅发言）

**定义**：主教练的言论、评论或声明

**典型句式**：
- "Arteta said: 'We played well.'"
- "The manager admitted the team struggled."
- "Guardiola told reporters after the match..."

**触发特征**：
- 动词：said, told, admitted, praised
- 角色词：manager, boss, coach
- 引号模式：`: ["\']`

**必需实体**：
- 发言人（PERSON）
- 角色（ROLE: manager/coach）
- 引语内容（QUOTE）

**特殊处理**：
- 引语聚合器已在sentence_splitter处理
- 此处只需识别整个引语块的类型

**KG映射**：
```cypher
(Manager)-[:STATED {content: "quote"}]->(Statement)
(Statement)-[:ABOUT]->(Match)
```

---

### 5. FIXTURE（赛程安排）

**定义**：未来比赛的对阵和时间安排

**典型句式**：
- "Arsenal will face Chelsea next week."
- "The first leg is set for January 14."
- "City travel to Madrid on Tuesday."

**触发特征**：
- 动词：will face, will play, meet
- 时间词：next, scheduled for
- 地点：at home, away to

**必需实体**：
- 两队（TEAM, TEAM）
- 日期（DATE）
- 地点（VENUE）
- 赛事（COMPETITION）

**时态特征**：
- 必须是将来时态
- 与 MATCH_RESULT 互斥（一个描述未来，一个描述过去）

---

### 6. INJURY（伤病事件）

**定义**：球员受伤或伤病状态的事件

**典型句式**：
- "Kane picked up a hamstring injury."
- "The striker was ruled out for 3 weeks."
- "He limped off in the 30th minute."

**触发特征**：
- 动词：injured, suffered, ruled out
- 名词：injury, hamstring, ankle, knee
- 结果：limped off, carried off

**必需实体**：
- 球员（PLAYER）
- 伤病类型（INJURY_TYPE）
- 时长（DURATION）可选

**KG映射**：
```cypher
(Player)-[:SUFFERED {type: "hamstring", duration: "3 weeks"}]->(Injury)
```

---

### 7. MILESTONE（里程碑）

**定义**：球员达成特殊成就或纪录

**典型句式**：
- "This was his 100th appearance for Arsenal."
- "Ronaldo reached his 800th career goal."
- "The landmark victory came at Wembley."

**触发特征**：
- 数字模式：`\d+(th|st|nd|rd) (appearance|goal)`
- 关键词：milestone, landmark, century

**必需实体**：
- 球员（PLAYER）
- 数字（NUMBER）
- 类型（TYPE: goals/appearances/wins）

**常见类型**：
- 100th appearance
- 50th goal
- 500th win
- Career milestone

---

## 🔗 事件兼容性（Event Compatibility）

某些事件可以合并在同一个语义块中，因为它们在时间和因果上紧密相关。

### 兼容规则

```python
GOAL ↔ ASSIST      # 进球通常伴随助攻
GOAL ↔ MILESTONE   # 进球可能是里程碑
GOAL ↔ STATISTIC   # 进球 + 统计（"他的第10球"）

PENALTY_SHOOTOUT ↔ SAVE   # 点球大战中的扑救
PENALTY_SHOOTOUT ↔ MISS   # 点球大战中的射失

INJURY ↔ SUBSTITUTION     # 受伤导致换人

MANAGER_QUOTE ↔ MANAGER_QUOTE  # 同一人的多句引语
```

### 不兼容示例

```python
MATCH_RESULT ⚠️ FIXTURE    # 一个过去一个未来
GOAL ⚠️ RED_CARD           # 两个独立事件
INJURY ⚠️ GOAL             # 语义不相关
```

---

## 🎨 依附句识别（Dependency Markers）

某些句子不能独立成为事件，必须依附于前文的锚点句。

### 指代代词（Anaphoric Pronouns）

**触发依附**：
- This, That, It, They, He, She
- His, Her, Their

**示例**：
```
[Anchor] Haaland scored in the 45th minute.
[Dependent] This was his 10th goal of the season.  ← "This" 指代前面的进球
```

### 时间延续词（Temporal Continuations）

**触发依附**：
- When, After, Before, As, While
- Following, Subsequently, Then, Later

**示例**：
```
[Anchor] Palace equalised late.
[Dependent] When it finally arrived, Guehi was there.  ← "When" 延续前句
```

### 阐述标记（Elaboration Markers）

**弱依附**（需结合其他特征）：
- 以定冠词开头（The）+ 缺少强动词
- Overall, In total, Altogether

**示例**：
```
[Anchor] Arsenal dominated possession.
[Dependent] The Gunners had 65% of the ball.  ← "The Gunners" 补充说明
```

---

## 🛠️ 使用示例

### Python API

```python
from semantic_blocker.event_taxonomy import (
    EventType, 
    EVENT_TRIGGERS,
    get_event_triggers,
    is_compatible_event
)

# 获取某个事件的触发器
goal_triggers = get_event_triggers(EventType.GOAL)
print(goal_triggers.verbs)  # {'scored', 'netted', ...}

# 检查句子是否包含触发词
sentence = "Haaland scored in the 45th minute"
if any(verb in sentence.lower() for verb in goal_triggers.verbs):
    print("This is a GOAL event!")

# 检查事件兼容性
compatible = is_compatible_event(EventType.GOAL, EventType.ASSIST)
print(compatible)  # True - 进球和助攻可以在同一块
```

### 实际分块示例

**输入句子**：
```python
sentences = [
    "Arsenal won 8-7 on penalties.",              # MATCH_RESULT
    "Two late goals made it 1-1.",                # GOAL (dependent on result)
    "The Gunners will face Chelsea next.",        # FIXTURE
    "Arteta said: 'We played well.'",             # MANAGER_QUOTE
    "The boss praised his team's attitude.",      # MANAGER_QUOTE (continuation)
]
```

**预期输出块**：
```python
[
    {
        "event_type": "MATCH_RESULT",
        "sentences": [
            "Arsenal won 8-7 on penalties.",
            "Two late goals made it 1-1."
        ],
        "confidence": 0.95
    },
    {
        "event_type": "FIXTURE",
        "sentences": ["The Gunners will face Chelsea next."],
        "confidence": 0.90
    },
    {
        "event_type": "MANAGER_QUOTE",
        "sentences": [
            "Arteta said: 'We played well.'",
            "The boss praised his team's attitude."
        ],
        "confidence": 0.88
    }
]
```

---

## 📈 置信度计算

每个事件检测都有一个置信度分数（0-1），基于以下因素：

### 高置信度触发器（0.9-1.0）

- 明确的事件动词 + 实体
- 多个触发特征同时出现
- 符合标准句式模式

**示例**：
```
"Haaland scored his 35th goal in the 78th minute."
→ Confidence: 0.95
  - verb: "scored" ✓
  - noun: "goal" ✓
  - time: "78th minute" ✓
  - entity: "Haaland" ✓
```

### 中等置信度（0.6-0.89）

- 单一触发特征
- 部分实体缺失
- 需要上下文推断

**示例**：
```
"The striker found the net."
→ Confidence: 0.75
  - verb: "found the net" ✓
  - entity: "striker" (generic) ⚠️
```

### 低置信度（<0.6）

- 模糊表达
- 多重解释可能
- 严重依赖上下文

**示例**：
```
"It was a great moment."
→ Confidence: 0.45
  - 缺少明确事件类型
  - 指代不明
```

---

## 🔄 扩展指南

### 添加新事件类型

1. 在 `EventType` 枚举中添加新类型
2. 在 `EVENT_TRIGGERS` 中定义触发器
3. 更新 `EVENT_COMPATIBILITY` 定义兼容关系
4. 编写单元测试验证

**示例：添加"转会"事件**

```python
# Step 1: 添加枚举
class EventType(Enum):
    ...
    TRANSFER = "transfer"

# Step 2: 定义触发器
EVENT_TRIGGERS[EventType.TRANSFER] = EventTrigger(
    verbs={'signed', 'joined', 'moved to', 'transferred'},
    keywords={'transfer', 'deal', 'fee', 'contract'},
    patterns=[r'\bsigned for\b', r'\btransfer.*\d+m\b'],
    entity_types={'PLAYER', 'TEAM', 'MONEY'}
)

# Step 3: 定义兼容性
EVENT_COMPATIBILITY[EventType.TRANSFER] = {
    EventType.CONTRACT_EXTENSION,
    EventType.OFFICIAL_STATEMENT
}
```

### 优化现有触发器

根据实际数据调整：
- 添加遗漏的触发词
- 删除误报的触发词
- 调整正则表达式模式
- 更新实体类型约束

---

## 📊 性能指标

### 评估维度

1. **召回率（Recall）** - 正确识别的事件比例
2. **准确率（Precision）** - 识别结果的正确比例
3. **事件完整性** - 事件块包含所有相关句子
4. **边界准确性** - 事件块边界划分正确

### 基准测试

在100篇足球新闻上的表现（目标）：
- Recall: >85%
- Precision: >90%
- F1-Score: >87%

---

## 🎯 总结

本事件分类体系提供了：

✅ **27种细粒度事件类型** - 覆盖足球新闻主要场景  
✅ **结构化触发器定义** - 易于维护和扩展  
✅ **事件兼容性规则** - 确保语义块的连贯性  
✅ **依附句识别机制** - 处理跨句指代  
✅ **知识图谱友好** - 直接支持KG构建  

这为事件驱动的语义分块提供了坚实的理论和工程基础。
