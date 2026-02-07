# Football Anchor Extraction - 事实锚点抽取

使用 Ollama 本地大模型从足球新闻语义块中抽取结构化事实锚点，并自动判定 **EVENT vs STATE**。

## 📋 总体目标

你是一个足球领域事实抽取与语义锚点识别专家 Agent。

从单条新闻语义块中，抽取结构化"事实锚点（anchors）"，并准确判定该事实是 **EVENT（历史事件）** 还是 **STATE（状态事实）**。

**质量优先级：** 正确性 > 一致性 > 完整性 > 覆盖率

**核心原则：** 宁可少抽、保守，也不要编造或过度推断。

---

## 📁 文件结构

```
extractor_v1/
├── ollama_backend.py            # Ollama 后端（Prompt + LLM 调用）
├── anchor_extractor.py          # 业务调用层（纯透传）
├── test_anchor_extraction.py    # 综合测试套件
├── example_usage.py             # 使用示例
├── __init__.py                  # Python 包初始化
└── README_ANCHOR_EXTRACTION.md  # 本文档
```

---

## 📥 输入格式

```json
{
  "block_id": "001",
  "text": "De Ligt has agreed to join Manchester United from Bayern Munich on 1 September 2025.",
  "source": "BBC",
  "publish_date": "2025-08-23"
}
```

| 字段 | 说明 |
|------|------|
| `block_id` | 语义块唯一 ID（不可修改） |
| `text` | 原始文本（唯一事实来源） |
| `source` | 新闻来源 |
| `publish_date` | 发布日期（⚠️ **不是事件时间**） |

---

## 📤 输出格式

```json
{
  "block_id": "001",
  "text": "De Ligt has agreed to join Manchester United...",
  "source": "BBC",
  "publish_date": "2025-08-23",
  "anchors": {
    "participants": [
      {"type": "Player", "name": "De Ligt"},
      {"type": "Club", "name": "Manchester United"},
      {"type": "Club", "name": "Bayern Munich"}
    ],
    "temporal_anchors": [
      {
        "event_date": "2025-09-01",
        "valid_from": "2025-09-01",
        "valid_to": "2025-09-01"
      }
    ],
    "sources": [
      {"name": "BBC", "type": "Media"}
    ],
    "constraints": [
      {
        "type": "TRANSFER_STATUS",
        "subject": "De Ligt",
        "expected_state": "transfer_possible"
      }
    ]
  },
  "fact_type": "EVENT",
  "need_resolver": false
}
```

---

## 🧩 四类锚点（Anchors）

### 1️⃣ participants（参与实体）

只抽取"客观存在、可唯一指代"的实体。

**允许的类型：**
- `Player`: 球员
- `Club`: 俱乐部
- `Coach`: 教练
- `Team`: 国家队
- `Stadium`: 球场
- `Tournament`: 赛事
- `Referee`: 裁判
- `Other`: 其他

**规则：**
- ✅ 使用文本中出现的**原始名称**
- ❌ 不做别名扩展、不查外部知识
- ❌ 不确定时宁可不抽

**示例：**
```json
{"type": "Player", "name": "De Ligt"}
{"type": "Club", "name": "Manchester United"}
```

---

### 2️⃣ temporal_anchors（时间锚点）

表达事件或状态在时间轴上的定位。

**字段说明：**
- `event_date`: 文本直接指向的事件时间
- `valid_from`: 有效开始日期
- `valid_to`: 有效结束日期

**规则：**
- ✅ 若文本中出现明确时间点（`on` / `in` / `at`），必须抽取
- ✅ 统一输出为 ISO-8601（`YYYY-MM-DD`）
- ❌ **不要把 publish_date 当作事件时间**
- EVENT：通常 `event_date = valid_from = valid_to`
- STATE：若文本未给结束时间，可只给 `valid_from`

**示例：**
```json
{
  "event_date": "2025-09-01",
  "valid_from": "2025-09-01",
  "valid_to": "2025-09-01"
}
```

---

### 3️⃣ sources（信息来源）

**规则：**
- 默认从输入的 `source` 字段生成
- 类型：`Media`, `Official`, `Social`, `Other`

**示例：**
```json
{"name": "BBC", "type": "Media"}
```

---

### 4️⃣ constraints（约束 / 条件）

抽象语义约束，不是实体。

**常见约束类型：**

