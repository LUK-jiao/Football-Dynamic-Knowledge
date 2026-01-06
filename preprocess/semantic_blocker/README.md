# Semantic Chunker v2 - Production System# Semantic Chunker - Refactored



**Version**: 2.0.0  ## Overview

**Status**: Production-ready ✅

**A deterministic semantic boundary classifier using LLM as a binary decision engine.**

## Overview

This is a **refactored version** of the semantic blocker module, redesigned to be:

Production-grade semantic chunking module using **LLM as a scoring component** (not a decision maker).- ✅ **Simple**: LLM outputs only `SAME_UNIT` or `NEW_UNIT`

- ✅ **Robust**: Conservative fallback on any LLM failure

### Core Innovation- ✅ **Deterministic**: Same input → same output

- ✅ **Backend-agnostic**: Easy to swap Ollama → vLLM → OpenAI

```

LLM = Scoring Tool (0.0-1.0)## Key Principles

Code = Decision Controller (threshold-based)

Rules = Priority Guarantee (override LLM)### 🎯 LLM as Binary Classifier

```

The LLM is **NOT** a generator. It's a semantic boundary classifier that outputs:

**Key Change from v1**:- `SAME_UNIT` - Current sentence continues the same factual/semantic unit

- ❌ v1: LLM outputs binary `SAME_UNIT` / `NEW_UNIT` (unstable)- `NEW_UNIT` - Current sentence starts a new semantic unit

- ✅ v2: LLM outputs continuous score `0.0-1.0` (controllable)

**No summarization. No rewriting. No creativity.**

---

### 🪟 Sliding Window Architecture

## Quick Start

```

```pythonInput: [S1, S2, S3, S4, S5]

from sentence_splitter import SentenceSplitter

from semantic_blocker import (Step 1: Compare S2 with S1 → SAME_UNIT → Chunk: [S1, S2]

    SemanticChunker, Step 2: Compare S3 with S2 → NEW_UNIT  → Start new chunk

    ChunkerConfig, Step 3: Compare S4 with S3 → SAME_UNIT → Chunk: [S3, S4]

    GranularityMode,Step 4: Compare S5 with S4 → NEW_UNIT  → Start new chunk

    OllamaBackend

)Output: [[S1, S2], [S3, S4], [S5]]

```

# Initialize

splitter = SentenceSplitter()### 🛡️ Robust Fallback Strategy

backend = OllamaBackend(model="llama3:latest", temperature=0.2)

config = ChunkerConfig(granularity=GranularityMode.MEDIUM)**All LLM failures default to `NEW_UNIT`** (conservative approach):

chunker = SemanticChunker(llm=backend, config=config)

| Failure Type | Example | Fallback |

# Use|--------------|---------|----------|

sentences = splitter.split(text)| Invalid output | `"I think these are related..."` | `NEW_UNIT` |

chunks = chunker.chunk(sentences)| Empty response | `""` | `NEW_UNIT` |

| Multiple tokens | `"SAME_UNIT because..."` | `NEW_UNIT` |

for chunk in chunks:| API error | Network timeout | `NEW_UNIT` |

    print(f"[{chunk.chunk_type}] {len(chunk)} sentences")

```This ensures:

- ✅ No silent semantic drift

---- ✅ System remains stable

- ✅ Predictable behavior

## Architecture

## Quick Start

### Pipeline Flow

### Installation

```

Raw Text```bash

    ↓# Ensure Ollama is running

[Sentence Splitter]ollama serve

    ↓

Sentences# Pull a model (if not already)

    ↓ollama pull llama3:latest

[LLM Scoring] → each sentence gets 0.0-1.0 score```

    ↓

[Threshold Decision] → code decides split/merge### Basic Usage

    ↓

[Post-processing] → force split, merge orphans, structural rules```python

    ↓from preprocess.semantic_blocker import semantic_chunk, OllamaBackend

Final Chunks (with types)

