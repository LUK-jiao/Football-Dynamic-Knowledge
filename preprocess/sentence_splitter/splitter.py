"""
Simple and effective sentence splitter using spaCy.
No complex rules needed - spaCy handles everything perfectly.
"""

from typing import List
import warnings


class SentenceSplitter:
    """
    Production-grade sentence splitter for English text.
    
    Philosophy: Keep it simple
    - Use spaCy for sentence boundary detection (it's already excellent)
    - Only do minimal cleaning (whitespace, deduplication)
    - No complex rules or fallbacks needed
    
    Architecture:
    1. spaCy sentence segmentation
    2. Basic cleaning (whitespace normalization, deduplication)
    """
    
    def __init__(self, model_name: str = "en_core_web_sm", min_length: int = 10):
        """
        Initialize sentence splitter.
        
        Args:
            model_name: spaCy model to use
            min_length: Minimum sentence length (filter out fragments)
        """
        self.model_name = model_name
        self.min_length = min_length
        self.nlp = None
        self._load_spacy()
    
    def _load_spacy(self):
        """Load spaCy model."""
        try:
            import spacy
            try:
                self.nlp = spacy.load(self.model_name)
            except OSError:
                warnings.warn(
                    f"spaCy model '{self.model_name}' not found. "
                    f"Install with: python -m spacy download {self.model_name}"
                )
                self.nlp = None
        except ImportError:
            warnings.warn("spaCy not installed. Install with: pip install spacy")
            self.nlp = None
    
    def split(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Input text (English)
            
        Returns:
            List of clean sentences
        """
        if not text or not text.strip():
            return []
        
        if not self.nlp:
            warnings.warn("spaCy not available")
            return [text.strip()]
        
        # Step 1: Use spaCy for sentence segmentation
        doc = self.nlp(text.strip())
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Step 2: Basic cleaning
        cleaned = self._clean(sentences)
        
        return cleaned
    
    def _clean(self, sentences: List[str]) -> List[str]:
        """
        Basic cleaning: normalize whitespace, remove duplicates, filter short fragments.
        
        Args:
            sentences: Input sentences
            
        Returns:
            Cleaned sentences
        """
        if not sentences:
            return []
        
        cleaned = []
        seen = set()
        
        for sent in sentences:
            # Normalize whitespace
            sent = ' '.join(sent.split())
            
            # Skip empty or too short
            if not sent or len(sent) < self.min_length:
                continue
            
            # Skip duplicates (case-insensitive)
            sent_lower = sent.lower()
            if sent_lower in seen:
                continue
            
            seen.add(sent_lower)
            cleaned.append(sent)
        
        return cleaned
    
    def split_batch(self, texts: List[str]) -> List[List[str]]:
        """
        Split multiple texts.
        
        Args:
            texts: List of input paragraphs
            
        Returns:
            List of sentence lists
        """
        return [self.split(text) for text in texts]
