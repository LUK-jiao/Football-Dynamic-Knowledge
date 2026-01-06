"""
Semantic Blocker Module (v2 - Continuous Scoring System)

Production-grade semantic chunker using LLM as a scoring component (not a decision maker).

Key Features:
- LLM outputs semantic break strength scores (0.0-1.0)
- Threshold-based decisions (configurable granularity)
- Mandatory post-processing rules (force split, merge orphans, structural detection)
- Deterministic and explainable

Architecture:
    Sentences → LLM Scoring (0.0-1.0) → Threshold Decision → Post-processing → Chunks

Usage:
    >>> from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, GranularityMode
    >>> from preprocess.semantic_blocker import OllamaBackend
    >>> from sentence_splitter import SentenceSplitter
    >>> 
    >>> # Split sentences
    >>> splitter = SentenceSplitter()
    >>> sentences = splitter.split(text)
    >>> 
    >>> # Configure chunker
    >>> backend = OllamaBackend(model="llama3:latest", temperature=0.2)
    >>> config = ChunkerConfig(
    ...     granularity=GranularityMode.MEDIUM,
    ...     enable_structural_rules=True
    ... )
    >>> 
    >>> # Chunk
    >>> chunker = SemanticChunker(llm=backend, config=config)
    >>> chunks = chunker.chunk(sentences)
    >>> 
    >>> # Use chunks
    >>> for chunk in chunks:
    ...     print(f"[{chunk.chunk_type}] {len(chunk)} sentences")
"""

from .semantic_chunker import (
    SemanticChunker,
    ChunkerConfig,
    GranularityMode,
    Chunk,
    ScoringResult,
    StructuralRules,
    LLMBackend
)

from .ollama_backend import (
    OllamaBackend,
    OpenAIBackend
)

__all__ = [
    # Core classes
    'SemanticChunker',
    'ChunkerConfig',
    'GranularityMode',
    'Chunk',
    'ScoringResult',
    'StructuralRules',
    'LLMBackend',
    
    # Backends
    'OllamaBackend',
    'OpenAIBackend',
]

__version__ = '2.0.0'

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

