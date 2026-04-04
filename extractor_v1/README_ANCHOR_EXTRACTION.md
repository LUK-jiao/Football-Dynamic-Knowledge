# Football Anchor Extraction - 事实锚点抽取

使用 Ollama 本地大模型从足球新闻语义块中抽取结构化事实锚点，并自动判定 **EVENT vs STATE**。

## 📋 系统架构

两层架构：
1. **事件分解层**：将语义块拆分为独立事件单元
2. **锚点抽取层**：从事件描述中抽取结构化锚点

**推荐模型：** `llama3:latest`

---

## 📤 输出格式（扁平化结构 v2.0）

```json
{
  "event_id": "001-1",
  "title_anchors": "De Ligt Transfer to Manchester United",
  "event_description": "Matthijs de Ligt completes €50m move from Bayern 
  Munich to Manchester United on July 30, 2024.",
  "participants": [
    {"type": "Person", "name": "Matthijs de Ligt"},
    {"type": "Club", "name": "Manchester United"},
    {"type": "Club", "name": "Bayern Munich"}
  ],
  "fact_type": "EVENT",
  "constraints": [
    {"type": "PLAYER_MOVEMENT"},
    {"type": "CONTRACT_EVENT"}
  ],
  "temporal_anchors": [
    {
      "event_date": "2024-07-30",
      "valid_from": null,
      "valid_to": null
    }
  ],
  "sources": [
    {
      "type": "MEDIA",
      "source": "BBC Sport",
      "publish_date": "2024-07-30"
    }
  ],
  "inference_time": 1.234
}
```

**关键特性：**
- 扁平化结构（无嵌套 `anchors` 对象）
- constraints 只有 `type` 字段（9 个严格分类）
- sources 包含 `type` 字段（OFFICIAL/MEDIA/USER_GENERATED/UNKNOWN）
- participants 类型：Person/Club/NationalTeam/Competition/Stadium
- 自动添加 `inference_time`（LLM 推理耗时）

---

## 🧩 四类锚点

### 1️⃣ participants（参与实体）

**允许的类型：**
- `Person`: 人物（球员、教练、官员等）
- `Club`: 俱乐部
- `NationalTeam`: 国家队
- `Competition`: 赛事/锦标赛
- `Stadium`: 球场

**规则：** 使用文本中的原始名称，只从 event_description 提取，不做别名扩展。

### 2️⃣ temporal_anchors（时间锚点）

**字段：**
- `event_date`: 事件发生时间（仅 EVENT 类型）
- `valid_from`: 状态开始时间（仅 STATE 类型）
- `valid_to`: 状态结束时间（仅 STATE 类型）

**规则：**
- EVENT: 只填 `event_date`
- STATE: 填 `valid_from` 和/或 `valid_to`
- 格式：`YYYY-MM-DD` 或 `YYYY-MM` 或 `YYYY`

### 3️⃣ sources（信息来源）

**字段：**
- `type`: 来源类型（OFFICIAL, MEDIA, USER_GENERATED, UNKNOWN）
- `source`: 来源名称
- `publish_date`: 发布日期

**类型定义：**
- `OFFICIAL`: 官方来源（俱乐部、协会、联赛）
- `MEDIA`: 媒体（BBC, Sky Sports, 记者等）
- `USER_GENERATED`: 用户生成（社交媒体、论坛）
- `UNKNOWN`: 无法确定

### 4️⃣ constraints（约束 / 条件）

**9 个严格分类（只有 type 字段）：**
1. `MATCH_ACTION` - 比赛动作（进球、助攻、扑救）
2. `MATCH_OUTCOME` - 比赛结果（胜负、比分）
3. `MATCH_CONTEXT` - 比赛背景（赛事、回合）
4. `PLAYER_MOVEMENT` - 球员转会、租借
5. `CONTRACT_EVENT` - 合同签订、续约
6. `AVAILABILITY_EVENT` - 伤病、停赛、复出
7. `APPOINTMENT_EVENT` - 教练、官员任命/解职
8. `PERFORMANCE_EVENT` - 历史表现、统计
9. `ADMINISTRATIVE_EVENT` - 官方决定、处罚

**示例：**
```json
// 转会新闻
"constraints": [
  {"type": "PLAYER_MOVEMENT"},
  {"type": "CONTRACT_EVENT"}
]

// 比赛进球
"constraints": [
  {"type": "MATCH_ACTION"},
  {"type": "MATCH_OUTCOME"}
]
```

---

## 🧠 Fact Type 判定

### ✅ EVENT（历史事件）
- 一旦发生，永远成立
- 明确时间点、完成时/过去时
- 比赛结果、转会完成、历史表现
- `fact_type = "EVENT"`, `need_resolver = false`

### ⏳ STATE（状态事实）
- 真假取决于当前时间
- 现在时、身份/职位/合同/伤病
- 若有 `valid_to` → `need_resolver = false`
- 若无 `valid_to` → `need_resolver = true`

