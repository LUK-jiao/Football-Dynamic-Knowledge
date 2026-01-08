"""
Extractor Output Directory

本目录存储 extractor 模块生成的 JSON 输出文件。

## 文件命名规范

格式: `extractor_output_<test_case_name>.json`

## 当前文件

- **extractor_output_arsenal_efl_cup_match.json**: Arsenal EFL Cup 比赛报道
- **extractor_output_de_ligt_transfer.json**: De Ligt 转会新闻
- **extractor_output_salah_injury_report.json**: Salah 伤病报告

## 文件结构

每个 JSON 文件包含一个数组，其中每个元素是一个处理后的语义块：

```json
[
  {
    "block_id": "block_001",
    "text": "语义分块的完整文本...",
    "source": "来源名称",
    "publish_date": "YYYY-MM-DD",
    "anchors": {
      "participants": [...],
      "temporal_anchors": [...],
      "sources": [...],
      "constraints": [...]
    }
  }
]
```

## 用途

这些输出文件可用于：
- 验证 extractor 抽取结果
- 作为知识图谱构建的输入
- 调试和分析锚点质量
- 示例数据展示

## 生成方式

通过集成测试自动生成：
```bash
.venv/bin/python extractor/integration_test.py
```
"""
