# 项目结构整理说明

## 📁 目录结构变更

### 新增目录

#### 1. `debug/` - 调试和测试模块
存放所有开发调试和测试脚本

**文件列表**：
- `debug_chunker.py` - 语义分块调试工具（详细日志、粒度对比）
- `test_v2.py` - v2 系统完整测试
- `test_fresh.py` - 基础功能测试
- `quick_test.py` - 快速测试脚本
- `README.md` - 调试模块说明文档

**使用方式**：
```bash
# 调试语义分块
.venv/bin/python debug/debug_chunker.py -g medium

# 运行系统测试
.venv/bin/python debug/test_v2.py
```

#### 2. `extractor/output/` - Extractor 输出目录
存放 extractor 模块生成的 JSON 锚点文件

**文件列表**：
- `extractor_output_arsenal_efl_cup_match.json` - Arsenal EFL Cup 比赛
- `extractor_output_de_ligt_transfer.json` - De Ligt 转会
- `extractor_output_salah_injury_report.json` - Salah 伤病
- `README.md` - 输出目录说明文档

**自动生成**：
```bash
# 运行集成测试会自动生成输出到此目录
.venv/bin/python extractor/integration_test.py
```

---

## 🔄 变更记录

### 移动的文件

**从根目录 → debug/**：
- `debug_chunker.py`
- `quick_test.py`
- `test_fresh.py`
- `test_v2.py`

**从根目录 → extractor/output/**：
- `extractor_output_arsenal_efl_cup_match.json`
- `extractor_output_de_ligt_transfer.json`
- `extractor_output_salah_injury_report.json`

### 代码变更

**更新的文件**：
- `extractor/integration_test.py`
  - 修改输出路径：从根目录 → `extractor/output/`
  - 添加自动创建输出目录的逻辑

---

## 📊 整理后的项目结构

```
Football_Dynamic_Knowledge/
├── api/                              # API 层
├── core/                             # 核心配置
├── datasource/                       # 数据采集
├── preprocess/                       # 预处理
│   ├── sentence_splitter/           # 句子分割
│   └── semantic_blocker/            # 语义分块
├── extractor/                        # ✨ 锚点抽取模块
│   ├── ner.py                       # 核心抽取器
│   ├── integration_test.py          # 集成测试
│   ├── output/                      # 📁 输出目录 (新增)
│   │   ├── README.md
│   │   └── *.json                   # 锚点 JSON 文件
│   └── README.md
├── debug/                            # 📁 调试模块 (新增)
│   ├── debug_chunker.py             # 语义分块调试
│   ├── test_v2.py                   # 系统测试
│   ├── test_fresh.py                # 基础测试
│   ├── quick_test.py                # 快速测试
│   └── README.md
├── knowledge_graph/                  # 知识图谱
├── embeddings/                       # 向量化
├── rag/                              # RAG 引擎
├── retriever/                        # 检索器
├── verifier/                         # 验证器
├── feedback/                         # 反馈系统
├── workers/                          # 后台任务
└── docker/                           # 部署配置
```

---

## ✅ 整理的好处

### 1. **清晰的目录结构**
- 调试文件统一管理在 `debug/`
- 输出文件统一管理在 `extractor/output/`
- 根目录更加整洁

### 2. **易于维护**
- 新增调试脚本放到 `debug/`
- 模块化输出目录，避免根目录混乱

### 3. **便于版本控制**
- 可以通过 `.gitignore` 灵活控制是否提交调试文件和输出文件
- 目录结构更符合 Python 项目规范

### 4. **自动化输出**
- 集成测试自动将结果输出到 `extractor/output/`
- 无需手动指定路径

---

## 🔧 后续开发建议

### 调试文件管理
```bash
# 新增调试脚本时，直接放到 debug/ 目录
debug/
├── debug_xxx.py          # 新的调试脚本
└── test_xxx.py           # 新的测试脚本
```

### 输出文件管理
```bash
# extractor 输出自动管理
extractor/output/
└── extractor_output_<test_name>.json

# 其他模块也可以采用类似结构
knowledge_graph/output/
rag/output/
```

---

## 📝 注意事项

1. **路径引用**：如果其他代码引用了移动的文件，需要更新路径
2. **测试运行**：确保所有测试脚本在新位置仍能正常运行
3. **文档同步**：相关文档已更新路径说明

---

## ✅ 验证清单

- [x] 创建 `debug/` 目录
- [x] 创建 `extractor/output/` 目录
- [x] 移动调试文件到 `debug/`
- [x] 移动输出文件到 `extractor/output/`
- [x] 更新 `extractor/integration_test.py` 输出路径
- [x] 创建 `debug/README.md`
- [x] 创建 `extractor/output/README.md`
- [x] 更新 `.gitignore`
- [x] 创建整理说明文档

**🎉 项目结构整理完成！**
