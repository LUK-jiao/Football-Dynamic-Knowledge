# Text Preprocessing Module# Text Preprocessing Module



## 📋 概述Complete text preprocessing pipeline for the Football Dynamic Knowledge system.



两阶段文本预处理Pipeline，将原始新闻文本转换为语义连贯的文本块，为后续知识抽取做准备。## Overview



```This module provides a two-stage text processing pipeline:

原始文本 → [句子分割] → 句子列表 → [语义分块] → 语义块

``````

Raw Text → [Sentence Splitter] → Sentences → [Semantic Chunker] → Semantic Chunks

**设计哲学**:```

- ✅ **简单可靠**: 优先使用成熟工具 (spaCy)

- ✅ **可控确定**: LLM作为评分器而非决策者### Stage 1: Sentence Splitting

- ✅ **容错健壮**: 多层fallback机制- Uses spaCy for accurate sentence boundary detection

- ✅ **可追溯**: 完整日志和中间结果- Handles quotes, abbreviations, and edge cases

- Simple, fast, reliable

---

### Stage 2: Semantic Chunking

## 🏗️ 系统架构- Uses LLM (Ollama/OpenAI) as binary boundary classifier

- Outputs: `SAME_UNIT` or `NEW_UNIT`

### 阶段1: 句子分割 (Sentence Splitter)- Robust fallback on LLM failures

- Deterministic behavior

**实现**: spaCy NLP Pipeline  

**核心类**: `SentenceSplitter`  ## Quick Start

**位置**: `sentence_splitter/splitter.py`

### Installation

#### 核心功能

```bash

```python# Install dependencies

from preprocess.sentence_splitter import SentenceSplitterpip install spacy requests



splitter = SentenceSplitter(model_name="en_core_web_sm")# Download spaCy model

sentences = splitter.split(raw_text)python -m spacy download en_core_web_sm

```

# Ensure Ollama is running

#### 处理流程ollama serve

ollama pull gemma3:12b

1. **spaCy分句** - 基于语言模型的边界检测```

2. **引用聚合** - 合并引号内的多句对话

3. **清洗过滤** - 去除空白、重复和短句### Basic Usage



#### 技术细节```python

from preprocess.sentence_splitter import SentenceSplitter

| 项目 | 说明 |from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

|------|------|

| **依赖模型** | `en_core_web_sm` (spaCy) |# Raw text

| **处理能力** | 缩写 (Dr., U.S.A.), 引号, 列表, 编号 |text = """

| **最小长度** | 10字符 (过滤碎片) |Arsenal won 2-1. Saka scored the winner. 

| **引用模式** | 自动检测并合并 `"..."` 内容 |Manager Arteta was delighted with the result.

| **性能** | ~1000句/秒 |"""



#### 特殊处理# Stage 1: Split into sentences

splitter = SentenceSplitter()

**引用聚合示例**:sentences = splitter.split(text)

```python# Result: ["Arsenal won 2-1.", "Saka scored the winner.", ...]

# 输入

['Manager said "We played well.',# Stage 2: Chunk semantically

 'The team showed great spirit."']backend = OllamaBackend(model="gemma3:12b")

chunks = semantic_chunk(sentences, backend)

# 输出 (聚合后)# Result: [["Arsenal won 2-1.", "Saka scored the winner."], [...]]

['Manager said "We played well. The team showed great spirit."']```

```

## Module Structure

**处理缩写**:

```python```

# 正确识别preprocess/

"Dr. Smith works at U.S.A. Medical Center."├── integration_test.py              # End-to-end pipeline test

# 输出: 1个句子 (不会错误分割)│

```├── sentence_splitter/

│   ├── __init__.py

---│   ├── splitter.py                  # SentenceSplitter class

│   └── README.md                    # Detailed documentation

### 阶段2: 语义分块 (Semantic Chunker)│

└── semantic_blocker/

**实现**: LLM连续评分 + 阈值决策      ├── __init__.py

**核心函数**: `semantic_chunk()`      ├── semantic_chunker.py          # Core chunker logic

**位置**: `semantic_blocker/semantic_chunker.py`    ├── ollama_backend.py            # LLM backend implementations

    ├── llm_aggregator.py            # Legacy event aggregator (deprecated)

#### 核心算法    ├── test_semantic_chunker.py     # Unit tests

    ├── example_refactored.py        # Usage examples

