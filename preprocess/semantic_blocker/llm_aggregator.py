"""
LLM-based Event Aggregator for Football News

This module uses LLM to perform event-level semantic aggregation,
replacing the rule-based chunker with intelligent grouping.

Key Principles:
- LLM ONLY groups sentences (does not rewrite/summarize)
- Strict output validation and fallback mechanisms
- Sliding window for long texts
- Full compatibility with existing pipeline

Position in Pipeline:
    Sentence Splitter → [LLM Aggregator] → Fact Extraction
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass
import json
import os
from enum import Enum

# Optional: OpenAI client (can be replaced with other LLM providers)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


# ============================================================================
# Event Types (aligned with taxonomy)
# ============================================================================

class EventType(str, Enum):
    """Event types for semantic blocks."""
    MATCH_RESULT = "match_result"
    GOAL_EVENT = "goal_event"
    PENALTY_SHOOTOUT = "penalty_shootout"
    FIXTURE = "fixture"
    TEAM_PERFORMANCE = "team_performance"
    INDIVIDUAL_PERFORMANCE = "individual_performance"
    MANAGER_STATEMENT = "manager_statement"
    PLAYER_STATEMENT = "player_statement"
    STATISTICS = "statistics"
    BACKGROUND_CONTEXT = "background_context"
    INJURY_EVENT = "injury_event"
    SUBSTITUTION = "substitution"
    CARD_EVENT = "card_event"


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class LLMEventBlock:
    """Event block output from LLM."""
    event_type: str
    sentence_ids: List[int]
    anchor_id: int
    confidence: float = 1.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'event_type': self.event_type,
            'sentence_ids': self.sentence_ids,
            'anchor_id': self.anchor_id,
            'confidence': self.confidence
        }


@dataclass
class SemanticBlock:
    """Final semantic block with sentences."""
    event_type: str
    sentences: List[str]
    anchor_index: int
    confidence: float
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for output."""
        return {
            'event_type': self.event_type,
            'sentences': self.sentences,
            'anchor_index': self.anchor_index,
            'confidence': self.confidence,
            'text': ' '.join(self.sentences),
            'length': len(' '.join(self.sentences)),
            'metadata': self.metadata
        }


# ============================================================================
# LLM Prompts
# ============================================================================

SYSTEM_PROMPT = """You are an event-level semantic aggregation engine for football news.

Your role is strictly limited to grouping sentences that describe the SAME real-world football event.

You do NOT summarize.
You do NOT rewrite text.
You do NOT invent facts.
You do NOT perform entity extraction.

You only group sentence IDs into event blocks."""

USER_PROMPT_TEMPLATE = """Task:
Given a list of pre-split sentences from a football news article, group them into event-level semantic blocks.

Definition:
An "event" is a real-world occurrence such as a match result, a goal, a penalty shootout, a fixture announcement, a manager's statement, or a statistical summary.

Grouping Rules (must follow):
1. Sentences should be grouped if they describe the same occurrence, even if details differ.
2. Sentences connected by pronouns, temporal continuity, or causal relations usually belong to the same event.
3. Direct quotes must be grouped with the event they refer to, not isolated.
4. Prefer fewer, larger event blocks rather than many single-sentence blocks.
5. Do NOT merge unrelated events.

Event Types (choose one per block):
- match_result
- goal_event
- penalty_shootout
- fixture
- team_performance
- individual_performance
- manager_statement
- player_statement
- statistics
- background_context
- injury_event
- substitution
- card_event

Input:
{input_json}

Output Requirements:
- Output ONLY valid JSON.
- Output a JSON array of event blocks.
- Each block must contain:
  - event_type (string from the list above)
  - sentence_ids (array of integers, sorted, representing sentence indices)
  - anchor_id (one sentence id that best represents the event)

Do not include explanations, comments, or extra text. Only output the JSON array."""


# ============================================================================
# LLM Event Aggregator
# ============================================================================

