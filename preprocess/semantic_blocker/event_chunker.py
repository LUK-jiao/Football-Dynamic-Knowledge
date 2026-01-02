"""
Event-Driven Semantic Chunker for Football News

This module implements a complete event-driven semantic blocking system
that replaces the similarity-driven approach with event-based aggregation.

Core Philosophy:
- One block = One independently modelable event
- Event anchors drive aggregation (not similarity scores)
- Forward-only merging (no backward dependencies)
- Linguistic rules + event taxonomy (not black-box embeddings)

Pipeline:
1. Event Anchor Detection - Identify event core sentences
2. Dependency Detection - Find dependent/elaboration sentences
3. Forward Aggregation - Merge from anchor to next anchor
4. Block Validation - Ensure coherence and usability
"""

from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import re

from .event_taxonomy import (
    EventType,
    EVENT_TRIGGERS,
    get_event_triggers,
    is_compatible_event,
    DependencyMarkers,
    EventTrigger
)


# ============================================================================
# Data Structures
# ============================================================================

class SentenceRole(Enum):
    """Classification of sentence role in event structure."""
    ANCHOR = "anchor"          # Event core - starts a new block
    DEPENDENT = "dependent"    # Must attach to previous anchor
    INDEPENDENT = "independent" # Can stand alone but might merge


@dataclass
class AnnotatedSentence:
    """Sentence with event analysis annotations."""
    text: str
    index: int
    role: SentenceRole
    event_type: Optional[EventType] = None
    confidence: float = 0.0
    is_quote: bool = False
    has_time_marker: bool = False
    has_entity: bool = False


