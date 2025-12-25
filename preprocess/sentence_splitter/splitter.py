"""
Unified sentence splitting interface.
Refactored pipeline: NLP → Sports Rules → Fallback → Clean
NLP-first architecture for English sports news.
"""

from typing import List
from .nlp_splitter import NLPSplitter
from .sports_rules import SportsRuleAdjuster
from .fallback import FallbackSplitter
from .cleaner import SentenceCleaner


class SentenceSplitter:
    """
    Production-grade sentence splitter for English sports news.
    
    Refactored Pipeline (NLP-First):
    1. NLP-based sentence segmentation (PRIMARY - spaCy)
    2. Sports-aware rule adjustment (POST-PROCESSING)
    3. Fallback length splitting (SAFETY NET)
    4. Output cleaning
    
    Design Principles:
    - NLP first, rules second
    - English-specific, sports-aware
    - Testable, replaceable, extensible
    """
    
    def __init__(self, enable_sports_rules: bool = True, enable_fallback: bool = True):
        """
        Initialize NLP-first splitter pipeline.
        
        Args:
            enable_sports_rules: Apply sports-specific post-processing rules
            enable_fallback: Enable fallback splitting for oversized sentences
        """
        # PRIMARY: NLP sentence segmentation
        self.nlp_splitter = NLPSplitter()
        
        # SECONDARY: Sports-aware rule adjustments (post-processing only)
        self.rule_adjuster = SportsRuleAdjuster() if enable_sports_rules else None
        
        # FALLBACK: Length-based emergency splitting
        self.fallback_splitter = FallbackSplitter() if enable_fallback else None
        
        # CLEANUP: Final output normalization
        self.cleaner = SentenceCleaner()
        
    def split(self, text: str) -> List[str]:
        """
        Split English sports news text into semantically complete sentences.
        
        Args:
            text: Input paragraph (English sports news)
            
        Returns:
            List of clean, semantically complete sentences
        """
        if not text or not text.strip():
            return []
        
        # Step 1: NLP-based sentence segmentation (PRIMARY)
        sentences = self.nlp_splitter.split(text)
        
        if not sentences:
            # NLP failed - return cleaned original or empty
            return [self.cleaner.normalize_single(text)] if text.strip() else []
        
        # Step 2: Sports-aware rule adjustment (POST-PROCESSING)
        # Rules can only merge/fix NLP output, not override segmentation
        if self.rule_adjuster:
            sentences = self.rule_adjuster.adjust(sentences, original_text=text)
        
        # Step 3: Fallback length splitting (SAFETY NET)
        # Only triggers if NLP produces oversized sentences
        if self.fallback_splitter:
            sentences = self.fallback_splitter.split_long_sentences(sentences)
        
        # Step 4: Clean output
        clean_sentences = self.cleaner.clean(sentences)
        
        return clean_sentences
    
    def split_batch(self, texts: List[str]) -> List[List[str]]:
        """
        Split multiple texts.
        
        Args:
            texts: List of input paragraphs
            
        Returns:
            List of sentence lists
        """
        return [self.split(text) for text in texts]