class LLMEventAggregator:
    """
    LLM-based event aggregator.
    
    Uses LLM to intelligently group sentences into event-level semantic blocks.
    Includes validation, fallback, and sliding window support.
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        window_size: int = 15,
        overlap: int = 2,
        temperature: float = 0.1,
        max_retries: int = 2,
        fallback_to_rules: bool = True
    ):
        """
        Initialize LLM aggregator.
        
        Args:
            model: LLM model name
            api_key: OpenAI API key (reads from env if None)
            window_size: Number of sentences per LLM call
            overlap: Sentence overlap between windows
            temperature: LLM temperature (lower = more deterministic)
            max_retries: Max retry attempts on failure
            fallback_to_rules: Use rule-based fallback if LLM fails
        """
        self.model = model
        self.window_size = window_size
        self.overlap = overlap
        self.temperature = temperature
        self.max_retries = max_retries
        self.fallback_to_rules = fallback_to_rules
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE:
            self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        else:
            self.client = None
            print("⚠️  OpenAI not available. Install with: pip install openai")
    
    def aggregate(self, sentences: List[str]) -> List[SemanticBlock]:
        """
        Main aggregation method.
        
        Args:
            sentences: List of sentences from sentence_splitter
            
        Returns:
            List of semantic blocks
        """
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [SemanticBlock(
                event_type=EventType.BACKGROUND_CONTEXT.value,
                sentences=[sentences[0]],
                anchor_index=0,
                confidence=1.0
            )]
        
        # Handle short texts directly
        if len(sentences) <= self.window_size:
            return self._aggregate_window(sentences, offset=0)
        
        # Use sliding window for long texts
        return self._aggregate_with_sliding_window(sentences)
    
    def _aggregate_window(
        self, 
        sentences: List[str],
        offset: int = 0
    ) -> List[SemanticBlock]:
        """
        Aggregate a single window of sentences.
        
        Args:
            sentences: Sentence window
            offset: Global offset for sentence indices
            
        Returns:
            List of semantic blocks
        """
        # Prepare input for LLM
        input_data = {
            "sentences": [
                {"id": i, "text": sent}
                for i, sent in enumerate(sentences)
            ]
        }
        
        # Call LLM
        llm_blocks = self._call_llm(input_data)
        
        # Validate output
        if not self._validate_output(llm_blocks, len(sentences)):
            print(f"⚠️  LLM output validation failed. Using fallback.")
            if self.fallback_to_rules:
                return self._fallback_aggregation(sentences, offset)
            else:
                return []
        
        # Convert to SemanticBlock objects
        semantic_blocks = []
        for block in llm_blocks:
            block_sentences = [sentences[i] for i in block.sentence_ids]
            semantic_blocks.append(SemanticBlock(
                event_type=block.event_type,
                sentences=block_sentences,
                anchor_index=offset + block.anchor_id,
                confidence=block.confidence,
                metadata={'method': 'llm'}
            ))
        
        return semantic_blocks
    
    def _aggregate_with_sliding_window(
        self, 
        sentences: List[str]
    ) -> List[SemanticBlock]:
        """
        Aggregate long text using sliding windows.
        
        Strategy:
        - Split into overlapping windows
        - Aggregate each window
        - Merge overlapping blocks
        """
        all_blocks = []
        i = 0
        
        while i < len(sentences):
            # Define window
            window_end = min(i + self.window_size, len(sentences))
            window = sentences[i:window_end]
            
            # Aggregate window
            window_blocks = self._aggregate_window(window, offset=i)
            all_blocks.extend(window_blocks)
            
            # Move to next window
            i += self.window_size - self.overlap
        
        # Merge overlapping blocks
        merged_blocks = self._merge_overlapping_blocks(all_blocks)
        
        return merged_blocks
    
    def _call_llm(self, input_data: Dict) -> List[LLMEventBlock]:
        """
        Call LLM with retry logic.
        
        Args:
            input_data: Input JSON with sentences
            
        Returns:
            List of LLMEventBlock objects
        """
        if not self.client:
            print("⚠️  LLM client not available")
            return []
        
        for attempt in range(self.max_retries):
            try:
                # Prepare prompt
                user_prompt = USER_PROMPT_TEMPLATE.format(
                    input_json=json.dumps(input_data, ensure_ascii=False, indent=2)
                )
                
                # Call LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    response_format={"type": "json_object"}
                )
                
                # Parse response
                content = response.choices[0].message.content
                blocks_data = json.loads(content)
                
                # Handle different response formats
                if isinstance(blocks_data, dict):
                    # Response might be wrapped in {"blocks": [...]}
                    if "blocks" in blocks_data:
                        blocks_data = blocks_data["blocks"]
                    elif "event_blocks" in blocks_data:
                        blocks_data = blocks_data["event_blocks"]
                    else:
                        # Single block or invalid format
                        blocks_data = [blocks_data] if blocks_data else []
                
                # Convert to LLMEventBlock objects
                llm_blocks = []
                for block_data in blocks_data:
                    llm_blocks.append(LLMEventBlock(
                        event_type=block_data.get('event_type', 'background_context'),
                        sentence_ids=sorted(block_data.get('sentence_ids', [])),
                        anchor_id=block_data.get('anchor_id', 0),
                        confidence=1.0
                    ))
                
                return llm_blocks
                
            except Exception as e:
                print(f"⚠️  LLM call attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return []
        
        return []
    
    def _validate_output(
        self, 
        blocks: List[LLMEventBlock],
        total_sentences: int
    ) -> bool:
        """
        Validate LLM output.
        
        Checks:
        1. All sentence IDs are covered
        2. No duplicate usage of sentences
        3. Event types are valid
        4. Anchor IDs are valid
        """
        if not blocks:
            return False
        
        # Check 1: All sentences covered
        all_ids = set()
        for block in blocks:
            all_ids.update(block.sentence_ids)
        
        expected_ids = set(range(total_sentences))
        if all_ids != expected_ids:
            print(f"⚠️  Validation failed: Missing or extra sentence IDs")
            print(f"   Expected: {expected_ids}")
            print(f"   Got: {all_ids}")
            return False
        
        # Check 2: No duplicates
        all_ids_list = []
        for block in blocks:
            all_ids_list.extend(block.sentence_ids)
        
        if len(all_ids_list) != len(set(all_ids_list)):
            print(f"⚠️  Validation failed: Duplicate sentence IDs")
            return False
        
        # Check 3: Valid event types
        valid_types = {et.value for et in EventType}
        for block in blocks:
            if block.event_type not in valid_types:
                print(f"⚠️  Validation failed: Invalid event type '{block.event_type}'")
                return False
        
        # Check 4: Valid anchor IDs
        for block in blocks:
            if block.anchor_id not in block.sentence_ids:
                print(f"⚠️  Validation failed: Anchor {block.anchor_id} not in sentence_ids")
                return False
        
        return True
    
    def _fallback_aggregation(
        self, 
        sentences: List[str],
        offset: int
    ) -> List[SemanticBlock]:
        """
        Fallback to simple rule-based aggregation.
        
        Strategy: Group by length, keep blocks under 400 chars
        """
        blocks = []
        current = []
        current_length = 0
        
        for i, sent in enumerate(sentences):
            if current_length + len(sent) > 400 and current:
                # Create block
                blocks.append(SemanticBlock(
                    event_type=EventType.BACKGROUND_CONTEXT.value,
                    sentences=current,
                    anchor_index=offset + i - len(current),
                    confidence=0.5,
                    metadata={'method': 'fallback'}
                ))
                current = []
                current_length = 0
            
            current.append(sent)
            current_length += len(sent)
        
        # Last block
        if current:
            blocks.append(SemanticBlock(
                event_type=EventType.BACKGROUND_CONTEXT.value,
                sentences=current,
                anchor_index=offset + len(sentences) - len(current),
                confidence=0.5,
                metadata={'method': 'fallback'}
            ))
        
        return blocks
    
    def _merge_overlapping_blocks(
        self, 
        blocks: List[SemanticBlock]
    ) -> List[SemanticBlock]:
        """
        Merge blocks from overlapping windows.
        
        Strategy:
        - If two blocks have overlapping sentences and same event type, merge
        - Otherwise keep separate
        """
        if not blocks:
            return []
        
        # Sort by anchor index
        blocks = sorted(blocks, key=lambda b: b.anchor_index)
        
        merged = [blocks[0]]
        
        for block in blocks[1:]:
            last = merged[-1]
            
            # Check for overlap
            # (Simplified: just append for now - can be improved)
            merged.append(block)
        
        return merged


# ============================================================================
# Convenience Function
# ============================================================================

def llm_semantic_chunk(
    sentences: List[str],
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    window_size: int = 15
) -> List[Dict]:
    """
    Convenience function for LLM-based semantic chunking.
    
    Args:
        sentences: List of sentences from sentence_splitter
        model: LLM model name
        api_key: OpenAI API key
        window_size: Sentences per LLM call
        
    Returns:
        List of block dictionaries
        
    Example:
        >>> from preprocess.sentence_splitter import SentenceSplitter
        >>> from preprocess.semantic_blocker import llm_semantic_chunk
        >>> 
        >>> splitter = SentenceSplitter()
        >>> text = "Arsenal won 3-2. Haaland scored twice. The team celebrated."
        >>> sentences = splitter.split(text)
        >>> blocks = llm_semantic_chunk(sentences)
        >>> 
        >>> for block in blocks:
        ...     print(f"{block['event_type']}: {block['text']}")
    """
    aggregator = LLMEventAggregator(
        model=model,
        api_key=api_key,
        window_size=window_size
    )
    
    blocks = aggregator.aggregate(sentences)
    return [block.to_dict() for block in blocks]
