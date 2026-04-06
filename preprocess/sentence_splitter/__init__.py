"""
Simple and effective sentence splitting module.
Uses spaCy for accurate sentence boundary detection.
"""

from .splitter import SentenceSplitter
from preprocess.contracts import PreChunkInput

__all__ = ['SentenceSplitter', 'PreChunkInput']