**v2.0架构** - LLM作为评分器:    ├── comparison.py                # Old vs new comparison

    └── README.md                    # Detailed documentation

``````

句子对 → LLM评分(0.0-1.0) → 阈值判断 → 强制规则 → 孤儿合并 → 语义块

```## Integration Test



**与v1.0对比**:Run the complete pipeline test:

- ❌ v1.0: LLM直接输出 `SAME_UNIT | NEW_UNIT` (二元决策)

- ✅ v2.0: LLM输出连续分数 (0.0-1.0), 系统根据阈值决策```bash

# Using virtual environment

#### 使用方式.venv/bin/python preprocess/integration_test.py



```python# Or system Python

from preprocess.semantic_blocker import semantic_chunk, OllamaBackendpython3 preprocess/integration_test.py

```

# 初始化LLM后端

backend = OllamaBackend(Expected output:

    model="gemma3:12b",```

    base_url="http://localhost:11434"================================================================================

)INTEGRATION TEST: Sentence Splitter + Semantic Chunker

================================================================================

# 执行语义分块

chunks = semantic_chunk([TEST 1] Football Match Report

    sentences=["Sent 1", "Sent 2", "Sent 3"],  ✓ Split into 11 sentences

    llm_backend=backend,  ✓ Created 2 semantic chunks

    granularity="medium"  # fine | medium | coarse

)[TEST 2] Mixed Topics

  ✓ Split into 7 sentences

# 结果  ✓ Created 3 semantic chunks

# [

#   ["Sent 1", "Sent 2"],  # Chunk 1[VALIDATION]

#   ["Sent 3"]             # Chunk 2  ✓ Should produce sentences

# ]  ✓ Should produce chunks

```  ✓ Should aggregate some sentences

  ✓ All sentences should be in chunks

#### 配置参数

✓ ALL INTEGRATION TESTS PASSED

##### 粒度模式 (Granularity)```



| 模式 | 阈值 | 适用场景 |## Features

|------|------|----------|

| `fine` | 0.45 | 细粒度分块，独立事件分离 |### Sentence Splitter

| `medium` | 0.55 | **推荐**，平衡准确度和召回 |- ✅ spaCy-based sentence boundary detection

| `coarse` | 0.65 | 粗粒度分块，保持上下文连贯 |- ✅ Quote aggregation for interviews

- ✅ Whitespace normalization

##### 高级配置- ✅ Deduplication

- ✅ Minimum length filtering

```python

from preprocess.semantic_blocker import ChunkerConfig, GranularityMode### Semantic Chunker

- ✅ LLM as binary classifier (not generator)

config = ChunkerConfig(- ✅ Sliding window architecture

    granularity=GranularityMode.MEDIUM,- ✅ Conservative fallback strategy

    break_threshold=0.55,              # 自定义阈值- ✅ Deterministic behavior (temp=0)

    max_sentences_per_chunk=5,         # 最大句子数- ✅ Backend-agnostic (Ollama, OpenAI, custom)

    context_window=2,                  # 上下文窗口- ✅ Comprehensive error handling

    enable_structural_rules=True,      # 启用结构化规则- ✅ Statistics tracking

    enable_orphan_merge=True,          # 合并孤儿句

    log_scores=True                    # 记录所有分数## Configuration

)

### Sentence Splitter

chunks = semantic_chunk(sentences, backend, config=config)

``````python

splitter = SentenceSplitter(

#### 评分机制    model_name="en_core_web_sm",  # spaCy model

    min_length=10                  # Minimum sentence length

**LLM Prompt模板**:)

``````

Rate the semantic break strength between these sentences on a scale of 0.0 to 1.0:

### Semantic Chunker

Previous context:

"Arsenal won 2-1 against Brighton."```python

from preprocess.semantic_blocker import ChunkerConfig

Current sentence:

"Bukayo Saka scored the winning goal."config = ChunkerConfig(

    window_size=1,              # Compare with N previous sentences

Next sentence:    force_new_on_failure=True,  # Conservative fallback

"Manager Arteta praised the team's performance."    log_failures=True,          # Log fallback events

    max_context_length=500      # Max context chars for LLM

Instructions:)

- 0.0-0.3: Same event/topic (CONTINUE)

- 0.4-0.6: Related but distinct (SOFT BREAK)chunker = SemanticChunker(backend, config)

- 0.7-1.0: Completely different topic (HARD BREAK)```



Output only a number between 0.0 and 1.0:## Performance

```

| Stage | Speed | Quality |

**评分规则**:|-------|-------|---------|

- `score < 0.45`: 同一主题，继续累积| Sentence Splitting | ~0.01s per paragraph | Excellent (spaCy) |

- `0.45 ≤ score < 0.55`: 边界区域，依赖上下文| Semantic Chunking | ~1-2s per decision | Excellent (LLM) |

- `score ≥ 0.55`: 明确分界，切分新块

## Testing

#### 后处理规则

### Unit Tests

##### 1. 强制分割 (Structural Rules)```bash

# Test semantic chunker

当`enable_structural_rules=True`时自动检测:.venv/bin/python preprocess/semantic_blocker/test_semantic_chunker.py

# Expected: 11/11 tests pass

```python```

# 引号边界

'Arteta said "We played well." The next match is crucial.'### Integration Test

# → 在引号后强制分割```bash

# Test full pipeline

# 统计数据.venv/bin/python preprocess/integration_test.py

'Arsenal scored 5 goals. Statistics: Shots 20, Possession 65%.'# Expected: All tests pass

# → 在统计关键词前分割```



# 列表标记### Examples

'There are three reasons: 1) Defense improved. 2) Attack sharp.'```bash

# → 在编号前分割# Run semantic chunker examples

```.venv/bin/python preprocess/semantic_blocker/example_refactored.py



##### 2. 孤儿合并 (Orphan Merge)# Compare old vs new system

.venv/bin/python preprocess/semantic_blocker/comparison.py

当`enable_orphan_merge=True`时:```



```python## Design Philosophy

# 处理前

[["Arsenal won 2-1.", "Saka scored."], ["Great performance."]]### Simplicity Over Complexity

                                        ↑ 单句孤儿- Each module does one thing well

- Clear separation of concerns

# 处理后- Easy to understand and maintain

[["Arsenal won 2-1.", "Saka scored.", "Great performance."]]

                                        ↑ 向前合并### Robustness Over Perfection

```- Conservative fallback strategies

- Comprehensive error handling

##### 3. 长度限制 (Max Sentences)- No silent failures



```python### Determinism Over Creativity

max_sentences_per_chunk = 5- Same input → same output

- No randomness in production

# 如果累积到第5句，强制切分- Predictable behavior

["Sent1", "Sent2", "Sent3", "Sent4", "Sent5"] → 切分

["Sent6", ...]                                → 新块## Troubleshooting

```

### spaCy model not found

#### 容错机制```bash

python -m spacy download en_core_web_sm

**三层Fallback**:```



```python### Cannot connect to Ollama

1. LLM评分失败 → 返回 score=0.7 (保守策略：偏向切分)```bash

2. LLM超时 → 重试1次# Start Ollama server

3. LLM完全不可用 → 使用规则分块器 (关键词+长度)ollama serve

```

# Verify it's running

**日志记录**:curl http://localhost:11434/api/tags

```python```

# 每个评分决策都会记录

logger.info(f"Sentence pair [{i}-{i+1}]: score={score:.2f}, decision={'BREAK' if break else 'CONTINUE'}")### High fallback rate

```- Check Ollama server logs

- Try increasing timeout

---- Consider using more capable model



## 📊 完整示例## Future Enhancements



### 基础用法Potential improvements (not currently implemented):

- [ ] Batch processing for better throughput

```python- [ ] Caching for repeated inputs

from preprocess.sentence_splitter import SentenceSplitter- [ ] Multi-language support

from preprocess.semantic_blocker import semantic_chunk, OllamaBackend- [ ] Confidence scoring

- [ ] Async processing

# 原始新闻文本

text = """## Documentation

Arsenal secured a dramatic 8-7 penalty shootout victory over Crystal Palace 

in the EFL Cup quarter-final on Wednesday night. The match ended 1-1 after - **Sentence Splitter**: See `sentence_splitter/README.md`

extra time at Emirates Stadium.- **Semantic Chunker**: See `semantic_blocker/README.md`

- **Integration Test**: See `integration_test.py` source code

Bukayo Saka scored the winning penalty after goalkeeper David Raya saved 

two Palace spot-kicks. Manager Mikel Arteta praised his team's resilience.## Version History



In other Premier League news, Manchester United announced the signing of ### v2.0.0 (Current)

a new striker from Bayern Munich for £50 million.- ✨ Refactored semantic chunker as binary classifier

"""- ✨ Added Ollama backend support

- ✨ Comprehensive testing and documentation

# 阶段1: 句子分割- ✨ Integration test for full pipeline

splitter = SentenceSplitter()- 🗑️ Cleaned up redundant files

sentences = splitter.split(text)

print(f"Split into {len(sentences)} sentences")### v1.0.0

- Initial implementation with event aggregation

# 阶段2: 语义分块- OpenAI backend only

backend = OllamaBackend(model="gemma3:12b")- Complex event taxonomy

chunks = semantic_chunk(sentences, backend, granularity="medium")

## License

# 输出结果

for i, chunk in enumerate(chunks, 1):Same as parent project (Football Dynamic Knowledge).

    print(f"\n=== Chunk {i} ({len(chunk)} sentences) ===")

    for sent in chunk:---

        print(f"  - {sent}")

```**Last Updated**: 2026-01-06


### 预期输出

```
Split into 6 sentences

=== Chunk 1 (3 sentences) ===
  - Arsenal secured a dramatic 8-7 penalty shootout victory over Crystal Palace in the EFL Cup quarter-final on Wednesday night.
  - The match ended 1-1 after extra time at Emirates Stadium.
  - Bukayo Saka scored the winning penalty after goalkeeper David Raya saved two Palace spot-kicks.

=== Chunk 2 (1 sentence) ===
  - Manager Mikel Arteta praised his team's resilience.

=== Chunk 3 (2 sentences) ===
  - In other Premier League news, Manchester United announced the signing of a new striker from Bayern Munich for £50 million.
```

### 高级用法：自定义配置

```python
from preprocess.semantic_blocker import ChunkerConfig, GranularityMode

# 精细分块 + 结构化规则
config = ChunkerConfig(
    granularity=GranularityMode.FINE,
    enable_structural_rules=True,
    enable_orphan_merge=True,
    log_scores=True
)

chunks = semantic_chunk(sentences, backend, config=config)
```

---

## 🧪 测试和验证

### 集成测试

```bash
# 运行完整Pipeline测试
python preprocess/integration_test.py
```

**测试内容**:
- ✅ 句子分割准确性
- ✅ 语义分块一致性
- ✅ 边界情况处理
- ✅ LLM容错机制

### 单元测试

```bash
# 句子分割器测试
python preprocess/sentence_splitter/test_splitter.py

# 语义分块器测试
python preprocess/semantic_blocker/test_semantic_chunker.py
```

---

## ⚙️ 技术规格

### 依赖项

```bash
# 核心依赖
pip install spacy requests

# spaCy模型
python -m spacy download en_core_web_sm

# LLM后端
# Ollama需单独安装: https://ollama.ai
ollama serve
ollama pull gemma3:12b
```

### 性能指标

| 指标 | 数值 |
|------|------|
| 句子分割速度 | ~1000句/秒 |
| 语义分块速度 | ~0.5秒/对 (LLM) |
| 内存占用 | ~500MB (包含spaCy模型) |
| LLM超时 | 10秒 |
| 批处理能力 | 100篇文章/分钟 |

### 推荐配置

**生产环境**:
```python
config = ChunkerConfig(
    granularity=GranularityMode.MEDIUM,
    max_sentences_per_chunk=5,
    context_window=2,
    enable_structural_rules=True,
    enable_orphan_merge=True,
    log_scores=False  # 生产环境关闭详细日志
)
```

**开发/调试**:
```python
config = ChunkerConfig(
    granularity=GranularityMode.FINE,
    max_sentences_per_chunk=3,
    context_window=3,
    enable_structural_rules=True,
    enable_orphan_merge=True,
    log_scores=True  # 启用详细日志
)
```

---

## 🔧 LLM后端配置

### Ollama Backend

```python
from preprocess.semantic_blocker import OllamaBackend

backend = OllamaBackend(
    model="gemma3:12b",              # 推荐模型
    base_url="http://localhost:11434",
    timeout=10.0,                     # 请求超时
    default_temperature=0.3           # 低温度保证稳定性
)
```

### 支持的模型

| 模型 | 参数量 | 速度 | 准确度 | 推荐用途 |
|------|--------|------|--------|----------|
| `gemma3:12b` | 12B | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **生产推荐** |
| `llama3:latest` | 8B | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 快速原型 |
| `mistral:latest` | 7B | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 资源受限 |

---

## 📁 模块结构

```
preprocess/
├── README.md                        # 本文档
├── integration_test.py              # 端到端测试
│
├── sentence_splitter/               # 句子分割器
│   ├── __init__.py
│   ├── splitter.py                  # SentenceSplitter类
│   ├── test_splitter.py             # 单元测试
│   └── README.md                    # 详细文档
│
└── semantic_blocker/                # 语义分块器
    ├── __init__.py
    ├── semantic_chunker.py          # 核心分块逻辑 (v2.0)
    ├── ollama_backend.py            # LLM后端接口
    ├── test_semantic_chunker.py     # 单元测试
    ├── example_refactored.py        # 使用示例
    └── README.md                    # 详细文档
```

---

## 🚨 常见问题

### 1. spaCy模型未安装

**错误**:
```
OSError: [E050] Can't find model 'en_core_web_sm'
```

**解决**:
```bash
python -m spacy download en_core_web_sm
```

### 2. Ollama连接失败

**错误**:
```
ConnectionError: Could not connect to Ollama at http://localhost:11434
```

**解决**:
```bash
# 启动Ollama服务
ollama serve

# 拉取模型
ollama pull gemma3:12b
```

### 3. 分块过于细碎

**问题**: 每个句子都被切分为独立块

**解决**:
```python
# 调整为coarse模式
chunks = semantic_chunk(sentences, backend, granularity="coarse")

# 或自定义更高阈值
config = ChunkerConfig(break_threshold=0.7)
chunks = semantic_chunk(sentences, backend, config=config)
```

### 4. 分块过于粗糙

**问题**: 不同主题的句子被合并

**解决**:
```python
# 调整为fine模式
chunks = semantic_chunk(sentences, backend, granularity="fine")

# 或启用结构化规则
config = ChunkerConfig(
    granularity=GranularityMode.MEDIUM,
    enable_structural_rules=True
)
chunks = semantic_chunk(sentences, backend, config=config)
```

---

## 🎯 设计原则

### 为什么不用传统NLP方法？

**传统方法 (TextTiling, C99)**:
- ❌ 依赖词汇相似度 (无法理解语义)
- ❌ 固定窗口大小 (不灵活)
- ❌ 无法处理隐式主题转换

**LLM评分方法**:
- ✅ 理解语义和上下文
- ✅ 动态判断边界强度
- ✅ 处理复杂叙事结构

### 为什么v2.0改用连续评分？

**v1.0问题 (二元决策)**:
- ❌ 边界模糊时LLM输出不稳定
- ❌ 无法表达"略有关联"的中间状态
- ❌ 难以调整灵敏度

**v2.0优势 (连续评分)**:
- ✅ 可以通过阈值控制粒度
- ✅ 分数可用于后续分析
- ✅ 更加确定和可控

### 为什么需要后处理规则？

**纯LLM方法的局限**:
- ❌ 可能产生单句孤儿块
- ❌ 不保证最大长度限制
- ❌ 忽略明确的结构标记

**规则+LLM混合**:
- ✅ 保证输出质量基线
- ✅ 处理特殊格式 (引用、列表)
- ✅ 提高鲁棒性

---

## 📚 相关文档

- [句子分割器详细文档](sentence_splitter/README.md)
- [语义分块器详细文档](semantic_blocker/README.md)
- [项目架构文档](../PROJECT_ARCHITECTURE.md)

---

## 🔄 更新日志

### v2.0 (2026-02-26)
- ✅ 改用连续评分机制 (0.0-1.0)
- ✅ 新增粒度模式 (fine/medium/coarse)
- ✅ 新增结构化强制规则
- ✅ 新增孤儿句合并
- ✅ 新增上下文窗口配置
- ✅ 改进日志和可追溯性

### v1.0 (2025-12)
- ✅ 初始版本：二元决策 (SAME_UNIT/NEW_UNIT)
- ✅ spaCy句子分割
- ✅ Ollama LLM集成

---

**最后更新**: 2026年2月27日  
**版本**: v2.0  
**维护者**: LUK-jiao
