"""
Football Anchor Extraction V1

基于 Ollama LLM 的足球事实锚点抽取系统。

主要模块：
- ollama_backend: Ollama 后端（优化的 Prompt + LLM 调用）
- anchor_extractor: 业务调用层（支持并发）
- cached_extractor: 带缓存的抽取器（推荐）
- test_anchor_extraction: 综合测试套件
- example_usage: 使用示例

优化工具：
- compare_model_speed: 模型速度对比
- OPTIMIZATION.md: 完整优化指南
- PROMPT_OPTIMIZATION.md: Prompt 优化说明
"""

from extractor_v1.ollama_backend import OllamaBackend, run_event_anchor_extraction
from extractor_v1.anchor_extractor import AnchorExtractor, extract_anchors_from_block

__version__ = "1.2.0"  # Prompt 优化：减少 81% tokens，提速 7-15%

__all__ = [
    "OllamaBackend",
    "run_event_anchor_extraction",
    "AnchorExtractor",
    "extract_anchors_from_block"
]