| 类型 | 可能的状态值 |
|------|-------------|
| `TRANSFER_STATUS` | `transfer_possible`, `transfer_completed`, `transfer_rumored`, `transfer_rejected` |
| `CONTRACT_STATUS` | `contract_active`, `contract_expired`, `contract_extended` |
| `INJURY_STATUS` | `injured`, `recovering`, `fit` |
| `ROLE_STATUS` | `role_active`, `role_changed` |
| `MATCH_STATUS` | `match_scheduled`, `match_completed`, `match_postponed`, `match_cancelled` |
| `SUSPENSION_STATUS` | `suspended`, `available` |

**规则：**
- 只在文本**明确表达**某种状态/承诺/限制时才生成
- `subject` 必须来自 `participants`
- `expected_state` 必须是**抽象语义**（不是自然语言句子）

**示例：**
```json
{
  "type": "TRANSFER_STATUS",
  "subject": "De Ligt",
  "expected_state": "transfer_possible"
}
```

---

## 🧠 Fact Type 判定（极其重要）

### ✅ EVENT（历史事件）

**定义：** 一旦发生，永远成立，**不依赖当前时间 now**

**典型特征（满足任一即可）：**
- 明确时间点（`on 1 September 2025`, `in 2021`）
- 完成时/过去时动词（`signed`, `agreed`, `won`, `scored`）
- 比赛结果、转会完成、历史表现

**判定：** `fact_type = "EVENT"` → `need_resolver = false`

**示例：**

```python
# 示例 1：转会完成
"De Ligt has agreed to join Manchester United on 1 September 2025."
→ EVENT, need_resolver = false

# 示例 2：历史进球
"Castellanos scored four goals against Real Madrid in 2023."
→ EVENT, need_resolver = false

# 示例 3：比赛结果
"Arsenal won 3-2 against Chelsea."
→ EVENT, need_resolver = false
```

---

### ⏳ STATE（状态事实）

**定义：** 在某个时间区间内成立，真假**取决于当前时间**

**典型特征：**
- 现在时（`is`, `remains`, `serves as`）
- 身份/职位/合同/伤病
- 隐含 "until something changes"

**判定：**
- `fact_type = "STATE"`
- 若已有 `valid_to` → `need_resolver = false`
- 若无 `valid_to` → `need_resolver = true`

**示例：**

```python
# 示例 1：教练身份（无结束时间）
"Amorim is the head coach of Manchester United."
→ STATE, need_resolver = true（需要推理任期）

# 示例 2：合同状态（有到期日）
"He signed a contract until 2028."
→ STATE, need_resolver = false（已有 valid_to）

# 示例 3：伤病状态（无恢复时间）
"Salah is currently injured."
→ STATE, need_resolver = true（需要推理恢复时间）
```

---

## ⚠️ 边界判断原则

| 表达 | 判定 |
|------|------|
| `has agreed to join` | **EVENT**（协议达成是事件） |
| `is under contract` | **STATE** |
| `will join next summer` | **EVENT**（未来已确定事件） |
| `could join` / `linked with` | ❌ **不构成事实**（谨慎，可能无 EVENT） |

---

## 🛑 禁止事项（Hard Constraints）

你绝对不能：

❌ 引入文本中不存在的实体  
❌ 使用外部知识补全事实  
❌ 推断隐含未明说的时间  
❌ 把推测性语言当作已发生事实  
❌ 不确定时不要编造，返回空数组 `[]`

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装 Ollama
# macOS/Linux: https://ollama.ai/download
curl -fsSL https://ollama.ai/install.sh | sh

# 启动 Ollama 服务
ollama serve

# 下载模型（在另一个终端）
ollama pull llama3.2:latest
```

### 2. 安装 Python 依赖

```bash
pip install ollama
```

### 3. 基本使用

```python
from extractor_v1.anchor_extractor import AnchorExtractor

# 准备输入 block
block = {
    "block_id": "B1",
    "source": "BBC Sport",
    "publish_date": "2025-01-15",
    "text": """
    Matthijs de Ligt completes €50m move from Bayern Munich to Manchester United.
    The defender signs a five-year deal until June 2029.
    """
}

# 初始化提取器
extractor = AnchorExtractor(model="llama3.2:latest")

# 提取事实锚点
result = extractor.extract_anchors(block)

print(f"Fact Type: {result['fact_type']}")
print(f"Need Resolver: {result['need_resolver']}")
print(result)
```

### 4. 批量处理

```python
blocks = [block1, block2, block3]
results = extractor.extract_anchors_batch(blocks)
```

---

## 🧪 测试

### 运行完整测试

```bash
cd extractor_v1
python test_anchor_extraction.py
```

### 运行特定测试

```bash
# 只测试 Ollama 连接
python test_anchor_extraction.py --test connection

