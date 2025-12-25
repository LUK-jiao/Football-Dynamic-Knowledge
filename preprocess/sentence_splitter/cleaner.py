"""
Output cleaner for sentence normalization.
Ensures clean, consistent output for downstream processing.
"""

import re
from typing import List
from . import config


class SentenceCleaner:
    """Clean and normalize sentence output."""
    
    def normalize_single(self, text: str) -> str:
        """
        Normalize a single piece of text.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        return self._normalize(text)
    
    def clean(self, sentences: List[str]) -> List[str]:
        """
        Clean sentence list.
        
        Operations:
        1. Remove empty/whitespace-only sentences
        2. Normalize whitespace
        3. Fix punctuation issues
        4. Merge fragments with previous sentence if needed
        5. Remove duplicates
        6. Filter too-short fragments
        
        Args:
            sentences: Input sentences
            
        Returns:
            Cleaned sentences
        """
        if not sentences:
            return []
        
        # First normalize all sentences
        normalized = [self._normalize(sent) for sent in sentences if sent.strip()]
        
        # Merge fragments that start with invalid words
        merged = self._merge_fragments(normalized)
        
        cleaned = []
        seen = set()
        
        for sent in merged:
            # Skip empty
            if not sent:
                continue
            
            # Skip too short
            if len(sent) < config.MIN_SENTENCE_LENGTH:
                continue
            
            # Skip duplicates
            sent_lower = sent.lower()
            if sent_lower in seen:
                continue
            
            seen.add(sent_lower)
            cleaned.append(sent)
        
        return cleaned
    
    def _merge_fragments(self, sentences: List[str]) -> List[str]:
        """
        Merge sentence fragments with previous sentences.
        Fragments are sentences starting with invalid words or lacking verbs.
        """
        if not sentences:
            return []
        
        result = []
        i = 0
        
        while i < len(sentences):
            sent = sentences[i]
            
            # Check if current sentence is a fragment
            if i > 0 and self._is_fragment(sent):
                # Merge with previous
                if result:
                    # Remove trailing period from previous, merge, add period
                    prev = result[-1].rstrip('.')
                    result[-1] = prev + ' ' + sent
            else:
                result.append(sent)
            
            i += 1
        
        return result
    
    def _is_fragment(self, text: str) -> bool:
        """Check if sentence appears to be a fragment."""
        if not text:
            return True
        
        words = text.split()
        if len(words) < config.MIN_TOKENS:
            return True
        
        first_word = words[0].lower().rstrip('.,;:!?')
        return first_word in config.INVALID_START_WORDS
    
    def _normalize(self, text: str) -> str:
        """Normalize a single sentence."""
        if not text:
            return ""
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize internal whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix multiple punctuation
        text = re.sub(r'([.!?]){2,}', r'\1', text)
        
        # Ensure sentence ends with punctuation
        if text and text[-1] not in '.!?':
            text += '.'
        
        # Remove spaces before punctuation
        text = re.sub(r'\s+([,.!?;:])', r'\1', text)
        
        # Ensure space after punctuation (except at end)
        text = re.sub(r'([,.!?;:])([^\s\d])', r'\1 \2', text)
        
        # Fix quotes
        text = re.sub(r'\s+"', ' "', text)
        text = re.sub(r'"\s+', '" ', text)
        
        return text.strip()
