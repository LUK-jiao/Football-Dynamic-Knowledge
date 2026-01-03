"""
Semantic blocking module - LLM-based event aggregation.
Groups sentences into coherent semantic blocks using LLM intelligence.
Each block represents a complete event or fact suitable for downstream extraction.
"""

from .llm_aggregator import llm_semantic_chunk, LLMEventAggregator

__all__ = ['llm_semantic_chunk', 'LLMEventAggregator']
