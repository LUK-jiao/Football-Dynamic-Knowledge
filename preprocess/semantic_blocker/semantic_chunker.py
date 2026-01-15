"""
Semantic Chunker v2 - Continuous Scoring System

A production-grade semantic chunking module using LLM as a scoring component
(not a decision maker).

Core Architecture:
    Sentences → LLM Scoring (0.0-1.0) → Threshold Decision → Post-processing → Chunks

Key Principles:
- LLM outputs semantic break strength score (continuous, 0.0-1.0)
- Threshold-based decisions (configurable granularity)
- Mandatory post-processing rules (force split, merge orphans, structural detection)
- Deterministic and explainable
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
import re


# ============================================================================
# Configuration
# ============================================================================

class GranularityMode(str, Enum):
    """Chunk granularity levels."""
    FINE = "fine"          # Aggressive splitting (threshold=0.45)
    MEDIUM = "medium"      # Balanced (threshold=0.55)
    COARSE = "coarse"      # Conservative (threshold=0.65)


@dataclass
class ChunkerConfig:
    """
    Configuration for semantic chunker v2.
    
    Args:
        granularity: Chunk granularity mode (fine/medium/coarse)
        break_threshold: Override threshold (0.0-1.0), None uses granularity default
        max_sentences_per_chunk: Hard limit to prevent runaway chunks
        context_window: Number of previous sentences to consider (1-3 recommended)
        enable_structural_rules: Use rule-based forced splits (quotes, stats)
        enable_orphan_merge: Merge single-sentence chunks backward
        log_scores: Log all LLM scores for debugging
    """
    granularity: GranularityMode = GranularityMode.MEDIUM
    break_threshold: Optional[float] = None
    max_sentences_per_chunk: int = 5
    context_window: int = 2
    enable_structural_rules: bool = True
    enable_orphan_merge: bool = True
    log_scores: bool = False
    
    def __post_init__(self):
        # Set threshold based on granularity if not overridden
        if self.break_threshold is None:
            self.break_threshold = {
                GranularityMode.FINE: 0.45,
                GranularityMode.MEDIUM: 0.55,
                GranularityMode.COARSE: 0.65
            }[self.granularity]
        
        # Validate
        if not 0.0 <= self.break_threshold <= 1.0:
            raise ValueError(f"break_threshold must be in [0.0, 1.0], got {self.break_threshold}")
        if self.max_sentences_per_chunk < 1:
            raise ValueError(f"max_sentences_per_chunk must be >= 1")
        if not 1 <= self.context_window <= 5:
            logging.warning(f"context_window={self.context_window} outside recommended range [1,5]")


@dataclass
class ScoringResult:
    """Result from LLM scoring."""
    score: float  # 0.0 (same unit) to 1.0 (new topic)
    success: bool
    raw_output: Optional[str] = None
    
    def should_break(self, threshold: float) -> bool:
        """Check if score exceeds break threshold."""
        return self.score >= threshold


@dataclass
@dataclass
class Chunk:
    """A semantic chunk with metadata."""
    sentences: List[str]
    chunk_id: int
    chunk_type: str = "normal"  # Type of chunk: "normal", "single", "quote", etc.
    scores: List[float] = None  # LLM scores for each sentence (except first)
    
    def __post_init__(self):
        if self.scores is None:
            self.scores = []
    
    def __len__(self):
        return len(self.sentences)
    
    def to_extractor_input(self, source: str = "", publish_date: str = "") -> dict:
        """
        转换为 extractor 模块所需的输入格式
        
        Args:
            source: 文档来源（如 "BBC", "Official"）
            publish_date: 发布日期（YYYY-MM-DD）
            
        Returns:
            标准化的 extractor 输入字典，包含 block_id, text, source, publish_date
        """
        return {
            "block_id": f"block_{self.chunk_id:03d}",
            "text": " ".join(self.sentences),  # 合并句子为单个文本块
            "source": source,
            "publish_date": publish_date
        }


# ============================================================================
# LLM Backend Interface
# ============================================================================

class LLMBackend:
    """Abstract interface for LLM scoring backend."""
    
    def score_boundary(
        self, 
        current_sentence: str, 
        previous_sentences: List[str]
    ) -> Tuple[float, bool]:
        """
        Score semantic break strength between current and previous context.
        
        Args:
            current_sentence: Sentence to evaluate
            previous_sentences: Previous context (1-N sentences)
            
        Returns:
            (score, success)
            - score: float in [0.0, 1.0]
              * 0.0 = same semantic unit
              * 0.5 = sub-event shift
              * 1.0 = completely new topic
            - success: True if LLM responded validly
        """
        raise NotImplementedError


# ============================================================================
# Structural Rule Detection
# ============================================================================

class StructuralRules: #通过正则匹配针对
    """Rule-based detection of forced semantic boundaries."""
    
    # Patterns that force a new chunk
    QUOTE_START_PATTERN = r'(said|told|stated|commented|explained|added)\s+(that\s+)?["\']'
    QUOTE_ATTRIBUTION = r'^[A-Z][a-z]+\s+(said|told|stated)'
    
    STATS_MARKERS = [
        "Overall,", "Historically,", "This was", "In total,", 
        "The final score", "Statistics show"
    ]
    
    FUTURE_MARKERS = [
        "will face", "will play", "next round", "semi-final", 
        "quarter-final", "scheduled for", "set for"
    ]
    
    TEMPORAL_MARKERS = [
        "Meanwhile,", "Later,", "After the match,", "Following the game,",
        "In another match,", "In the next game,"
    ]
    
    @classmethod
    def should_force_split(cls, sentence: str) -> Tuple[bool, Optional[str]]:
        """
        Check if sentence should force a new chunk.
        
        Returns:
            (should_split, reason)
        """
        # Quote detection
        if re.search(cls.QUOTE_START_PATTERN, sentence, re.IGNORECASE):
            return (True, "quote_start")
        if re.match(cls.QUOTE_ATTRIBUTION, sentence):
            return (True, "quote_attribution")
        
        # Statistics
        if any(sentence.startswith(marker) for marker in cls.STATS_MARKERS):
            return (True, "statistics")
        
        # Future fixtures
        if any(marker in sentence.lower() for marker in cls.FUTURE_MARKERS):
            return (True, "future_fixture")
        
        # Temporal shifts
        if any(sentence.startswith(marker) for marker in cls.TEMPORAL_MARKERS):
            return (True, "temporal_shift")
        
        return (False, None)


# ============================================================================
# Main Semantic Chunker
# ============================================================================

class SemanticChunker:
    """
    Production-grade semantic chunker with continuous scoring.
    
    Pipeline:
        1. Sliding window with LLM scoring
        2. Threshold-based decisions
        3. Post-processing (force split, structural rules, orphan merge)
    """
    
    def __init__(self, llm: LLMBackend, config: ChunkerConfig = None):
        """
        Initialize semantic chunker.
        
        Args:
            llm: LLM backend for scoring
            config: Chunker configuration
        """
        self.llm = llm
        self.config = config or ChunkerConfig()
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'total_scores': 0,
            'llm_failures': 0,
            'forced_splits_size': 0,
            'forced_splits_structural': 0,
            'orphan_merges': 0,
            'score_distribution': []
        }
    
    def chunk(self, sentences: List[str]) -> List[Chunk]:
        """
        Split sentences into semantic chunks.
        
        Args:
            sentences: Pre-split sentences (from spaCy-based splitter)
            
        Returns:
            List of Chunk objects with metadata
        """
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [Chunk(sentences=sentences, chunk_id=1, chunk_type="single")]
        
        # Reset stats
        self.stats['score_distribution'] = []
        
        # Stage 1: Initial chunking with LLM scoring
        raw_chunks = self._initial_chunking(sentences)
        
        # Stage 2: Post-processing
        if self.config.enable_orphan_merge:
            raw_chunks = self._merge_orphans(raw_chunks)
        
        # Stage 3: Assign chunk IDs and types
        final_chunks = self._finalize_chunks(raw_chunks)
        
        return final_chunks
    
    def _initial_chunking(self, sentences: List[str]) -> List[List[str]]:
        """
        Initial chunking using LLM scoring and threshold decisions.
        
        Returns:
            List of sentence lists (chunks)
        """
        chunks = []
        current_chunk = [sentences[0]]
        current_scores = []
        
        for i in range(1, len(sentences)):
            current_sentence = sentences[i]
            
            # Check structural rules first (override LLM)
            if self.config.enable_structural_rules:
                should_split, reason = StructuralRules.should_force_split(current_sentence)
                if should_split:
                    self.logger.info(f"Forced split at sentence {i}: {reason}")
                    self.stats['forced_splits_structural'] += 1
                    chunks.append(current_chunk)
                    current_chunk = [current_sentence]
                    current_scores = []
                    continue
            
            # Check hard size limit (override LLM)
            if len(current_chunk) >= self.config.max_sentences_per_chunk:
                self.logger.info(f"Forced split at sentence {i}: max size reached")
                self.stats['forced_splits_size'] += 1
                chunks.append(current_chunk)
                current_chunk = [current_sentence]
                current_scores = []
                continue
            
            # Get previous context
            context = self._get_context(current_chunk)
            
            # Get LLM score
            scoring_result = self._score_sentence(current_sentence, context)
            self.stats['total_scores'] += 1
            self.stats['score_distribution'].append(scoring_result.score)
            
            if not scoring_result.success:
                self.stats['llm_failures'] += 1
            
            # Log if enabled
            if self.config.log_scores:
                self.logger.info(
                    f"Sentence {i}: score={scoring_result.score:.2f} "
                    f"(threshold={self.config.break_threshold:.2f})"
                )
            
            # Make decision
            if scoring_result.should_break(self.config.break_threshold):
                # Start new chunk
                chunks.append(current_chunk)
                current_chunk = [current_sentence]
                current_scores = []
            else:
                # Continue current chunk
                current_chunk.append(current_sentence)
                current_scores.append(scoring_result.score)
        
        # Don't forget last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_context(self, current_chunk: List[str]) -> List[str]:
        """Get previous context based on context_window."""
        return current_chunk[-self.config.context_window:]
    
    def _score_sentence(
        self, 
        sentence: str, 
        context: List[str]
    ) -> ScoringResult:
        """
        Get semantic break score from LLM.
        
        Returns:
            ScoringResult with score and success flag
        """
        score, success = self.llm.score_boundary(sentence, context)
        
        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))
        
        return ScoringResult(score=score, success=success)
    
    def _merge_orphans(self, chunks: List[List[str]]) -> List[List[str]]:
        """
        Merge single-sentence chunks backward if weakly connected.
        
        Rule: If chunk has 1 sentence AND would score < 0.3 with previous chunk,
              merge it backward.
        """
        if len(chunks) <= 1:
            return chunks
        
        merged = [chunks[0]]
        
        for i in range(1, len(chunks)):
            current = chunks[i]
            
            # Check if orphan (single sentence)
            if len(current) == 1:
                # Score against previous chunk
                prev_context = self._get_context(merged[-1])
                result = self._score_sentence(current[0], prev_context)
                
                # Merge if score < 0.3 (weak boundary)
                if result.score < 0.3:
                    self.logger.info(f"Merging orphan chunk (score={result.score:.2f})")
                    merged[-1].extend(current)
                    self.stats['orphan_merges'] += 1
                    continue
            
            # Don't merge
            merged.append(current)
        
        return merged
    
    def _finalize_chunks(self, raw_chunks: List[List[str]]) -> List[Chunk]:
        """
        Convert raw chunks to Chunk objects with metadata.
        """
        chunks = []
        for i, sentences in enumerate(raw_chunks, 1):
            chunk_type = self._infer_chunk_type(sentences)
            chunks.append(Chunk(
                sentences=sentences,
                chunk_id=i,
                chunk_type=chunk_type
            ))
        return chunks
    
    def _infer_chunk_type(self, sentences: List[str]) -> str:
        """
        Heuristically infer chunk type.
        """
        text = " ".join(sentences)
        
        if re.search(r'(said|told|stated|commented)', text):
            return "quotes"
        if any(marker in text for marker in ["Overall", "This was", "Statistics"]):
            return "statistics"
        if any(marker in text for marker in ["will face", "semi-final", "next round"]):
            return "future_fixture"
        if re.search(r'penalty|penalties|shoot-?out', text, re.IGNORECASE):
            return "penalty_shootout"
        if re.search(r'scored?|goal', text, re.IGNORECASE):
            return "goal_sequence"
        
        return "match_narrative"
    
    def get_stats(self) -> Dict:
        """Get chunking statistics."""
        stats = self.stats.copy()
        
        if stats['score_distribution']:
            scores = stats['score_distribution']
            stats['avg_score'] = sum(scores) / len(scores)
            stats['min_score'] = min(scores)
            stats['max_score'] = max(scores)
        
        return stats
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_scores': 0,
            'llm_failures': 0,
            'forced_splits_size': 0,
            'forced_splits_structural': 0,
            'orphan_merges': 0,
            'score_distribution': []
        }
