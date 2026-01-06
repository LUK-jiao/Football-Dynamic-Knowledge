"""
Semantic Blocker Module

Sliding-window semantic chunker with LLM-based boundary detection.

This module provides deterministic, robust semantic chunking using LLM
as a binary classifier (SAME_UNIT vs NEW_UNIT).

Usage:
    >>> from preprocess.semantic_blocker import semantic_chunk
    >>> from preprocess.semantic_blocker import OllamaBackend
    >>> 
    >>> backend = OllamaBackend(model="llama3:latest")
    >>> sentences = ["Sentence 1.", "Sentence 2.", "Sentence 3."]
    >>> chunks = semantic_chunk(sentences, backend, window_size=1)
"""

from .semantic_chunker import (
    SemanticChunker,
    ChunkerConfig,
    BoundaryDecision,
    FallbackReason,
    ChunkDecision,
    semantic_chunk
)

from .ollama_backend import (
    OllamaBackend,
    OpenAIBackend
)

__all__ = [
    'SemanticChunker',
    'ChunkerConfig',
    'BoundaryDecision',
    'FallbackReason',
    'ChunkDecision',
    'semantic_chunk',
    'OllamaBackend',
    'OpenAIBackend',
]

