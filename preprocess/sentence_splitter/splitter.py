"""
Simple and effective sentence splitter using spaCy.
No complex rules needed - spaCy handles everything perfectly.
"""

from typing import List
import warnings
import re


class SentenceSplitter:
    """
    Production-grade sentence splitter for English text.
    
    Philosophy: Keep it simple
    - Use spaCy for sentence boundary detection (it's already excellent)
    - Only do minimal cleaning (whitespace, deduplication)
    - Quote aggregation for interview/reporting contexts
    
    Architecture:
    1. spaCy sentence segmentation
    2. Quote aggregation (merge quoted speech)
    3. Basic cleaning (whitespace normalization, deduplication)
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
    
    def _separate_quote_endings(self, sentences: List[str]) -> List[str]:
        """
        Separate sentences where a quote ending is mixed with a new sentence.
        
        Example input: '" Kevin De Bruyne has signed...'
        Example output: ['"', 'Kevin De Bruyne has signed...']
        
        Args:
            sentences: Input sentences
            
        Returns:
            Sentences with quote endings separated
        """
        separated = []
        
        for sent in sentences:
            # Check if sentence starts with just a quote mark followed by content
            # Pattern: ^\s*["']\s+[A-Z] (quote mark, whitespace, then capital letter)
            match = re.match(r'^(\s*["\'])\s+([A-Z].*)', sent)
            if match:
                # Split into quote ending and new sentence
                quote_part = match.group(1).strip()
                content_part = match.group(2).strip()
                if content_part:  # Only split if there's actual content
                    separated.append(quote_part)
                    separated.append(content_part)
                    continue
            
            separated.append(sent)
        
        return separated
    
    def _aggregate_quotes(self, sentences: List[str]) -> List[str]:
        """
        Aggregate quoted sentences with their attribution.
        
        When a sentence contains a reporting verb (said, told, admitted, etc.) 
        or ends with a colon before quotes, merge all following quoted sentences
        until the quote truly ends.
        
        Handles journalism-style quotes where each paragraph starts with a new quote mark:
            Example: Coach said: "We played well.
                     "We deserved to win."
        
        Args:
            sentences: Input sentences from spaCy
            
        Returns:
            Sentences with quotes aggregated
        """
        if not sentences:
            return []
        
        # Reporting verbs that typically introduce quotes
        REPORTING_VERBS = {
            'said', 'told', 'admitted', 'claimed', 'stated', 'declared',
            'explained', 'mentioned', 'noted', 'argued', 'insisted',
            'suggested', 'replied', 'responded', 'added', 'continued',
            'praised', 'criticized', 'warned', 'confirmed', 'revealed'
        }
        
        aggregated = []
        i = 0
        
        while i < len(sentences):
            sent = sentences[i]
            
            # Check if this sentence introduces a quote
            has_reporting_verb = any(
                f' {verb} ' in f' {sent.lower()} '
                for verb in REPORTING_VERBS
            )
            has_colon_quote = ':' in sent and ('"' in sent or "'" in sent)
            
            # If has reporting verb/colon+quote, start aggregating
            if has_reporting_verb or has_colon_quote:
                merged = [sent]
                i += 1
                
                # Determine which quote type is active (double " or single ')
                # Priority: double quotes > single quotes
                using_double = '"' in sent
                using_single = "'" in sent and not using_double
                
                # Track if we're inside an open quote
                in_quote = True
                
                # Keep merging sentences that are part of the quote
                while i < len(sentences) and in_quote:
                    next_sent = sentences[i]
                    
                    # Check if this is a NEW standalone attributed quote (e.g., "Arteta: 'quote'")
                    # These should NOT be merged
                    is_new_attribution = ':' in next_sent and ('"' in next_sent or "'" in next_sent)
                    
                    if is_new_attribution:
                        # This is a new standalone quote, don't merge
                        break
                    
                    # Check if next sentence starts with a quote mark (explicit continuation)
                    starts_with_quote = (
                        next_sent.lstrip().startswith('"') if using_double 
                        else next_sent.lstrip().startswith("'")
                    )
                    
                    # Check if it ends with closing quote followed by optional punctuation
                    # Look for patterns like: "  or ."  or !"  or ?"
                    ends_with_quote = False
                    if using_double:
                        # Match quote at end, possibly with whitespace/newline after
                        if '"' in next_sent:
                            # Find the last quote
                            last_quote_pos = next_sent.rfind('"')
                            # Everything after the quote should be whitespace/punctuation
                            after_quote = next_sent[last_quote_pos+1:].strip()
                            # If nothing or only punctuation after quote, it's a closing quote
                            ends_with_quote = not after_quote or all(c in '.!?,;: \n\t' for c in after_quote)
                    else:
                        if "'" in next_sent:
                            last_quote_pos = next_sent.rfind("'")
                            after_quote = next_sent[last_quote_pos+1:].strip()
                            ends_with_quote = not after_quote or all(c in '.!?,;: \n\t' for c in after_quote)
                    
                    # Merge if it's part of the quote
                    if starts_with_quote or (in_quote and not ends_with_quote):
                        merged.append(next_sent)
                        i += 1
                        
                        # Check if we should stop
                        if ends_with_quote:
                            in_quote = False
                            break
                    elif ends_with_quote:
                        # Last sentence of the quote
                        merged.append(next_sent)
                        i += 1
                        in_quote = False
                        break
                    else:
                        # Not part of quote anymore
                        break
                
                # Join the merged sentences
                aggregated.append(' '.join(merged))
            else:
                # No aggregation needed
                aggregated.append(sent)
                i += 1
        
        return aggregated
    
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
        
        # Step 2: Separate mixed quote endings (e.g., '" New sentence' -> ['"', 'New sentence'])
        sentences = self._separate_quote_endings(sentences)
        
        # Step 3: Aggregate quotes (merge quoted sentences back to their attribution)
        sentences = self._aggregate_quotes(sentences)
        
        # Step 4: Basic cleaning
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