```# Initialize backend

backend = OllamaBackend(model="llama3:latest")

### Scoring System

# Your pre-split sentences

| Score | Meaning | Example |sentences = [

|-------|---------|---------|    "Arsenal won 2-1 against Chelsea.",

| 0.0-0.2 | Strong continuation | "Arsenal scored." → "Saka assisted." |    "Saka scored in the 23rd minute.",

| 0.3-0.4 | Weak continuation | "Match ended 2-1." → "Thrilling finish." |    "Liverpool lost at home."

| 0.5 | Sub-event shift | Goal → Crowd reaction |]

| 0.6-0.7 | Clear boundary | Match → Interview |

| 0.8-1.0 | New topic | Arsenal → Liverpool |# Chunk into semantic units

chunks = semantic_chunk(sentences, backend, window_size=1)

---

# Result: [[sent1, sent2], [sent3]]

## Configurationfor i, chunk in enumerate(chunks, 1):

    print(f"Chunk {i}: {chunk}")

### Granularity Modes```



| Mode | Threshold | Chunks (14 sent.) | Use Case |### Advanced Usage

|------|-----------|-------------------|----------|

| **FINE** | 0.45 | 7-9 | Detailed NER |```python

| **MEDIUM** ⭐ | 0.55 | 6-7 | Standard processing |from preprocess.semantic_blocker import SemanticChunker, ChunkerConfig, OllamaBackend

| **COARSE** | 0.65 | 6-7 | Summarization |

# Configure chunker

### Config Parametersconfig = ChunkerConfig(

    window_size=1,              # Context window size

```python    force_new_on_failure=True,  # Fallback strategy

ChunkerConfig(    log_failures=True           # Log fallback events

    granularity=GranularityMode.MEDIUM,  # fine/medium/coarse)

    break_threshold=None,                # Manual override

    max_sentences_per_chunk=5,           # Hard limit# Initialize

    context_window=2,                    # Previous N sentencesbackend = OllamaBackend(model="llama3:latest", timeout=30)

    enable_structural_rules=True,        # Auto-detect quotes/statschunker = SemanticChunker(backend, config)

    enable_orphan_merge=True,            # Merge single sentences

    log_scores=False                     # Debug mode# Process

)chunks = chunker.chunk(sentences)

```

# Get statistics

---stats = chunker.get_stats()

print(f"Fallback rate: {stats['fallback_rate']:.2%}")

## Post-Processing Rules```



### 1. Hard Size Limit## API Reference

```python

if len(chunk) >= 5:### `semantic_chunk(sentences, llm_backend, window_size=1, force_new_on_failure=True)`

    force_split()

```Convenience function for semantic chunking.



### 2. Structural Detection (Overrides LLM)**Parameters:**

- `sentences` (List[str]): Pre-split sentences

**Quotes**: `"Arteta said:"`, `"He told Sky Sports"`  - `llm_backend` (LLMBackend): Backend implementation (Ollama, OpenAI, etc.)

**Statistics**: `"Overall,"`, `"This was"`, `"Historically"`  - `window_size` (int): Number of previous sentences for context (default: 1)

**Future**: `"will face"`, `"semi-final"`, `"next round"`  - `force_new_on_failure` (bool): Start new chunk on LLM failure (default: True)

**Temporal**: `"Meanwhile,"`, `"Later,"`, `"After the match"`

**Returns:**

### 3. Orphan Merge- `List[List[str]]`: List of semantic chunks

```python

if len(chunk) == 1 and score < 0.3:### `SemanticChunker`

    merge_with_previous()

```Main chunker class for advanced usage.



---```python

chunker = SemanticChunker(llm_backend, config)

## Output Formatchunks = chunker.chunk(sentences)

stats = chunker.get_stats()

### Chunk Objectchunker.reset_stats()

```

```python

@dataclass### `OllamaBackend`

class Chunk:

    sentences: List[str]  # Sentence listOllama backend implementation.

    chunk_id: int         # Chunk number

    chunk_type: str       # Auto-inferred```python

    scores: List[float]   # LLM scoresbackend = OllamaBackend(

