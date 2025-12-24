"""
NLP-based sentence splitter (Validation Layer).
Uses spaCy for sentence boundary detection.
"""

from typing import List, Optional
import warnings


class NLPSplitter:
    """Wrapper for spaCy sentence boundary detection."""
    
    def __init__(self):
        self.nlp = None
        self._initialize_spacy()
    
    def _initialize_spacy(self):
        """Initialize spaCy model lazily."""
        try:
            import spacy
            try:
                # Try to load English model
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                warnings.warn(
                    "spaCy model 'en_core_web_sm' not found. "
                    "Install with: python -m spacy download en_core_web_sm"
                )
                self.nlp = None
        except ImportError:
            warnings.warn("spaCy not installed. NLP splitting disabled.")
            self.nlp = None
    
    def split(self, text: str) -> Optional[List[str]]:
        """
        Split text using spaCy sentence segmentation.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences or None if spaCy unavailable
        """
        if not self.nlp:
            return None
        
        if not text or not text.strip():
            return []
        
        doc = self.nlp(text.strip())
        sentences = [sent.text.strip() for sent in doc.sents]
        
        return sentences
    
    def is_available(self) -> bool:
        """Check if NLP splitter is available."""
        return self.nlp is not None
