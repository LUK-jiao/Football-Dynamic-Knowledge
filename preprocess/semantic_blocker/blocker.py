"""
Semantic blocker for grouping sentences into coherent semantic units.

Strategy:
- PRIMARY: Vector-based semantic similarity (sentence-transformers)
- SECONDARY: Rule-based adjustments (subject consistency, discourse markers)
- FALLBACK: Length-based splitting for oversized blocks

Dependencies:
- sentence-transformers: For sentence embeddings
- numpy: For cosine similarity calculation
- spacy: For subject extraction (optional enhancement)
"""

import re
from typing import List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

# Try to import spacy for subject extraction
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None


class SemanticBlocker:
    """
    Semantic blocker using vector similarity and linguistic rules.
    
    Pipeline:
    1. Vectorize sentences using sentence-transformers
    2. Calculate pairwise semantic similarity
    3. Apply rule-based adjustments (subject, discourse markers)
    4. Merge high-similarity consecutive sentences into blocks
    5. Split oversized blocks using fallback strategy
    6. Clean and normalize output
    """
    
    # Discourse markers that signal block boundaries
    BLOCK_BOUNDARY_MARKERS = {
        # Contrast/transition
        'however', 'nevertheless', 'nonetheless', 'meanwhile', 'conversely',
        'on the other hand', 'in contrast', 'by contrast',
        
        # Temporal transitions
        'later', 'subsequently', 'afterwards', 'then', 'next',
        'earlier', 'previously', 'before that',
        
        # Topic shift
        'separately', 'elsewhere', 'in other news', 'additionally',
        'furthermore', 'moreover', 'on another note',
    }
    
    # Time expressions that signal new events
    TIME_EXPRESSIONS = [
        r'\b\d{4}\b',  # Year: 2024
        r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(last|next|this)\s+(week|month|year|season)\b',
        r'\bin\s+the\s+\d+th\s+minute\b',  # Sports: in the 78th minute
    ]
    
    def __init__(
        self,
        # model_name: str = 'all-MiniLM-L6-v2',
        model_name: str = 'all-mpnet-base-v2',
        similarity_threshold: float = 0.5,
        max_block_length: int = 400,
        use_subject_matching: bool = True
    ):
        """
        Initialize semantic blocker.
        
        Args:
            model_name: Sentence transformer model name
            similarity_threshold: Cosine similarity threshold for merging (0-1)
            max_block_length: Maximum characters per block before fallback split
            use_subject_matching: Enable subject consistency checking
        """
        self.similarity_threshold = similarity_threshold
        self.max_block_length = max_block_length
        self.use_subject_matching = use_subject_matching
        
        # Initialize sentence transformer model
        if TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception as e:
                print(f"Warning: Failed to load transformer model: {e}")
                self.model = None
        else:
            print("Warning: sentence-transformers not available. Install with: pip install sentence-transformers")
            self.model = None
        
        # Initialize spaCy for subject extraction (optional)
        self.nlp = None
        if use_subject_matching and SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except Exception:
                print("Warning: spaCy model not available. Subject matching disabled.")
    
    def block(self, sentences: List[str]) -> List[str]:
        """
        Group sentences into semantic blocks.
        
        Args:
            sentences: List of sentences from sentence_splitter
            
        Returns:
            List of semantic blocks (merged sentences)
        """
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [self._clean_block(sentences[0])]
        
        # Step 1: Calculate semantic similarities
        similarities = self._calculate_similarities(sentences)
        
        # Step 2: Apply rule-based adjustments
        merge_decisions = self._apply_rules(sentences, similarities)
        
        # Step 3: Merge sentences into blocks based on decisions
        blocks = self._merge_into_blocks(sentences, merge_decisions)
        
        # Step 4: Split oversized blocks
        blocks = self._split_long_blocks(blocks)
        
        # Step 5: Clean output
        blocks = [self._clean_block(block) for block in blocks if block.strip()]
        
        return blocks
    
    def _calculate_similarities(self, sentences: List[str]) -> np.ndarray:
        """
        Calculate pairwise semantic similarities using sentence embeddings.
        
        Returns:
            Array of shape (n-1,) with similarity scores between consecutive sentences
        """
        if not self.model:
            # Fallback: return low similarities (will rely on rules only)
            return np.zeros(len(sentences) - 1)
        
        try:
            # Encode all sentences
            embeddings = self.model.encode(sentences, convert_to_numpy=True)
            
            # Calculate cosine similarity between consecutive sentences
            similarities = []
            for i in range(len(embeddings) - 1):
                sim = cosine_similarity(
                    embeddings[i].reshape(1, -1),
                    embeddings[i + 1].reshape(1, -1)
                )[0][0]
                similarities.append(sim)
            
            return np.array(similarities)
        except Exception as e:
            print(f"Warning: Similarity calculation failed: {e}")
            return np.zeros(len(sentences) - 1)
    
    def _apply_rules(self, sentences: List[str], similarities: np.ndarray) -> List[bool]:
        """
        Apply linguistic rules to adjust merge decisions.
        
        Args:
            sentences: List of sentences
            similarities: Similarity scores between consecutive sentences
            
        Returns:
            List of boolean decisions: True = merge with next, False = boundary
        """
        decisions = []
        
        for i in range(len(sentences) - 1):
            current = sentences[i]
            next_sent = sentences[i + 1]
            base_similarity = similarities[i]
            
            # Start with base similarity decision
            should_merge = base_similarity >= self.similarity_threshold
            
            # Rule 1: Block boundary markers - force split
            if self._has_boundary_marker(next_sent):
                should_merge = False
            
            # Rule 2: Time expression shift - force split
            elif self._has_time_shift(current, next_sent):
                should_merge = False
            
            # Rule 3: Subject consistency - boost merge
            elif self.use_subject_matching and self._same_subject(current, next_sent):
                # If subjects match, be more aggressive in merging
                should_merge = should_merge or base_similarity >= (self.similarity_threshold - 0.1)
            
            # Rule 4: Length check - prevent oversized blocks
            elif len(current) + len(next_sent) > self.max_block_length:
                should_merge = False
            
            decisions.append(should_merge)
        
        return decisions
    
    def _has_boundary_marker(self, sentence: str) -> bool:
        """Check if sentence starts with a discourse boundary marker."""
        sentence_lower = sentence.lower().strip()
        
        for marker in self.BLOCK_BOUNDARY_MARKERS:
            if sentence_lower.startswith(marker):
                return True
        
        return False
    
    def _has_time_shift(self, sent1: str, sent2: str) -> bool:
        """
        Detect significant time shift between sentences.
        Indicates a new event or scene.
        """
        for pattern in self.TIME_EXPRESSIONS:
            if re.search(pattern, sent2.lower()) and not re.search(pattern, sent1.lower()):
                # sent2 introduces new time context not in sent1
                return True
        
        return False
    
    def _same_subject(self, sent1: str, sent2: str) -> bool:
        """
        Check if two sentences have the same subject.
        Uses spaCy for subject extraction.
        """
        if not self.nlp:
            return False
        
        try:
            doc1 = self.nlp(sent1)
            doc2 = self.nlp(sent2)
            
            # Extract subjects (nsubj or nsubjpass)
            subj1 = [token.text.lower() for token in doc1 if token.dep_ in ('nsubj', 'nsubjpass')]
            subj2 = [token.text.lower() for token in doc2 if token.dep_ in ('nsubj', 'nsubjpass')]
            
            if not subj1 or not subj2:
                return False
            
            # Check for overlap
            return bool(set(subj1) & set(subj2))
        except Exception:
            return False
    
    def _merge_into_blocks(self, sentences: List[str], merge_decisions: List[bool]) -> List[str]:
        """
        Merge sentences into blocks based on merge decisions.
        
        Args:
            sentences: List of sentences
            merge_decisions: List of booleans indicating merge with next
            
        Returns:
            List of merged blocks
        """
        blocks = []
        current_block = sentences[0]
        
        for i, should_merge in enumerate(merge_decisions):
            if should_merge:
                # Merge with next sentence
                current_block += " " + sentences[i + 1]
            else:
                # End current block, start new one
                blocks.append(current_block)
                current_block = sentences[i + 1]
        
        # Add the last block
        if current_block:
            blocks.append(current_block)
        
        return blocks
    
    def _split_long_blocks(self, blocks: List[str]) -> List[str]:
        """
        Split blocks that exceed maximum length.
        Uses simple strategy: split at sentence boundaries or punctuation.
        """
        result = []
        
        for block in blocks:
            if len(block) <= self.max_block_length:
                result.append(block)
            else:
                # Try to split at periods (sentence boundaries)
                sub_blocks = self._split_at_periods(block)
                result.extend(sub_blocks)
        
        return result
    
    def _split_at_periods(self, text: str) -> List[str]:
        """
        Split long block at period boundaries.
        Fallback strategy for oversized blocks.
        """
        # First try to split at periods followed by space and capital letter
        pattern = r'(?<=[.!?])\s+(?=[A-Z])'
        parts = re.split(pattern, text)
        
        # Ensure no part exceeds max length
        result = []
        current = ""
        
        for part in parts:
            if not current:
                current = part
            elif len(current) + len(part) + 1 <= self.max_block_length:
                current += " " + part
            else:
                # Current would be too long, save it and start new
                if len(current) > self.max_block_length:
                    # Current itself is too long, need to force split
                    result.extend(self._force_split_by_words(current))
                else:
                    result.append(current)
                current = part
        
        if current:
            if len(current) > self.max_block_length:
                result.extend(self._force_split_by_words(current))
            else:
                result.append(current)
        
        return result
    
    def _force_split_by_words(self, text: str) -> List[str]:
        """
        Force split text at word boundaries when no sentence boundaries available.
        Last resort for extremely long blocks.
        """
        if len(text) <= self.max_block_length:
            return [text]
        
        result = []
        words = text.split()
        current = ""
        
        for word in words:
            if not current:
                current = word
            elif len(current) + len(word) + 1 <= self.max_block_length:
                current += " " + word
            else:
                result.append(current)
                current = word
        
        if current:
            result.append(current)
        
        return result
    
    def _clean_block(self, block: str) -> str:
        """
        Clean and normalize a semantic block.
        
        Operations:
        - Strip whitespace
        - Normalize multiple spaces
        - Remove extra punctuation
        """
        # Strip leading/trailing whitespace
        block = block.strip()
        
        # Normalize multiple spaces
        block = re.sub(r'\s+', ' ', block)
        
        # Remove multiple consecutive punctuation (except ellipsis)
        block = re.sub(r'([.!?,;:])\1+', r'\1', block)
        
        # Ensure proper spacing after punctuation
        block = re.sub(r'([.!?,;:])([A-Za-z])', r'\1 \2', block)
        
        return block


# ============================================================================
# Convenience Function
# ============================================================================

def semantic_block(
    sentences: List[str],
    similarity_threshold: float = 0.6,
    max_block_length: int = 400,
    model_name: str = 'all-MiniLM-L6-v2'
) -> List[str]:
    """
    Convenience function for semantic blocking.
    
    Args:
        sentences: List of sentences from sentence_splitter
        similarity_threshold: Cosine similarity threshold for merging (0-1)
        max_block_length: Maximum characters per block
        model_name: Sentence transformer model name
        
    Returns:
        List of semantic blocks
        
    Example:
        >>> from preprocess.sentence_splitter import SentenceSplitter
        >>> from preprocess.semantic_blocker import semantic_block
        >>> 
        >>> splitter = SentenceSplitter()
        >>> text = "Chelsea won 3-2. The team celebrated. However, injuries remain a concern."
        >>> sentences = splitter.split(text)
        >>> blocks = semantic_block(sentences)
        >>> print(blocks)
        ['Chelsea won 3-2. The team celebrated.', 'However, injuries remain a concern.']
    """
    blocker = SemanticBlocker(
        model_name=model_name,
        similarity_threshold=similarity_threshold,
        max_block_length=max_block_length
    )
    return blocker.block(sentences)