@dataclass
class SemanticBlock:
    """Event-level semantic block output."""
    event_type: EventType
    sentences: List[str]
    anchor_index: int
    confidence: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for output."""
        return {
            'event_type': self.event_type.value,
            'sentences': self.sentences,
            'anchor_index': self.anchor_index,
            'confidence': self.confidence,
            'text': ' '.join(self.sentences),
            'length': len(' '.join(self.sentences)),
            'metadata': self.metadata
        }


# ============================================================================
# Main Chunker Class
# ============================================================================

class EventDrivenSemanticChunker:
    """
    Event-driven semantic chunker for football news.
    
    Implements 4-stage pipeline:
    1. Sentence classification (anchor/dependent/independent)
    2. Event type detection
    3. Forward aggregation from anchors
    4. Block validation and cleanup
    """
    
    def __init__(
        self,
        max_block_length: int = 500,
        min_confidence: float = 0.3,
        aggressive_merging: bool = False
    ):
        """
        Initialize event-driven chunker.
        
        Args:
            max_block_length: Maximum characters per block
            min_confidence: Minimum confidence to accept event detection
            aggressive_merging: If True, merge more aggressively
        """
        self.max_block_length = max_block_length
        self.min_confidence = min_confidence
        self.aggressive_merging = aggressive_merging
        self.dependency_markers = DependencyMarkers()
    
    def chunk(self, sentences: List[str]) -> List[SemanticBlock]:
        """
        Main chunking pipeline.
        
        Args:
            sentences: List of sentences from sentence_splitter
            
        Returns:
            List of semantic blocks (event-level)
        """
        if not sentences:
            return []
        
        if len(sentences) == 1:
            # Single sentence - detect event and return
            event_type, conf = self._detect_event_type(sentences[0])
            return [SemanticBlock(
                event_type=event_type,
                sentences=[sentences[0]],
                anchor_index=0,
                confidence=conf
            )]
        
        # Stage 1: Classify all sentences
        annotated = self._classify_sentences(sentences)
        
        # Stage 2: Detect event types for anchors
        annotated = self._detect_event_types(annotated)
        
        # Stage 3: Forward aggregation from anchors
        blocks = self._aggregate_forward(annotated)
        
        # Stage 4: Validate and post-process
        blocks = self._validate_blocks(blocks)
        
        return blocks
    
    # ========================================================================
    # Stage 1: Sentence Classification
    # ========================================================================
    
    def _classify_sentences(self, sentences: List[str]) -> List[AnnotatedSentence]:
        """
        Classify each sentence as ANCHOR, DEPENDENT, or INDEPENDENT.
        
        Strategy:
        - Check for event triggers → ANCHOR
        - Check for dependency markers → DEPENDENT
        - Otherwise → INDEPENDENT (may merge if related)
        """
        annotated = []
        
        for i, sent in enumerate(sentences):
            # Check if this is an anchor (has event triggers)
            if self._is_anchor_sentence(sent):
                role = SentenceRole.ANCHOR
            # Check if dependent on previous context
            elif self._is_dependent_sentence(sent, i, sentences):
                role = SentenceRole.DEPENDENT
            else:
                role = SentenceRole.INDEPENDENT
            
            # Additional annotations
            is_quote = self._is_quote_sentence(sent)
            has_time = self._has_time_marker(sent)
            has_entity = self._has_named_entity(sent)
            
            annotated.append(AnnotatedSentence(
                text=sent,
                index=i,
                role=role,
                is_quote=is_quote,
                has_time_marker=has_time,
                has_entity=has_entity
            ))
        
        return annotated
    
    def _is_anchor_sentence(self, sentence: str) -> bool:
        """
        Check if sentence contains event triggers.
        
        An anchor sentence:
        - Has explicit event verbs/keywords
        - Can answer "what happened?"
        - Doesn't require previous context
        """
        sent_lower = sentence.lower()
        
        # Check against all event types
        for event_type in EventType:
            triggers = get_event_triggers(event_type)
            
            # Check verbs
            for verb in triggers.verbs:
                if f' {verb} ' in f' {sent_lower} ' or sent_lower.startswith(f'{verb} '):
                    return True
            
            # Check keywords
            for keyword in triggers.keywords:
                if keyword in sent_lower:
                    return True
            
            # Check patterns
            for pattern in triggers.patterns:
                if re.search(pattern, sent_lower):
                    return True
        
        return False
    
    def _is_dependent_sentence(
        self, 
        sentence: str, 
        index: int, 
        all_sentences: List[str]
    ) -> bool:
        """
        Check if sentence is dependent on previous context.
        
        Dependency signals:
        1. Starts with anaphoric pronoun (this, it, that)
        2. Starts with temporal continuation (when, after)
        3. Lacks independent subject or verb
        4. Statistical/elaboration on previous statement
        5. Causal/result relationship with previous sentence
        6. Quantifier starting without context (two, several, many)
        """
        if index == 0:
            return False  # First sentence can't be dependent
        
        sent_lower = sentence.lower().strip()
        previous_sent = all_sentences[index - 1].lower() if index > 0 else ""
        
        # Signal 1: Anaphoric pronouns
        for pronoun in self.dependency_markers.ANAPHORIC_PRONOUNS:
            if sent_lower.startswith(pronoun + ' '):
                return True
        
        # Signal 2: Temporal continuations
        for marker in self.dependency_markers.TEMPORAL_CONTINUATIONS:
            if sent_lower.startswith(marker + ' '):
                return True
        
        # Signal 3: Elaboration markers with weak verb
        if sent_lower.startswith('the ') or sent_lower.startswith('overall'):
            # Check if has strong event verb
            if not self._has_strong_verb(sentence):
                return True
        
        # Signal 4: Pure statistics (likely elaboration)
        if self._is_pure_statistic(sentence):
            return True
        
        # Signal 5: Quantifier-starting sentences that elaborate on previous event
        # e.g., "Two late goals resulted..." after "Arsenal won"
        quantifier_patterns = [
            r'^(two|three|four|five|several|many|both)\s+',
            r'^a\s+(pair|couple|series)\s+of\s+',
        ]
        for pattern in quantifier_patterns:
            if re.match(pattern, sent_lower):
                # Check if previous sentence was an event
                if self._is_anchor_sentence(all_sentences[index - 1]):
                    return True
        
        # Signal 6: Sentences with result/causal verbs referencing previous action
        result_verbs = ['resulted', 'led to', 'caused', 'made it', 'brought', 'ensured']
        if any(verb in sent_lower for verb in result_verbs):
            # Likely explaining how previous event came about
            return True
        
        # Signal 7: Passive construction referencing implicit subject
        # e.g., "Was ruled out" without explicit subject
        if sent_lower.startswith('was ') or sent_lower.startswith('were '):
            if not self._has_explicit_subject(sentence):
                return True
        
        return False
    
    def _has_strong_verb(self, sentence: str) -> bool:
        """Check if sentence has a strong action verb."""
        strong_verbs = {
            'scored', 'won', 'lost', 'beat', 'said', 'told', 'admitted',
            'played', 'faced', 'defeated', 'drew', 'made', 'took', 'gave',
            'received', 'joined', 'signed', 'moved', 'left', 'arrived'
        }
        sent_lower = sentence.lower()
        return any(f' {verb} ' in f' {sent_lower} ' for verb in strong_verbs)
    
    def _is_pure_statistic(self, sentence: str) -> bool:
        """Check if sentence is primarily a statistic."""
        # Contains percentage or ratio without event context
        has_stat = bool(re.search(r'\b\d+(\.\d+)?%\b', sentence))
        has_stat = has_stat or bool(re.search(r'\b\d+ of \d+\b', sentence))
        
        # But doesn't have strong event verb
        has_event = self._has_strong_verb(sentence)
        
        return has_stat and not has_event
    
    def _is_quote_sentence(self, sentence: str) -> bool:
        """Check if sentence contains quotes."""
        return '"' in sentence or "'" in sentence
    
    def _has_time_marker(self, sentence: str) -> bool:
        """Check if sentence has explicit time marker."""
        time_patterns = [
            r'\bin the \d+th minute\b',
            r'\bat \d+:\d+\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b'
        ]
        sent_lower = sentence.lower()
        return any(re.search(pat, sent_lower) for pat in time_patterns)
    
    def _has_named_entity(self, sentence: str) -> bool:
        """Simple heuristic for named entity detection."""
        # Check for capitalized words that aren't sentence-initial
        words = sentence.split()
        if len(words) < 2:
            return False
        
        # Skip first word (sentence start)
        capitalized_count = sum(1 for w in words[1:] if w and w[0].isupper())
        return capitalized_count >= 1
    
    def _has_explicit_subject(self, sentence: str) -> bool:
        """Check if sentence has an explicit subject before the verb."""
        # Simple heuristic: check if there's a capitalized word or name before verb
        words = sentence.split()
        if len(words) < 2:
            return False
        
        # If first word is "Was" or "Were", check if second word is capitalized
        if words[0].lower() in ['was', 'were']:
            return len(words) > 1 and words[1][0].isupper()
        
        return True
    
    # ========================================================================
    # Stage 2: Event Type Detection
    # ========================================================================
    
    def _detect_event_types(
        self, 
        annotated: List[AnnotatedSentence]
    ) -> List[AnnotatedSentence]:
        """
        Detect event type for anchor sentences.
        """
        for sent in annotated:
            if sent.role == SentenceRole.ANCHOR:
                event_type, confidence = self._detect_event_type(sent.text)
                sent.event_type = event_type
                sent.confidence = confidence
        
        return annotated
    
    def _detect_event_type(self, sentence: str) -> Tuple[EventType, float]:
        """
        Detect the most likely event type for a sentence.
        
        Returns:
            (event_type, confidence_score)
        """
        sent_lower = sentence.lower()
        scores = {}
        
        # Score all event types
        for event_type in EventType:
            triggers = get_event_triggers(event_type)
            score = 0
            
            # Verb matches (highest weight)
            for verb in triggers.verbs:
                if f' {verb} ' in f' {sent_lower} ' or sent_lower.startswith(f'{verb} '):
                    score += 5
            
            # Keyword matches
            for keyword in triggers.keywords:
                if keyword in sent_lower:
                    score += 3
            
            # Pattern matches
            for pattern in triggers.patterns:
                if re.search(pattern, sent_lower):
                    score += 3
            
            # Confidence boosters
            for boost in triggers.confidence_boost:
                if re.search(boost, sent_lower):
                    score += 2
            
            if score > 0:
                scores[event_type] = score
        
        # Get best match
        if not scores:
            return (EventType.GENERAL_NARRATIVE, 0.0)
        
        best_event = max(scores.items(), key=lambda x: x[1])
        event_type = best_event[0]
        raw_score = best_event[1]
        
        # Normalize confidence to 0-1 range
        confidence = min(0.95, raw_score / 15.0)
        
        return (event_type, confidence)
    
    # ========================================================================
    # Stage 3: Forward Aggregation
    # ========================================================================
    
    def _aggregate_forward(
        self, 
        annotated: List[AnnotatedSentence]
    ) -> List[SemanticBlock]:
        """
        Aggregate sentences into blocks using forward-only merging.
        
        Algorithm:
        1. Find all anchor sentences
        2. For each anchor, scan forward until next anchor
        3. Merge compatible dependent/independent sentences
        4. Create semantic block
        """
        blocks = []
        anchor_indices = [
            i for i, sent in enumerate(annotated) 
            if sent.role == SentenceRole.ANCHOR
        ]
        
        # If no anchors found, treat all as general narrative
        if not anchor_indices:
            return self._fallback_chunking(annotated)
        
        # Process each anchor
        for anchor_idx in range(len(anchor_indices)):
            anchor_pos = anchor_indices[anchor_idx]
            anchor_sent = annotated[anchor_pos]
            
            # Define scanning window (up to next anchor)
            next_anchor_pos = (
                anchor_indices[anchor_idx + 1] 
                if anchor_idx + 1 < len(anchor_indices)
                else len(annotated)
            )
            
            # Start block with anchor
            block_sentences = [anchor_sent]
            
            # Scan forward for compatible sentences
            for i in range(anchor_pos + 1, next_anchor_pos):
                candidate = annotated[i]
                
                # Decision: should we merge this sentence?
                if self._should_merge(anchor_sent, candidate, block_sentences):
                    block_sentences.append(candidate)
                else:
                    # Stop at first incompatible sentence
                    # (conservative approach - avoids mixing events)
                    break
            
            # Create semantic block
            block = self._create_block(anchor_sent, block_sentences)
            blocks.append(block)
            
            # Handle remaining sentences before next anchor
            # (sentences that weren't merged)
            last_merged = block_sentences[-1].index
            if last_merged + 1 < next_anchor_pos:
                # Create orphan blocks for unmerged sentences
                orphan_blocks = self._handle_orphans(
                    annotated[last_merged + 1:next_anchor_pos]
                )
                blocks.extend(orphan_blocks)
        
        return blocks
    
    def _should_merge(
        self,
        anchor: AnnotatedSentence,
        candidate: AnnotatedSentence,
        current_block: List[AnnotatedSentence]
    ) -> bool:
        """
        Decide if candidate sentence should merge into current block.
        
        Merge conditions:
        1. Candidate is DEPENDENT → Always merge
        2. Candidate is INDEPENDENT → Merge if:
           - Same event type OR compatible event
           - Block length allows
           - No strong boundary signal
        3. Candidate is ANCHOR → Merge if same event type AND compatible
        """
        # Condition 1: Dependent sentences always merge
        if candidate.role == SentenceRole.DEPENDENT:
            return True
        
        # Check length constraint first
        current_length = sum(len(s.text) for s in current_block)
        if current_length + len(candidate.text) > self.max_block_length:
            return False
        
        # Condition 2: Independent sentences - selective merge
        if candidate.role == SentenceRole.INDEPENDENT:
            # Check event compatibility
            if candidate.event_type:
                if is_compatible_event(anchor.event_type, candidate.event_type):
                    return True
            
            # Check if it's a continuation (e.g., quote)
            if anchor.is_quote and candidate.is_quote:
                return True
            
            # In aggressive mode, merge short independent sentences
            if self.aggressive_merging and len(candidate.text) < 100:
                return True
            
            return False
        
        # Condition 3: Anchor sentences - merge only if SAME event type
        # This allows multiple sentences about the same event to cluster
        if candidate.role == SentenceRole.ANCHOR:
            # Same event type → merge (e.g., multiple penalty sentences)
            if candidate.event_type == anchor.event_type:
                return True
            
            # Compatible event types with strong relationship
            if is_compatible_event(anchor.event_type, candidate.event_type):
                # Only merge if one is a sub-event of the other
                # e.g., GOAL + ASSIST, PENALTY_SHOOTOUT + SAVE
                compatible_pairs = [
                    (EventType.PENALTY_SHOOTOUT, EventType.SAVE),
                    (EventType.PENALTY_SHOOTOUT, EventType.PENALTY_AWARD),
                    (EventType.GOAL, EventType.ASSIST),
                    (EventType.GOAL, EventType.MILESTONE),
                    (EventType.INJURY, EventType.SUBSTITUTION),
                ]
                
                for type1, type2 in compatible_pairs:
                    if (anchor.event_type == type1 and candidate.event_type == type2) or \
                       (anchor.event_type == type2 and candidate.event_type == type1):
                        return True
            
            # Don't merge different event types
            return False
        
        return False
    
    def _create_block(
        self,
        anchor: AnnotatedSentence,
        sentences: List[AnnotatedSentence]
    ) -> SemanticBlock:
        """Create a semantic block from anchor and merged sentences."""
        return SemanticBlock(
            event_type=anchor.event_type,
            sentences=[s.text for s in sentences],
            anchor_index=anchor.index,
            confidence=anchor.confidence,
            metadata={
                'sentence_count': len(sentences),
                'has_quote': any(s.is_quote for s in sentences),
                'has_time_marker': any(s.has_time_marker for s in sentences)
            }
        )
    
    def _handle_orphans(
        self, 
        orphans: List[AnnotatedSentence]
    ) -> List[SemanticBlock]:
        """
        Handle sentences that weren't merged into any anchor block.
        
        Strategy: Create mini-blocks for orphaned sentences
        """
        blocks = []
        
        for orphan in orphans:
            # Detect event type if not already done
            if not orphan.event_type:
                event_type, confidence = self._detect_event_type(orphan.text)
            else:
                event_type = orphan.event_type
                confidence = orphan.confidence
            
            blocks.append(SemanticBlock(
                event_type=event_type,
                sentences=[orphan.text],
                anchor_index=orphan.index,
                confidence=confidence * 0.7,  # Reduce confidence for orphans
                metadata={'orphan': True}
            ))
        
        return blocks
    
    def _fallback_chunking(
        self, 
        annotated: List[AnnotatedSentence]
    ) -> List[SemanticBlock]:
        """
        Fallback when no anchors found - group by length.
        """
        blocks = []
        current = []
        current_length = 0
        
        for sent in annotated:
            if current_length + len(sent.text) > self.max_block_length and current:
                # Create block
                blocks.append(SemanticBlock(
                    event_type=EventType.GENERAL_NARRATIVE,
                    sentences=[s.text for s in current],
                    anchor_index=current[0].index,
                    confidence=0.5,
                    metadata={'fallback': True}
                ))
                current = []
                current_length = 0
            
            current.append(sent)
            current_length += len(sent.text)
        
        # Last block
        if current:
            blocks.append(SemanticBlock(
                event_type=EventType.GENERAL_NARRATIVE,
                sentences=[s.text for s in current],
                anchor_index=current[0].index,
                confidence=0.5,
                metadata={'fallback': True}
            ))
        
        return blocks
    
    # ========================================================================
    # Stage 4: Block Validation
    # ========================================================================
    
    def _validate_blocks(self, blocks: List[SemanticBlock]) -> List[SemanticBlock]:
        """
        Validate and post-process blocks.
        
        Operations:
        1. Split oversized blocks
        2. Merge adjacent compatible blocks
        3. Filter low-confidence blocks
        4. Clean block text
        """
        validated = []
        
        for block in blocks:
            # Check 1: Length validation
            full_text = ' '.join(block.sentences)
            if len(full_text) > self.max_block_length:
                # Split into smaller blocks
                sub_blocks = self._split_oversized_block(block)
                validated.extend(sub_blocks)
            else:
                validated.append(block)
        
        # Check 2: Merge adjacent compatible blocks (optional)
        if self.aggressive_merging:
            validated = self._merge_adjacent_blocks(validated)
        
        # Check 3: Filter low confidence (optional)
        validated = [b for b in validated if b.confidence >= self.min_confidence]
        
        return validated
    
    def _split_oversized_block(self, block: SemanticBlock) -> List[SemanticBlock]:
        """Split a block that exceeds max length."""
        sub_blocks = []
        current_sentences = []
        current_length = 0
        
        for sent in block.sentences:
            if current_length + len(sent) > self.max_block_length and current_sentences:
                # Create sub-block
                sub_blocks.append(SemanticBlock(
                    event_type=block.event_type,
                    sentences=current_sentences,
                    anchor_index=block.anchor_index,
                    confidence=block.confidence * 0.9,
                    metadata={**block.metadata, 'split': True}
                ))
                current_sentences = []
                current_length = 0
            
            current_sentences.append(sent)
            current_length += len(sent)
        
        # Last sub-block
        if current_sentences:
            sub_blocks.append(SemanticBlock(
                event_type=block.event_type,
                sentences=current_sentences,
                anchor_index=block.anchor_index,
                confidence=block.confidence * 0.9,
                metadata={**block.metadata, 'split': True}
            ))
        
        return sub_blocks
    
    def _merge_adjacent_blocks(
        self, 
        blocks: List[SemanticBlock]
    ) -> List[SemanticBlock]:
        """Merge adjacent blocks if compatible and small."""
        if len(blocks) < 2:
            return blocks
        
        merged = []
        i = 0
        
        while i < len(blocks):
            current = blocks[i]
            
            # Try to merge with next
            if i + 1 < len(blocks):
                next_block = blocks[i + 1]
                
                # Merge condition: compatible + combined length OK
                if (is_compatible_event(current.event_type, next_block.event_type) and
                    len(' '.join(current.sentences + next_block.sentences)) <= self.max_block_length):
                    
                    # Merge
                    merged_block = SemanticBlock(
                        event_type=current.event_type,
                        sentences=current.sentences + next_block.sentences,
                        anchor_index=current.anchor_index,
                        confidence=min(current.confidence, next_block.confidence),
                        metadata={'merged': True}
                    )
                    merged.append(merged_block)
                    i += 2  # Skip next
                    continue
            
            merged.append(current)
            i += 1
        
        return merged


# ============================================================================
# Convenience Function
# ============================================================================

def event_based_chunk(
    sentences: List[str],
    max_block_length: int = 500,
    min_confidence: float = 0.3,
    aggressive_merging: bool = False
) -> List[Dict]:
    """
    Convenience function for event-based semantic chunking.
    
    Args:
        sentences: List of sentences from sentence_splitter
        max_block_length: Maximum characters per block
        min_confidence: Minimum confidence threshold
        aggressive_merging: Enable aggressive merging
        
    Returns:
        List of block dictionaries
        
    Example:
        >>> from preprocess.sentence_splitter import SentenceSplitter
        >>> from preprocess.semantic_blocker import event_based_chunk
        >>> 
        >>> splitter = SentenceSplitter()
        >>> text = "Arsenal won 3-2. Haaland scored twice. The team celebrated."
        >>> sentences = splitter.split(text)
        >>> blocks = event_based_chunk(sentences)
        >>> 
        >>> for block in blocks:
        ...     print(f"{block['event_type']}: {block['text']}")
    """
    chunker = EventDrivenSemanticChunker(
        max_block_length=max_block_length,
        min_confidence=min_confidence,
        aggressive_merging=aggressive_merging
    )
    
    blocks = chunker.chunk(sentences)
    return [block.to_dict() for block in blocks]