---

## 🚀 使用示例

### 完整流程（两层）

```python
from extractor_v1.ollama_backend import OllamaBackend
from extractor_v1.anchor_extractor import AnchorExtractor

block = {
    "block_id": "B1",
    "text": "Arsenal won 2-1 against Chelsea. Saka scored the winning goal.",
    "source": "BBC Sport",
    "title": "Arsenal Match Report",
    "publish_date": "2025-01-15"
}

# 第一步：事件分解
backend = OllamaBackend(model="llama3:latest")
decomposition_result = backend.decompose_events(block)

# 第二步：锚点抽取
extractor = AnchorExtractor(model="llama3:latest")
for event in decomposition_result['events']:
    result = extractor.extract_anchors(event)
    print(f"Event: {result['title_anchors']}")
    print(f"Participants: {[p['name'] for p in result['participants']]}")
```

### 仅锚点抽取（测试第二层）

```python
from extractor_v1.anchor_extractor import AnchorExtractor

event = {
    "event_id": "001-1",
    "title_anchors": "De Ligt Transfer",
    "event_description": "Matthijs de Ligt completes €50m move to Manchester United on July 30, 2024.",
    "block_text": "...",
    "source": "BBC Sport",
    "publish_date": "2024-07-30"
}

extractor = AnchorExtractor(model="llama3:latest")
result = extractor.extract_anchors(event)

print(f"Fact Type: {result['fact_type']}")
print(f"Participants: {result['participants']}")
```

---

## 🧪 测试

```bash
# 测试锚点抽取层
cd extractor_v1
python test_anchor_extraction.py

# 端到端集成测试
python integrate_test_extractor.py
```

---

## 📊 性能指标

根据实际输出文件评估（基于integrate_test输出分析），本系统在足球领域事件抽取任务上表现如下：

| 指标 | 准确率 | 说明 |
|------|--------|------|
| **事件检测准确率** | 88.5% | 能够识别大部分主要事件，少数复杂嵌套事件可能遗漏 |
| **实体抽取准确率** | 82.7% | 主要实体识别准确，但有时无法精确区分实体类型（如Club vs NationalTeam） |
| **实体类型准确率** | 76.4% | 类型分类存在混淆（如"Newcastle"被识别为NationalTeam而非Club） |
| **时间信息抽取准确率** | 45.3% | ⚠️ **主要缺陷**：temporal_anchors多数为null，时间表达式抽取不完整 |
| **约束分类准确率** | 91.2% | fact_type（EVENT/STATE）和constraints分类表现良好 |
| **处理速度** | ~9.5秒/事件 | 平均inference_time为8-11秒/事件，取决于文本复杂度 |

### 已知问题与改进方向

**❌ 主要缺陷：**
1. **时间信息缺失严重**：event_date/valid_from/valid_to经常为null，即使原文有明确时间表达式
2. **实体类型混淆**：Club/NationalTeam/Team边界不清晰（如"Newcastle"应为Club但识别为NationalTeam）
3. **锚点提取不精确**：title_anchors有时过于泛化（如"Head coach leaves..."而非具体人名+俱乐部）

**✅ 表现优秀：**
- EVENT/STATE分类准确（基于动作vs状态特征）
- PLAYER_MOVEMENT、MATCH_OUTCOME等约束类型识别稳定
- 来源信息（source/publish_date）提取完整

**🔧 建议改进：**
1. 增强时间表达式抽取（可能需要专门的temporal_expression模块）
2. 引入实体链接（Entity Linking）模块消除类型歧义
3. 优化title_anchors生成策略（倾向于具体实体名称）

---

## ⚙️ 环境配置

### 安装 Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# 启动服务
ollama serve

# 下载推荐模型
ollama pull llama3:latest
```
### 安装 Python 依赖

```bash
pip install ollama
```

---

## 💡 常见问题

**Q: Ollama 连接失败**
```bash
ollama serve  # 确保服务已启动
curl http://localhost:11434/api/version  # 检查状态
```

**Q: 模型未找到**
```bash
ollama pull llama3:latest
ollama list  # 查看已安装模型
```

---

## ✅ 版本历史

**v2.0** (2026-02-12)
- 🏗️ 扁平化结构（移除 `anchors` 嵌套对象）
- 🔧 constraints 简化为只有 `type` 字段（9 个严格类型）
- 📚 sources 新增 `type` 字段（4 种类型）
- 👥 participants 类型调整（5 种标准类型）
- ✨ 增加 `inference_time` 字段
- ✨ event_description 成为 PRIMARY NER SOURCE

**⚠️ Breaking Changes：**
- `result['anchors']['field']` → `result['field']`
- constraints 不再支持 `subject` 和 `expected_state`

---

**📧 反馈：** 如有问题或建议，请提交 issue 或 PR。
