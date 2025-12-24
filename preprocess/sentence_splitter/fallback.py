"""
Fallback splitter for handling overly long sentences.
Ensures no sentence exceeds maximum length threshold.
"""

import re
from typing import List
from . import config


class FallbackSplitter:
    """Force-split long sentences to prevent downstream issues."""
    
    def split_long_sentences(self, sentences: List[str]) -> List[str]:
        """
        Split any sentence exceeding max length.
        
        Strategy:
        1. Try to split at natural boundaries (commas, conjunctions)
        2. If still too long, split at word boundaries
        3. Preserve semantic integrity as much as possible
        
        Args:
            sentences: Input sentences
            
        Returns:
            Sentences with long ones split
        """
        result = []
        
        for sent in sentences:
            if len(sent) <= config.MAX_SENTENCE_LENGTH:
                result.append(sent)
            else:
                # Long sentence - need to split
                result.extend(self._force_split(sent))
        
        return result
    
    def _force_split(self, text: str) -> List[str]:
        """
        Force split a long sentence at natural boundaries.
        
        Priority:
        1. Split at coordinating conjunctions (but, and with comma)
        2. Split at commas if creates reasonable chunks
        3. Split at word boundaries as last resort
        """
        if len(text) <= config.MAX_SENTENCE_LENGTH:
            return [text]
        
        # Try splitting at conjunctions with preceding comma
        chunks = self._split_at_conjunctions(text)
        if self._is_valid_split(chunks):
            return chunks
        
        # Try splitting at commas
        chunks = self._split_at_commas(text)
        if self._is_valid_split(chunks):
            return chunks
        
        # Last resort: split at word boundaries
        return self._split_at_words(text)
    
    def _split_at_conjunctions(self, text: str) -> List[str]:
        """Split at coordinating conjunctions preceded by comma."""
        # Pattern: comma followed by conjunction
        pattern = r',\s+(but|and|or|yet)\s+'
        
        parts = re.split(pattern, text, flags=re.IGNORECASE)
        
        # Reconstruct with conjunctions
        chunks = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and parts[i + 1].lower() in {'but', 'and', 'or', 'yet'}:
                chunk = parts[i].strip()
                if chunk:
                    chunks.append(chunk)
                # Next part starts with conjunction
                if i + 2 < len(parts):
                    chunks.append(parts[i + 1] + ' ' + parts[i + 2])
                    i += 3
                else:
                    i += 2
            else:
                if parts[i].strip():
                    chunks.append(parts[i].strip())
                i += 1
        
        return chunks
    
    def _split_at_commas(self, text: str) -> List[str]:
        """Split at commas to create roughly equal chunks."""
        parts = text.split(',')
        
        chunks = []
        current = []
        current_len = 0
        
        for part in parts:
            part = part.strip()
            if current_len + len(part) > config.MAX_SENTENCE_LENGTH and current:
                # Flush current chunk
                chunks.append(', '.join(current))
                current = [part]
                current_len = len(part)
            else:
                current.append(part)
                current_len += len(part)
        
        if current:
            chunks.append(', '.join(current))
        
        return chunks
    
    def _split_at_words(self, text: str) -> List[str]:
        """Last resort: split at word boundaries."""
        words = text.split()
        chunks = []
        current = []
        current_len = 0
        
        for word in words:
            if current_len + len(word) + 1 > config.MAX_SENTENCE_LENGTH and current:
                chunks.append(' '.join(current))
                current = [word]
                current_len = len(word)
            else:
                current.append(word)
                current_len += len(word) + 1
        
        if current:
            chunks.append(' '.join(current))
        
        return chunks
    
    def _is_valid_split(self, chunks: List[str]) -> bool:
        """Check if split creates valid chunks."""
        if not chunks:
            return False
        
        # All chunks should be within reasonable bounds
        for chunk in chunks:
            if len(chunk) > config.MAX_SENTENCE_LENGTH:
                return False
            # Avoid creating too-short fragments
            if len(chunk) < config.MIN_SENTENCE_LENGTH:
                return False
        
        return True
