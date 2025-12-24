"""
Unified sentence splitting interface.
Orchestrates the complete pipeline: Rule → NLP → Resolve → Fallback → Clean.
"""

from typing import List
from .rule_splitter import RuleSplitter
from .nlp_splitter import NLPSplitter
from .resolver import SplitResolver
from .fallback import FallbackSplitter
from .cleaner import SentenceCleaner


class SentenceSplitter:
    """
    Production-grade sentence splitter for fact extraction.
    
    Pipeline:
    1. Rule-based splitting (primary)
    2. NLP validation (optional)
    3. Conflict resolution
    4. Fallback length splitting
    5. Output cleaning
    """
    
    def __init__(self, use_nlp: bool = True):
        """
        Initialize splitter pipeline.
        
        Args:
            use_nlp: Whether to use NLP validation layer
        """
        self.rule_splitter = RuleSplitter()
        self.nlp_splitter = NLPSplitter() if use_nlp else None
        self.resolver = SplitResolver()
        self.fallback_splitter = FallbackSplitter()
        self.cleaner = SentenceCleaner()
        
    def split(self, text: str) -> List[str]:
        """
        Split text into fact-oriented sentences.
        
        Args:
            text: Input paragraph
            
        Returns:
            List of clean, fact-oriented sentences
        """
        if not text or not text.strip():
            return []
        
        # Step 1: Rule-based splitting (PRIMARY)
        rule_sentences = self.rule_splitter.split(text)
        
        # Step 2: NLP validation (OPTIONAL)
        nlp_sentences = None
        if self.nlp_splitter and self.nlp_splitter.is_available():
            nlp_sentences = self.nlp_splitter.split(text)
        
        # Step 3: Conflict resolution
        if nlp_sentences:
            resolved_sentences = self.resolver.resolve(rule_sentences, nlp_sentences)
        else:
            resolved_sentences = rule_sentences
        
        # Step 4: Fallback length splitting
        final_sentences = self.fallback_splitter.split_long_sentences(resolved_sentences)
        
        # Step 5: Clean output
        clean_sentences = self.cleaner.clean(final_sentences)
        
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
