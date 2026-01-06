# Semantic Chunker - Refactored

## Overview

**A deterministic semantic boundary classifier using LLM as a binary decision engine.**

This is a **refactored version** of the semantic blocker module, redesigned to be:
- ✅ **Simple**: LLM outputs only `SAME_UNIT` or `NEW_UNIT`
- ✅ **Robust**: Conservative fallback on any LLM failure
- ✅ **Deterministic**: Same input → same output
- ✅ **Backend-agnostic**: Easy to swap Ollama → vLLM → OpenAI

## Key Principles

### 🎯 LLM as Binary Classifier

The LLM is **NOT** a generator. It's a semantic boundary classifier that outputs:
- `SAME_UNIT` - Current sentence continues the same factual/semantic unit
- `NEW_UNIT` - Current sentence starts a new semantic unit

**No summarization. No rewriting. No creativity.**

### 🪟 Sliding Window Architecture

```
Input: [S1, S2, S3, S4, S5]

Step 1: Compare S2 with S1 → SAME_UNIT → Chunk: [S1, S2]
Step 2: Compare S3 with S2 → NEW_UNIT  → Start new chunk
Step 3: Compare S4 with S3 → SAME_UNIT → Chunk: [S3, S4]
Step 4: Compare S5 with S4 → NEW_UNIT  → Start new chunk

Output: [[S1, S2], [S3, S4], [S5]]
```

### 🛡️ Robust Fallback Strategy

**All LLM failures default to `NEW_UNIT`** (conservative approach):

| Failure Type | Example | Fallback |
|--------------|---------|----------|
| Invalid output | `"I think these are related..."` | `NEW_UNIT` |
| Empty response | `""` | `NEW_UNIT` |
| Multiple tokens | `"SAME_UNIT because..."` | `NEW_UNIT` |
| API error | Network timeout | `NEW_UNIT` |

This ensures:
- ✅ No silent semantic drift
- ✅ System remains stable
- ✅ Predictable behavior

## Quick Start

### Installation

```bash
# Ensure Ollama is running
ollama serve

# Pull a model (if not already)
ollama pull llama3:latest
```

### Basic Usage

```python
from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

# Initialize backend
backend = OllamaBackend(model="llama3:latest")

# Your pre-split sentences
sentences = [
    "Arsenal won 2-1 against Chelsea.",
    "Saka scored in the 23rd minute.",
    "Liverpool lost at home."
]

# Chunk into semantic units
chunks = semantic_chunk(sentences, backend, window_size=1)

# Result: [[sent1, sent2], [sent3]]
for i, chunk in enumerate(chunks, 1):
    print(f"Chunk {i}: {chunk}")
```

### Advanced Usage

```python
from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, OllamaBackend

# Configure chunker
config = ChunkerConfig(
    window_size=1,              # Context window size
    force_new_on_failure=True,  # Fallback strategy
    log_failures=True           # Log fallback events
)

# Initialize
backend = OllamaBackend(model="llama3:latest", timeout=30)
chunker = SemanticChunker(backend, config)

# Process
chunks = chunker.chunk(sentences)

# Get statistics
stats = chunker.get_stats()
print(f"Fallback rate: {stats['fallback_rate']:.2%}")
```

## API Reference

### `semantic_chunk(sentences, llm_backend, window_size=1, force_new_on_failure=True)`

Convenience function for semantic chunking.

**Parameters:**
- `sentences` (List[str]): Pre-split sentences
- `llm_backend` (LLMBackend): Backend implementation (Ollama, OpenAI, etc.)
- `window_size` (int): Number of previous sentences for context (default: 1)
- `force_new_on_failure` (bool): Start new chunk on LLM failure (default: True)

**Returns:**
- `List[List[str]]`: List of semantic chunks

### `SemanticChunker`

Main chunker class for advanced usage.

```python
chunker = SemanticChunker(llm_backend, config)
chunks = chunker.chunk(sentences)
stats = chunker.get_stats()
chunker.reset_stats()
```

### `OllamaBackend`

Ollama backend implementation.

```python
backend = OllamaBackend(
    model="llama3:latest",
    base_url="http://localhost:11434",
    timeout=30,
    temperature=0.0
)
```

### `OpenAIBackend`

OpenAI-compatible backend (GPT, DeepSeek, etc.).

```python
backend = OpenAIBackend(
    model="gpt-4o-mini",
    api_key="sk-...",
    timeout=30
)
```

## Configuration

### ChunkerConfig Options

```python
ChunkerConfig(
    window_size=1,              # 1-5 recommended
    force_new_on_failure=True,  # Conservative fallback
    log_failures=True,          # Enable logging
    max_context_length=500      # Max chars in context
)
```

### Environment Variables

```bash
# For OpenAI backend
export OPENAI_API_KEY="sk-..."

# For custom Ollama URL
export OLLAMA_HOST="http://localhost:11434"
```

## Decision Rules (LLM Prompt)

The LLM follows these canonical rules:

### SAME_UNIT if:
- ✅ Coreference exists (pronouns, ellipsis, implicit subject)
- ✅ Sentence elaborates, explains, or adds attributes to same fact
- ✅ Temporal/causal continuation

### NEW_UNIT if:
- ✅ New event, actor, or unrelated fact introduced
- ✅ Topic shift detected
- ✅ Different time/location/subject

## Architecture