# 测试 Backend 提取
python test_anchor_extraction.py --test backend

# 测试 AnchorExtractor
python test_anchor_extraction.py --test extractor

# 测试边界情况
python test_anchor_extraction.py --test edge
```

### 跳过 LLM 测试

```bash
python test_anchor_extraction.py --skip-llm
```

### 使用不同模型

```bash
python test_anchor_extraction.py --model mistral:latest
```

---

## 📊 测试场景

测试套件包含 6 个测试场景：

| 测试 ID | 场景 | Fact Type | Need Resolver |
|---------|------|-----------|---------------|
| `test_transfer_event` | 转会新闻（明确时间） | EVENT | false |
| `test_match_event` | 比赛结果 | EVENT | false |
| `test_coach_state` | 教练身份（无结束时间） | STATE | true |
| `test_contract_state` | 合同状态（有结束时间） | STATE | false |
| `test_injury_state` | 伤病状态（无结束时间） | STATE | true |
| `test_historical_event` | 历史进球 | EVENT | false |

---

## ⚙️ 配置

### 修改模型

```python
# 使用不同的 Ollama 模型
extractor = AnchorExtractor(model="mistral:latest")
# 或
extractor = AnchorExtractor(model="qwen:7b")
```

### 自定义 Ollama 服务地址

```python
extractor = AnchorExtractor(
    model="llama3.2:latest",
    host="http://your-server:11434"
)
```

### 调整 Prompt

在 `ollama_backend.py` 中直接修改：

```python
SYSTEM_PROMPT = """Your custom system prompt..."""

DEVELOPER_PROMPT = """Your custom developer prompt..."""
```

---

## 🐛 常见问题

### Q1: Ollama 连接失败

```
RuntimeError: Ollama API 调用失败: Connection refused
```

**解决方法：**
```bash
# 确保 Ollama 服务已启动
ollama serve

# 检查服务状态
curl http://localhost:11434/api/version
```

### Q2: 模型未找到

```
RuntimeError: Ollama API 调用失败: model 'llama3.2:latest' not found
```

**解决方法：**
```bash
# 下载模型
ollama pull llama3.2:latest

# 查看已安装的模型
ollama list
```

### Q3: JSON 解析失败

**原因：** 模型返回了非 JSON 格式的内容

**解决方法：**
- 在 `ollama_backend.py` 中已降低 temperature（0.1）
- 在 Prompt 中强调 "Output ONLY JSON"

### Q4: Fact Type 判断不准确

**原因：** Prompt 可能需要针对特定模型调整

**解决方法：**
- 尝试不同的模型（某些模型更擅长分类任务）
- 在 Prompt 中增加更多示例

---

## 📝 Need Resolver 判定逻辑

```python
if fact_type == "EVENT":
    need_resolver = false  # 点事实，不需要有效期

elif fact_type == "STATE":
    if 已抽取到 valid_to:
        need_resolver = false  # 已有有效期，不需要 resolver
    else:
        need_resolver = true   # 缺失有效期，需要 resolver 推理
```

**决策表：**

| fact_type | 有效期情况 | need_resolver | 说明 |
|-----------|------------|---------------|------|
| EVENT | - | ❌ false | 历史事件，不需要有效期 |
| STATE | 有 valid_to | ❌ false | 已知结束时间，不需推理 |
| STATE | 无 valid_to | ✅ true | 需要 resolver 推理 |

---

## 📚 与现有系统集成

### 与 `extractor/ner.py` 的关系

```
extractor/
├── ner.py                      # 老版本：FootballAnchorExtractor（规则 based）
├── entity_extractor.py         # 实体抽取
└── time_expression_extractor.py # 时间表达式抽取

extractor_v1/                   # 新版本目录
├── ollama_backend.py           # LLM based
└── anchor_extractor.py         # 调用 ollama_backend
```

**建议：**
- 如果需要规则 based 抽取（不依赖 LLM），使用 `extractor/ner.py`
- 如果需要 LLM 智能抽取（支持 EVENT/STATE 判定），使用 `extractor_v1/anchor_extractor.py`

---

## 📄 License

MIT

---

## 📧 支持

如需帮助或建议，请查看：
- 测试文件：`test_anchor_extraction.py`
- Ollama 文档：https://github.com/ollama/ollama
- LLM Prompt Engineering：https://www.promptingguide.ai/