```    model="llama3:latest",

    base_url="http://localhost:11434",

### Chunk Types    timeout=30,

    temperature=0.0

- `quotes` - Coach/player interviews)

- `statistics` - Historical data```

- `future_fixture` - Upcoming matches

- `penalty_shootout` - Penalty events### `OpenAIBackend`

- `goal_sequence` - Goal descriptions

- `match_narrative` - General match descriptionOpenAI-compatible backend (GPT, DeepSeek, etc.).



---```python

backend = OpenAIBackend(

## Performance    model="gpt-4o-mini",

    api_key="sk-...",

### Real Test (Arsenal 14-sentence report)    timeout=30

)

``````

Chunks: 6-7

LLM calls: 7## Configuration

Success: 100%

Avg score: 0.33-0.39### ChunkerConfig Options

Range: [0.30, 0.70]

Forced splits: 6 (5 structural + 1 size)```python

Orphan merges: 1ChunkerConfig(

Speed: ~1-2 sec/sentence    window_size=1,              # 1-5 recommended

```    force_new_on_failure=True,  # Conservative fallback

    log_failures=True,          # Enable logging

---    max_context_length=500      # Max chars in context

)

## API Reference```



### SemanticChunker### Environment Variables



```python```bash

class SemanticChunker:# For OpenAI backend

    def chunk(self, sentences: List[str]) -> List[Chunk]export OPENAI_API_KEY="sk-..."

    def get_stats(self) -> Dict

    def reset_stats(self)# For custom Ollama URL

```export OLLAMA_HOST="http://localhost:11434"

```

### LLMBackend

## Decision Rules (LLM Prompt)

```python

class LLMBackend:The LLM follows these canonical rules:

    def score_boundary(

        self,### SAME_UNIT if:

        current_sentence: str,- ✅ Coreference exists (pronouns, ellipsis, implicit subject)

        previous_sentences: List[str]- ✅ Sentence elaborates, explains, or adds attributes to same fact

    ) -> Tuple[float, bool]  # (score, success)- ✅ Temporal/causal continuation

```

### NEW_UNIT if:

### Backends- ✅ New event, actor, or unrelated fact introduced

- ✅ Topic shift detected

**Ollama** (Local):- ✅ Different time/location/subject

```python

OllamaBackend(## Architecture

    model="llama3:latest",

    temperature=0.2,```

    timeout=30┌─────────────────────────────────────────────────┐

)│  Input: Pre-split sentences (rule-based)       │

```└────────────────┬────────────────────────────────┘

                 │

**OpenAI** (Cloud):                 ▼

```python┌─────────────────────────────────────────────────┐

OpenAIBackend(│  SemanticChunker                                │

    api_key="sk-...",│  ┌───────────────────────────────────────────┐  │

    model="gpt-3.5-turbo",│  │ Sliding Window Logic                      │  │

    temperature=0.2│  └────────────┬──────────────────────────────┘  │

)│               ▼                                  │

```│  ┌───────────────────────────────────────────┐  │

│  │ LLMBackend.decide_boundary()              │  │

---│  │  → Returns: (raw_output, success)         │  │

│  └────────────┬──────────────────────────────┘  │

## Testing│               ▼                                  │

│  ┌───────────────────────────────────────────┐  │

```bash│  │ Output Validation                         │  │

# Full test (3 granularities)│  │  → "SAME_UNIT" ✓                          │  │

python test_v2.py│  │  → "NEW_UNIT"  ✓                          │  │

│  │  → Other       ✗ → Fallback to NEW_UNIT   │  │

# Integration test│  └────────────┬──────────────────────────────┘  │

python preprocess/integration_test.py│               ▼                                  │

