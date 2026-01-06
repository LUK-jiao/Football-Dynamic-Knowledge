"""
Sliding-Window Semantic Chunker

A deterministic semantic boundary classifier using LLM as a binary decision engine.

Key Principles:
- LLM outputs ONLY "SAME_UNIT" or "NEW_UNIT"
- Sliding window compares current sentence with previous context
- Robust fallback: invalid LLM output → force NEW_UNIT
- No summarization, no generation, no creativity

Position in Pipeline:
    Rule-based Sentence Splitter → [Semantic Chunker] → Downstream Processing
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from datetime import datetime


# ============================================================================
# Decision Types
# ============================================================================

class BoundaryDecision(str, Enum):
    """LLM decision for semantic boundary."""
    SAME_UNIT = "SAME_UNIT"
    NEW_UNIT = "NEW_UNIT"


class FallbackReason(str, Enum):
    """Reasons for fallback to default behavior."""
    INVALID_OUTPUT = "invalid_output"
    EMPTY_RESPONSE = "empty_response"
    MULTIPLE_TOKENS = "multiple_tokens"
    LLM_ERROR = "llm_error"
    TIMEOUT = "timeout"


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class ChunkDecision:
    """Result of a single boundary decision."""
    decision: BoundaryDecision
    current_sentence: str
    previous_context: List[str]
    is_fallback: bool = False
    fallback_reason: Optional[FallbackReason] = None
    raw_llm_output: Optional[str] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class ChunkerConfig:
    """
    Configuration for semantic chunker.
    
    Args:
        window_size: 
            - Positive int: Fixed window (use last N sentences)
            - -1: Dynamic window (use all accumulated sentences in current chunk)
        force_new_on_failure: Fallback strategy when LLM fails
        log_failures: Whether to log LLM failures
        max_context_length: Max chars in context for LLM
    """
    window_size: int = 1  # 1=fixed window, -1=dynamic window
    force_new_on_failure: bool = True
    log_failures: bool = True
    max_context_length: int = 500
    
    def __post_init__(self):
        if self.window_size < 1 and self.window_size != -1:
            raise ValueError("window_size must be positive or -1 (dynamic)")
        if self.window_size > 5:
            logging.warning(f"Large window_size ({self.window_size}) may impact performance")


# ============================================================================
# LLM Backend Interface
# ============================================================================

class LLMBackend:
    """Abstract interface for LLM backend."""
    
    def decide_boundary(
        self, 
        current_sentence: str, 
        previous_sentences: List[str]
    ) -> Tuple[str, bool]:
        """
        Ask LLM to decide if current sentence continues the same semantic unit.
        
        Args:
            current_sentence: The sentence being evaluated
            previous_sentences: Previous 1-N sentences for context
            
        Returns:
            (raw_output: str, success: bool)
            - raw_output: The raw string from LLM
            - success: Whether the call succeeded (False = network/API error)
        """
        raise NotImplementedError


# ============================================================================
# Core Semantic Chunker
# ============================================================================

class SemanticChunker:
    """
    Sliding-window semantic chunker with LLM-based boundary detection.
    
    Design:
    - Deterministic: same input → same output
    - Conservative: when uncertain → start new chunk
    - Robust: handles all LLM failure modes
    """
    
    def __init__(
        self, 
        llm_backend: LLMBackend,
        config: Optional[ChunkerConfig] = None
    ):
        """
        Initialize chunker.
        
        Args:
            llm_backend: LLM backend implementation
            config: Configuration (uses defaults if None)
        """
        self.llm = llm_backend
        self.config = config or ChunkerConfig()
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'total_decisions': 0,
            'fallback_count': 0,
            'same_unit_count': 0,
            'new_unit_count': 0,
            'fallback_reasons': {}
        }
    
    def chunk(self, sentences: List[str]) -> List[List[str]]:
        """
        Split sentences into semantic chunks.
        
        Args:
            sentences: Pre-split sentences (from rule-based splitter)
            
        Returns:
            List of chunks, where each chunk is a list of sentences
            
        Example:
            >>> sentences = [
            ...     "Arsenal won 2-1.",
            ...     "Saka scored the winner.",
            ...     "Liverpool lost at home."
            ... ]
            >>> chunks = chunker.chunk(sentences)
            >>> # [[sentence1, sentence2], [sentence3]]
        """
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [sentences]
        
        chunks = []
        current_chunk = [sentences[0]]
        
        for i in range(1, len(sentences)):
            current_sentence = sentences[i]
            
            # Get previous context window
            previous_context = self._get_previous_context(current_chunk)
            
            # Make decision
            decision = self._make_decision(current_sentence, previous_context)
            
            # Update statistics
            self._update_stats(decision)
            
            # Apply decision
            if decision.decision == BoundaryDecision.SAME_UNIT:
                current_chunk.append(current_sentence)
            else:
                # Start new chunk
                chunks.append(current_chunk)
                current_chunk = [current_sentence]
        
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _get_previous_context(self, current_chunk: List[str]) -> List[str]:
        """
        Extract previous sentences for context window.
        
        Dynamic window strategy:
        - If window_size=-1: Use all sentences in current chunk (累积窗口)
          BUT limit to last 3 sentences to avoid context overflow
        - Otherwise: Use last N sentences (固定窗口)
        
        Args:
            current_chunk: The chunk being built
            
        Returns:
            Previous sentences for comparison
        """
        window_size = self.config.window_size
        
        # Dynamic window: use accumulated context (max 3 sentences)
        if window_size == -1:
            return current_chunk[-3:]  # Limit to prevent overwhelming context
        
        # Fixed window: use last N sentences
        return current_chunk[-window_size:]
    
    def _make_decision(
        self, 
        current_sentence: str, 
        previous_context: List[str]
    ) -> ChunkDecision:
        """
        Make boundary decision using LLM with fallback.
        
        Args:
            current_sentence: Sentence being evaluated
            previous_context: Previous sentences for context
            
        Returns:
            ChunkDecision with result and metadata
        """
        # Call LLM
        raw_output, call_success = self.llm.decide_boundary(
            current_sentence, 
            previous_context
        )
        
        # Parse and validate output
        decision, is_valid, reason = self._parse_llm_output(raw_output, call_success)
        
        # Handle fallback
        if not is_valid:
            if self.config.log_failures:
                self._log_fallback(
                    current_sentence, 
                    previous_context, 
                    raw_output, 
                    reason
                )
            
            # Apply fallback strategy
            if self.config.force_new_on_failure:
                decision = BoundaryDecision.NEW_UNIT
        
        return ChunkDecision(
            decision=decision,
            current_sentence=current_sentence,
            previous_context=previous_context,
            is_fallback=not is_valid,
            fallback_reason=reason if not is_valid else None,
            raw_llm_output=raw_output
        )
    
    def _parse_llm_output(
        self, 
        raw_output: str, 
        call_success: bool
    ) -> Tuple[BoundaryDecision, bool, Optional[FallbackReason]]:
        """
        Parse and validate LLM output.
        
        Args:
            raw_output: Raw string from LLM
            call_success: Whether the API call succeeded
            
        Returns:
            (decision, is_valid, fallback_reason)
        """
        # Check for API/network failure
        if not call_success:
            return (BoundaryDecision.NEW_UNIT, False, FallbackReason.LLM_ERROR)
        
        # Check for empty output
        if not raw_output or not raw_output.strip():
            return (BoundaryDecision.NEW_UNIT, False, FallbackReason.EMPTY_RESPONSE)
        
        # Normalize output
        cleaned = raw_output.strip().upper()
        
        # Check for exact match
        if cleaned == BoundaryDecision.SAME_UNIT.value:
            return (BoundaryDecision.SAME_UNIT, True, None)
        
        if cleaned == BoundaryDecision.NEW_UNIT.value:
            return (BoundaryDecision.NEW_UNIT, True, None)
        
        # Check if output contains multiple tokens or explanation
        if ' ' in cleaned or '\n' in cleaned or len(cleaned) > 20:
            return (BoundaryDecision.NEW_UNIT, False, FallbackReason.MULTIPLE_TOKENS)
        
        # Invalid output
        return (BoundaryDecision.NEW_UNIT, False, FallbackReason.INVALID_OUTPUT)
    
    def _log_fallback(
        self, 
        current_sentence: str, 
        previous_context: List[str],
        raw_output: str,
        reason: FallbackReason
    ):
        """Log fallback event for debugging."""
        self.logger.warning(
            f"LLM Fallback triggered | Reason: {reason.value} | "
            f"Context: {previous_context[-1] if previous_context else 'None'} | "
            f"Current: {current_sentence[:50]}... | "
            f"Raw Output: {raw_output[:100]}"
        )
    
    def _update_stats(self, decision: ChunkDecision):
        """Update internal statistics."""
        self.stats['total_decisions'] += 1
        
        if decision.is_fallback:
            self.stats['fallback_count'] += 1
            reason = decision.fallback_reason.value
            self.stats['fallback_reasons'][reason] = \
                self.stats['fallback_reasons'].get(reason, 0) + 1
        
        if decision.decision == BoundaryDecision.SAME_UNIT:
            self.stats['same_unit_count'] += 1
        else:
            self.stats['new_unit_count'] += 1
    
    def get_stats(self) -> Dict:
        """Get chunking statistics."""
        return {
            **self.stats,
            'fallback_rate': (
                self.stats['fallback_count'] / self.stats['total_decisions']
                if self.stats['total_decisions'] > 0 else 0.0
            )
        }
    
    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            'total_decisions': 0,
            'fallback_count': 0,
            'same_unit_count': 0,
            'new_unit_count': 0,
            'fallback_reasons': {}
        }


# ============================================================================
# Convenience Function
# ============================================================================

def semantic_chunk(
    sentences: List[str],
    llm_backend: LLMBackend,
    window_size: int = 1,
    force_new_on_failure: bool = True
) -> List[List[str]]:
    """
    Convenience function for semantic chunking.
    
    Args:
        sentences: Pre-split sentences
        llm_backend: LLM backend instance
        window_size: Number of previous sentences for context
        force_new_on_failure: Whether to start new chunk on LLM failure
        
    Returns:
        List of semantic chunks
        
    Example:
        >>> from semantic_chunker import semantic_chunk
        >>> from ollama_backend import OllamaBackend
        >>> 
        >>> backend = OllamaBackend(model="llama3:latest")
        >>> sentences = ["Sentence 1.", "Sentence 2.", "Sentence 3."]
        >>> chunks = semantic_chunk(sentences, backend, window_size=1)
    """
    config = ChunkerConfig(
        window_size=window_size,
        force_new_on_failure=force_new_on_failure
    )
    
    chunker = SemanticChunker(llm_backend, config)
    return chunker.chunk(sentences)
