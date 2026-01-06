# Text Preprocessing Module

Complete text preprocessing pipeline for the Football Dynamic Knowledge system.

## Overview

This module provides a two-stage text processing pipeline:

```
Raw Text → [Sentence Splitter] → Sentences → [Semantic Chunker] → Semantic Chunks
```

### Stage 1: Sentence Splitting
- Uses spaCy for accurate sentence boundary detection
- Handles quotes, abbreviations, and edge cases
- Simple, fast, reliable

### Stage 2: Semantic Chunking
- Uses LLM (Ollama/OpenAI) as binary boundary classifier
- Outputs: `SAME_UNIT` or `NEW_UNIT`
- Robust fallback on LLM failures
- Deterministic behavior

## Quick Start

### Installation

```bash
# Install dependencies
pip install spacy requests

# Download spaCy model
python -m spacy download en_core_web_sm

# Ensure Ollama is running
ollama serve
ollama pull llama3:latest
```

### Basic Usage

```python
from preprocess.sentence_splitter import SentenceSplitter
from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

# Raw text
text = """
Arsenal won 2-1. Saka scored the winner. 
Manager Arteta was delighted with the result.
"""

# Stage 1: Split into sentences
splitter = SentenceSplitter()
sentences = splitter.split(text)
# Result: ["Arsenal won 2-1.", "Saka scored the winner.", ...]

# Stage 2: Chunk semantically
backend = OllamaBackend(model="llama3:latest")
chunks = semantic_chunk(sentences, backend)
# Result: [["Arsenal won 2-1.", "Saka scored the winner."], [...]]
```

## Module Structure

```
preprocess/
├── integration_test.py              # End-to-end pipeline test
│
├── sentence_splitter/
│   ├── __init__.py
│   ├── splitter.py                  # SentenceSplitter class
│   └── README.md                    # Detailed documentation
│
└── semantic_blocker/
    ├── __init__.py
    ├── semantic_chunker.py          # Core chunker logic
    ├── ollama_backend.py            # LLM backend implementations
    ├── llm_aggregator.py            # Legacy event aggregator (deprecated)
    ├── test_semantic_chunker.py     # Unit tests
    ├── example_refactored.py        # Usage examples
    ├── comparison.py                # Old vs new comparison
    └── README.md                    # Detailed documentation
```

## Integration Test

Run the complete pipeline test:

```bash
# Using virtual environment
.venv/bin/python preprocess/integration_test.py

# Or system Python
python3 preprocess/integration_test.py
```

Expected output:
```
================================================================================
INTEGRATION TEST: Sentence Splitter + Semantic Chunker
================================================================================

[TEST 1] Football Match Report
  ✓ Split into 11 sentences
  ✓ Created 2 semantic chunks

[TEST 2] Mixed Topics
  ✓ Split into 7 sentences
  ✓ Created 3 semantic chunks

[VALIDATION]
  ✓ Should produce sentences
  ✓ Should produce chunks
  ✓ Should aggregate some sentences
  ✓ All sentences should be in chunks

✓ ALL INTEGRATION TESTS PASSED
```

## Features

### Sentence Splitter
- ✅ spaCy-based sentence boundary detection
- ✅ Quote aggregation for interviews
- ✅ Whitespace normalization
- ✅ Deduplication
- ✅ Minimum length filtering

### Semantic Chunker
- ✅ LLM as binary classifier (not generator)
- ✅ Sliding window architecture
- ✅ Conservative fallback strategy
- ✅ Deterministic behavior (temp=0)
- ✅ Backend-agnostic (Ollama, OpenAI, custom)
- ✅ Comprehensive error handling
- ✅ Statistics tracking

## Configuration

### Sentence Splitter

```python
splitter = SentenceSplitter(
    model_name="en_core_web_sm",  # spaCy model
    min_length=10                  # Minimum sentence length
)
```

### Semantic Chunker

```python
from preprocess.semantic_blocker import ChunkerConfig

config = ChunkerConfig(
    window_size=1,              # Compare with N previous sentences
    force_new_on_failure=True,  # Conservative fallback
    log_failures=True,          # Log fallback events
    max_context_length=500      # Max context chars for LLM
)

chunker = SemanticChunker(backend, config)
```

## Performance

| Stage | Speed | Quality |
|-------|-------|---------|
| Sentence Splitting | ~0.01s per paragraph | Excellent (spaCy) |
| Semantic Chunking | ~1-2s per decision | Excellent (LLM) |

## Testing

### Unit Tests
```bash
# Test semantic chunker
.venv/bin/python preprocess/semantic_blocker/test_semantic_chunker.py
# Expected: 11/11 tests pass
```

### Integration Test
```bash
# Test full pipeline
.venv/bin/python preprocess/integration_test.py
# Expected: All tests pass
```

### Examples
```bash
# Run semantic chunker examples
.venv/bin/python preprocess/semantic_blocker/example_refactored.py

# Compare old vs new system
.venv/bin/python preprocess/semantic_blocker/comparison.py
```

## Design Philosophy

### Simplicity Over Complexity
- Each module does one thing well
- Clear separation of concerns
- Easy to understand and maintain

### Robustness Over Perfection
- Conservative fallback strategies
- Comprehensive error handling
- No silent failures

### Determinism Over Creativity
- Same input → same output
- No randomness in production
- Predictable behavior

## Troubleshooting

### spaCy model not found
```bash
python -m spacy download en_core_web_sm
```

### Cannot connect to Ollama
```bash
# Start Ollama server
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### High fallback rate
- Check Ollama server logs
- Try increasing timeout
- Consider using more capable model

## Future Enhancements

Potential improvements (not currently implemented):
- [ ] Batch processing for better throughput
- [ ] Caching for repeated inputs
- [ ] Multi-language support
- [ ] Confidence scoring
- [ ] Async processing

## Documentation

- **Sentence Splitter**: See `sentence_splitter/README.md`
- **Semantic Chunker**: See `semantic_blocker/README.md`
- **Integration Test**: See `integration_test.py` source code

## Version History

### v2.0.0 (Current)
- ✨ Refactored semantic chunker as binary classifier
- ✨ Added Ollama backend support
- ✨ Comprehensive testing and documentation
- ✨ Integration test for full pipeline
- 🗑️ Cleaned up redundant files

### v1.0.0
- Initial implementation with event aggregation
- OpenAI backend only
- Complex event taxonomy

## License

Same as parent project (Football Dynamic Knowledge).

---

**Last Updated**: 2026-01-06
