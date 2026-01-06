import sys
sys.path.insert(0, 'preprocess')
from semantic_blocker.ollama_backend import OllamaBackend

backend = OllamaBackend()
result, success = backend.decide_boundary(
    "Arsenal won 2-1.",
    ["The match ended."]
)
print(f"Result: '{result}', Success: {success}")