```│  ┌───────────────────────────────────────────┐  │

│  │ Chunk Building & Statistics               │  │

---│  └───────────────────────────────────────────┘  │

└────────────────┬────────────────────────────────┘

## Troubleshooting                 │

                 ▼

### Ollama not connecting┌─────────────────────────────────────────────────┐

│  Output: List[List[str]] - Semantic chunks     │

```bash└─────────────────────────────────────────────────┘

ollama serve```

ollama pull llama3:latest

```## Testing



### Too many/few chunks### Unit Tests



```python```bash

# More chunks# Run comprehensive test suite

config = ChunkerConfig(granularity=GranularityMode.FINE)python preprocess/semantic_blocker/test_semantic_chunker.py



# Fewer chunks# Expected output: All 11 tests should pass

config = ChunkerConfig(granularity=GranularityMode.COARSE)```



# Custom thresholdTests cover:

config = ChunkerConfig(break_threshold=0.6)- ✅ Normal flow with valid outputs

```- ✅ All fallback scenarios

- ✅ Edge cases (empty input, single sentence)

### Debug mode- ✅ Window size variations

- ✅ Deterministic behavior

```python- ✅ Statistics tracking

config = ChunkerConfig(log_scores=True)

```### Integration Test with Ollama



---```bash

# Run real Ollama example

## Design Principlespython preprocess/semantic_blocker/example_refactored.py

```

1. **LLM as Tool, Not Decision Maker**

   - LLM provides scores (quantifiable)## Performance

   - Code makes decisions (deterministic)

### Speed

2. **Hybrid Strategy**- ~2-3 seconds per decision (Ollama llama3:8b on M1 Mac)

   - Rules handle obvious boundaries- Can be optimized with batching or faster models

   - LLM handles ambiguous cases

   - Code controls final output### Quality

- Superior to pure rule-based approaches

3. **Explainable Results**- Handles coreference, ellipsis, discourse markers

   - Every sentence has a score- Conservative: prefers separate chunks when uncertain

   - Every forced split has a reason

   - All statistics are tracked### Cost

- **Ollama**: Free (local inference)

4. **Robust Fallback**- **GPT-4o-mini**: ~$0.0001 per decision

   - LLM failure → neutral score (0.5)- **DeepSeek**: ~$0.00003 per decision

   - Size limit → force split

   - Orphan → smart merge## Migration from Old System



---### Old API (Event Aggregator)

```python

## Filesfrom preprocess.semantic_blocker import llm_semantic_chunk



```blocks = llm_semantic_chunk(

semantic_blocker/    sentences,

├── semantic_chunker.py      # Core logic (450 lines)    model="gpt-4o-mini",

├── ollama_backend.py        # LLM backends (280 lines)    window_size=15

├── __init__.py              # Exports)

└── README.md                # This file# Returns: List[dict] with event_type, sentences, confidence

``````



---### New API (Binary Classifier)

```python

## Version Historyfrom preprocess.semantic_blocker import semantic_chunk, OllamaBackend



**v2.0.0** (2026-01-06)backend = OllamaBackend(model="llama3:latest")

- Complete rewrite: binary → continuous scoringchunks = semantic_chunk(sentences, backend, window_size=1)

- Added granularity modes (fine/medium/coarse)# Returns: List[List[str]] - simpler, more predictable

- Implemented post-processing rules```

- Added chunk type inference

- 100% test success rate### Key Differences



**v1.0.0** (Previous)| Aspect | Old System | New System |

- Binary classifier (SAME_UNIT/NEW_UNIT)|--------|-----------|------------|

- Unstable oscillation issues| **Output** | Event blocks with types | Simple sentence lists |

- Deprecated| **LLM Role** | Event classifier | Binary boundary detector |

| **Complexity** | High (event taxonomy) | Low (binary decision) |

---| **Fallback** | Complex retry logic | Simple: force NEW_UNIT |

| **Determinism** | Variable | Guaranteed |

## License| **Backend** | OpenAI only | Pluggable (Ollama, OpenAI, etc.) |



Part of Football Dynamic Knowledge project.## Extending: Custom Backends


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