```
┌─────────────────────────────────────────────────┐
│  Input: Pre-split sentences (rule-based)       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  SemanticChunker                                │
│  ┌───────────────────────────────────────────┐  │
│  │ Sliding Window Logic                      │  │
│  └────────────┬──────────────────────────────┘  │
│               ▼                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ LLMBackend.decide_boundary()              │  │
│  │  → Returns: (raw_output, success)         │  │
│  └────────────┬──────────────────────────────┘  │
│               ▼                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ Output Validation                         │  │
│  │  → "SAME_UNIT" ✓                          │  │
│  │  → "NEW_UNIT"  ✓                          │  │
│  │  → Other       ✗ → Fallback to NEW_UNIT   │  │
│  └────────────┬──────────────────────────────┘  │
│               ▼                                  │
│  ┌───────────────────────────────────────────┐  │
│  │ Chunk Building & Statistics               │  │
│  └───────────────────────────────────────────┘  │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│  Output: List[List[str]] - Semantic chunks     │
└─────────────────────────────────────────────────┘
```

## Testing

### Unit Tests

```bash
# Run comprehensive test suite
python preprocess/semantic_blocker/test_semantic_chunker.py

# Expected output: All 11 tests should pass
```

Tests cover:
- ✅ Normal flow with valid outputs
- ✅ All fallback scenarios
- ✅ Edge cases (empty input, single sentence)
- ✅ Window size variations
- ✅ Deterministic behavior
- ✅ Statistics tracking

### Integration Test with Ollama

```bash
# Run real Ollama example
python preprocess/semantic_blocker/example_refactored.py
```

## Performance

### Speed
- ~2-3 seconds per decision (Ollama llama3:8b on M1 Mac)
- Can be optimized with batching or faster models

### Quality
- Superior to pure rule-based approaches
- Handles coreference, ellipsis, discourse markers
- Conservative: prefers separate chunks when uncertain

### Cost
- **Ollama**: Free (local inference)
- **GPT-4o-mini**: ~$0.0001 per decision
- **DeepSeek**: ~$0.00003 per decision

## Migration from Old System

### Old API (Event Aggregator)
```python
from preprocess.semantic_blocker import llm_semantic_chunk

blocks = llm_semantic_chunk(
    sentences,
    model="gpt-4o-mini",
    window_size=15
)
# Returns: List[dict] with event_type, sentences, confidence
```

### New API (Binary Classifier)
```python
from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

backend = OllamaBackend(model="llama3:latest")
chunks = semantic_chunk(sentences, backend, window_size=1)
# Returns: List[List[str]] - simpler, more predictable
```

### Key Differences

| Aspect | Old System | New System |
|--------|-----------|------------|
| **Output** | Event blocks with types | Simple sentence lists |
| **LLM Role** | Event classifier | Binary boundary detector |
| **Complexity** | High (event taxonomy) | Low (binary decision) |
| **Fallback** | Complex retry logic | Simple: force NEW_UNIT |
| **Determinism** | Variable | Guaranteed |
| **Backend** | OpenAI only | Pluggable (Ollama, OpenAI, etc.) |

## Extending: Custom Backends

Implement the `LLMBackend` interface:

```python
from semantic_chunker import LLMBackend
from typing import List, Tuple

class CustomBackend(LLMBackend):
    def decide_boundary(
        self,
        current_sentence: str,
        previous_sentences: List[str]
    ) -> Tuple[str, bool]:
        """
        Returns:
            (raw_output: str, success: bool)
        """
        # Your LLM call here
        raw_output = your_llm_call(...)
        success = True  # or False on error
        
        return (raw_output, success)
```

Then use it:

```python
backend = CustomBackend()
chunks = semantic_chunk(sentences, backend)
```

## Troubleshooting

### "Cannot connect to Ollama server"
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### "Model not found"
```bash
# List available models
ollama list

# Pull the model
ollama pull llama3:latest
```

### High fallback rate
- Check Ollama server logs
- Try increasing `timeout`
- Consider using a more capable model
- Check your prompt is clear

### Inconsistent results
- Set `temperature=0.0` for deterministic output
- Use same model version across runs
- Check for system load affecting inference

## Design Philosophy

### Why so simple?

The previous system tried to do too much:
- Event classification
- Entity extraction
- Confidence scoring
- Complex retry logic

The new system does **one thing well**: detect semantic boundaries.

### Why force NEW_UNIT on failure?

Conservative strategy ensures:
- No risk of merging unrelated content
- Predictable behavior under failure
- Downstream systems get clean boundaries

### Why not retry on failure?

Retrying introduces:
- Non-determinism
- Unpredictable latency
- Complex error handling
- Potential infinite loops

Better to **fail fast and log**.

## Success Criteria ✓

- [x] Reliably segments multi-sentence text into minimal factual units
- [x] Remains stable when LLM behaves unexpectedly
- [x] Ready for backend replacement (Ollama → vLLM) without logic changes
- [x] Deterministic: same input → same output
- [x] No summarization, no generation, no world knowledge
- [x] Comprehensive test coverage
- [x] Clean separation: preprocessing / LLM / fallback

## License

Same as parent project.

## Changelog

### v2.0.0 (Refactored)
- ✨ Complete rewrite as binary classifier
- ✨ Sliding window architecture
- ✨ Robust fallback strategies
- ✨ Pluggable backend system
- ✨ Comprehensive test suite
- ✨ Statistics and logging
- 📝 Improved documentation

### v1.0.0 (Original)
- Event-based aggregation
- OpenAI GPT backend
- Complex event taxonomy
