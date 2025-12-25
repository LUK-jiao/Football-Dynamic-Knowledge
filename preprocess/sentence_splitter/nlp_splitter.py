"""
NLP-based sentence splitter (PRIMARY LOGIC).
Uses spaCy for accurate English sentence boundary detection.
Designed for sports news text.
"""

from typing import List, Optional
import warnings


class NLPSplitter:
    """
    Primary sentence segmentation using spaCy.
    
    Why spaCy:
    - State-of-art sentence boundary detection for English
    - Handles complex structures: quotes, abbreviations, scores
    - Production-ready and well-maintained
    - Optimized for news text
    
    Recommended models:
    - en_core_web_trf (transformer-based, most accurate)
    - en_core_web_sm (smaller, faster, good enough)
    """
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize spaCy NLP pipeline.
        
        Args:
            model_name: spaCy model to use
        """
        self.model_name = model_name
        self.nlp = None
        self._initialize_spacy()
    
    def _initialize_spacy(self):
        """Load spaCy model with sentence segmentation."""
        try:
            import spacy
            try:
                # Load the specified model
                self.nlp = spacy.load(self.model_name)
                
                # Ensure sentencizer is enabled
                if "sentencizer" not in self.nlp.pipe_names and "parser" not in self.nlp.pipe_names:
                    self.nlp.add_pipe("sentencizer")
                    
            except OSError:
                warnings.warn(
                    f"spaCy model '{self.model_name}' not found. "
                    f"Install with: python -m spacy download {self.model_name}\n"
                    "Falling back to sentencizer."
                )
                # Fallback: create blank English pipeline with sentencizer
                self.nlp = spacy.blank("en")
                self.nlp.add_pipe("sentencizer")
                
        except ImportError:
            warnings.warn(
                "spaCy not installed. NLP splitting disabled.\n"
                "Install with: pip install spacy"
            )
            self.nlp = None
    
    def split(self, text: str) -> List[str]:
        """
        Split text using spaCy sentence boundary detection.
        
        This is the PRIMARY splitting logic. Handles:
        - Complex punctuation (quotes, dashes, colons)
        - Abbreviations (U.S., No., Dr., vs.)
        - Sports scores (3-2, 48.3%)
        - Dialogue and quotes
        
        Args:
            text: Input text (English sports news)
            
        Returns:
            List of sentences detected by spaCy
        """
        if not self.nlp:
            warnings.warn("spaCy not available, returning original text")
            return [text] if text.strip() else []
        
        if not text or not text.strip():
            return []
        
        # Process with spaCy
        doc = self.nlp(text.strip())
        
        # Extract sentences from spaCy doc
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        return sentences
    
    def is_available(self) -> bool:
        """Check if NLP splitter is available and functional."""
        return self.nlp is not None
