# Semantic Blocker Module

语义分块模块，用于将句子列表分组为语义完整的块，每个块可独立描述一个事件或事实。

## 功能概述

将 `sentence_splitter` 输出的句子列表进一步组织成语义块：
- **输入**：句子列表（来自 sentence_splitter）
- **输出**：语义块列表（每块语义完整，适合事件抽取）

## 架构设计

```
Sentences List
    ↓
① Vector Similarity Calculation (sentence-transformers)
    ↓
② Rule-based Adjustments
   - Subject consistency checking
   - Discourse marker detection
   - Time expression analysis
    ↓
③ Merge into Semantic Blocks
    ↓
④ Fallback Length Splitting
    ↓
⑤ Output Cleaning
    ↓
Semantic Blocks
```

## 安装依赖

```bash
# 核心依赖
pip install sentence-transformers scikit-learn numpy

# 可选依赖（用于主语提取）
pip install spacy
python -m spacy download en_core_web_sm
```

## 快速开始

### 基础用法

```python
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_block

# 1. 分句
splitter = SentenceSplitter()
text = """
Chelsea won 3-2 against United. The Blues celebrated.
However, Arsenal lost 1-0. The Gunners were disappointed.
"""
sentences = splitter.split(text)

# 2. 语义分块
blocks = semantic_block(sentences)

# 输出:
# Block 1: "Chelsea won 3-2 against United. The Blues celebrated."
# Block 2: "However, Arsenal lost 1-0. The Gunners were disappointed."
```

### 高级用法

```python
from preprocess.semantic_blocker import SemanticBlocker

# 自定义配置
blocker = SemanticBlocker(
    model_name='all-MiniLM-L6-v2',      # 向量模型
    similarity_threshold=0.6,            # 相似度阈值（0-1）
    max_block_length=400,                # 最大块长度
    use_subject_matching=True            # 启用主语匹配
)

blocks = blocker.block(sentences)
```

## 核心策略

### 1. 向量化（PRIMARY）

使用 `sentence-transformers` 计算句子向量的余弦相似度：
- 高相似度（≥ threshold）→ 考虑合并
- 低相似度（< threshold）→ 考虑分块

**默认模型**: `all-MiniLM-L6-v2`
- 轻量级（80MB）
- 速度快
- 适合英文语义理解

### 2. 规则调整（SECONDARY）

#### 规则 1: 话语标记边界
强制分块的话语标记：
- **转折**: however, nevertheless, nonetheless, conversely
- **时间过渡**: meanwhile, later, subsequently, then
- **话题转移**: separately, elsewhere, additionally

```python
# Example:
# "Chelsea won. However, Arsenal lost."
# → Block 1: "Chelsea won."
# → Block 2: "However, Arsenal lost."
```

#### 规则 2: 时间表达式转移
检测时间点变化，表示新事件：
- 年份：2024, 2025
- 月份：January, February
- 比赛时间：in the 78th minute
- 相对时间：last week, next season

```python
# Example:
# "Arsenal led 2-0. In the 89th minute, City equalized."
# → Block 1: "Arsenal led 2-0."
# → Block 2: "In the 89th minute, City equalized."
```

#### 规则 3: 主语一致性
相同主语的句子倾向合并（需要 spaCy）：

```python
# Example:
# "Chelsea signed a new striker. The club paid £50m."
# → Both about "Chelsea/club" → Merge
```

#### 规则 4: 长度保护
防止单个块过长（默认 400 字符）

### 3. 降级分割（FALLBACK）

当块超长时，在句号边界分割

### 4. 输出清洗

- 去除多余空格
- 规范化标点
- 确保格式一致

## 参数配置

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `model_name` | str | `'all-MiniLM-L6-v2'` | Sentence transformer 模型 |
| `similarity_threshold` | float | `0.6` | 余弦相似度阈值（0-1） |
| `max_block_length` | int | `400` | 最大块长度（字符） |
| `use_subject_matching` | bool | `True` | 启用主语一致性检查 |

## 使用场景

### 场景 1: 赛事报道分块
```python
text = """
Manchester City won 4-1. Haaland scored twice.
However, Liverpool lost 0-2. Injuries affected their performance.
"""
# → Block 1: City赢球 + Haaland表现
# → Block 2: Liverpool输球 + 伤病问题
```

### 场景 2: 转会新闻分块
```python
text = """
Chelsea signed Mudryk for £88m. The Ukrainian joined from Shakhtar.
He signed a 8-year contract. Mudryk expressed his excitement.
"""
# → Single block: 完整的转会事件（同一主语）
```

### 场景 3: 混合新闻分块
```python
text = """
Arsenal beat Spurs 3-1 on Sunday. Saka scored twice.
Meanwhile, Bayern Munich announced Tuchel's departure.
The German club will search for a new manager.
"""
# → Block 1: Arsenal vs Spurs
# → Block 2: Bayern教练变动
```

## 运行示例

```bash
# 从项目根目录运行
python -m preprocess.semantic_blocker.example
```

## 与现有模块集成

```python
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_block

# Pipeline: 原文 → 分句 → 语义分块
text = "Your sports news article..."
splitter = SentenceSplitter()

# Step 1: 分句
sentences = splitter.split(text)

# Step 2: 语义分块
blocks = semantic_block(sentences, similarity_threshold=0.6)

# Step 3: 事件抽取（下游任务）
for block in blocks:
    # extract_events(block)
    pass
```

## 性能优化建议

1. **模型选择**：
   - 轻量级：`all-MiniLM-L6-v2` (80MB, 快速)
   - 高精度：`all-mpnet-base-v2` (420MB, 更准确)
   - 多语言：`paraphrase-multilingual-MiniLM-L12-v2`

2. **阈值调优**：
   - 严格分块：`similarity_threshold=0.7` (更多小块)
   - 宽松分块：`similarity_threshold=0.5` (更少大块)
   - 默认平衡：`similarity_threshold=0.6`

3. **批量处理**：
   ```python
   blocker = SemanticBlocker()  # 复用模型
   for doc in documents:
       sentences = splitter.split(doc)
       blocks = blocker.block(sentences)
   ```

## 限制与注意事项

1. **依赖 sentence-transformers**：
   - 首次使用会下载模型（~80MB）
   - 需要合理的计算资源

2. **主语提取依赖 spaCy**（可选）：
   - 如未安装，主语匹配规则不生效
   - 不影响核心向量化功能

3. **语言限制**：
   - 当前针对英文优化
   - 其他语言需调整话语标记和时间表达式

## 测试

```bash
# 运行示例
python -m preprocess.semantic_blocker.example

# 集成测试
python -m pytest tests/test_semantic_blocker.py
```

## 扩展性

模块设计支持自定义扩展：

```python
class CustomBlocker(SemanticBlocker):
    def _apply_rules(self, sentences, similarities):
        # 添加自定义规则
        decisions = super()._apply_rules(sentences, similarities)
        # ... 你的规则逻辑
        return decisions
```

## 作者与维护

与 `sentence_splitter` 模块保持一致的代码风格和设计理念。
