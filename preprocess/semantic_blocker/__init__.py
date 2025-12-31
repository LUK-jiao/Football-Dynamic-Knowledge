"""
Semantic blocking module for grouping sentences into coherent semantic blocks.
Each block represents a complete event or fact suitable for downstream extraction.
"""

from .blocker import semantic_block, SemanticBlocker

__all__ = ['semantic_block', 'SemanticBlocker']
