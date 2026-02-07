"""
Football Anchor Extraction V1

基于 Ollama LLM 的足球事实锚点抽取系统。

主要模块：
- ollama_backend: Ollama 后端（Prompt + LLM 调用）
- anchor_extractor: 业务调用层（纯透传）
- test_anchor_extraction: 综合测试套件
- example_usage: 使用示例
"""

from extractor_v1.ollama_backend import OllamaBackend, run_event_anchor_extraction
from extractor_v1.anchor_extractor import AnchorExtractor, extract_anchors_from_block

__version__ = "1.0.0"

__all__ = [
    "OllamaBackend",
    "run_event_anchor_extraction",
    "AnchorExtractor",
    "extract_anchors_from_block",
]
