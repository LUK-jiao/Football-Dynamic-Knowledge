"""
Ollama Backend v2 - Continuous Scoring

Implements LLMBackend interface for semantic break strength scoring.
"""

from typing import List, Tuple
import requests
import logging
from .semantic_chunker import LLMBackend


class OllamaBackend(LLMBackend):
    """
    Ollama-based LLM backend for semantic boundary strength scoring.
    
    Returns continuous scores (0.0-1.0) instead of binary decisions.
    """
    
    SYSTEM_PROMPT = """You are evaluating whether the CURRENT sentence starts a new semantic unit relative to the PREVIOUS context.

Semantic units correspond to coherent events or sub-events (e.g. match outcome, goal sequence, penalty shoot-out, manager comments).

Return a single number between 0.0 and 1.0:

0.0 = same semantic unit (strong continuation)
0.3 = weak continuation / elaboration
0.5 = sub-event shift (same topic, different aspect)
0.7 = clear semantic boundary
1.0 = completely new topic / event

Guidelines:
- Same event/action = 0.0-0.2
- Adding detail to previous = 0.2-0.4
- Shift within same topic = 0.4-0.6
- New sub-event = 0.6-0.8
- New topic/team/time = 0.8-1.0

Output ONLY the number (e.g. 0.3 or 0.7). No explanation."""

    USER_PROMPT_TEMPLATE = """PREVIOUS context: {previous}

CURRENT sentence: {current}

Semantic break strength (0.0-1.0):"""
    
    def __init__(
        self,
        model: str = "llama3:latest",
        base_url: str = "http://localhost:11434",
        timeout: int = 30,
        temperature: float = 0.2
    ):
        """
        Initialize Ollama backend.
        
        Args:
            model: Ollama model name
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            temperature: LLM temperature (0.2 for stability with some variance)
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)
        
        # API endpoints
        self.generate_url = f"{self.base_url}/api/generate"
        self.tags_url = f"{self.base_url}/api/tags"
        
        # Verify connection
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify Ollama server is accessible."""
        try:
            resp = requests.get(self.tags_url, timeout=5)
            resp.raise_for_status()
            
            models = resp.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            if self.model not in model_names:
                self.logger.warning(
                    f"Model '{self.model}' not found in available models: {model_names}"
                )
            else:
                self.logger.info(f"✓ Ollama backend initialized with model '{self.model}'")
                
        except requests.exceptions.ConnectionError:
            self.logger.error(
                "Cannot connect to Ollama server. "
                "Make sure Ollama is running: ollama serve"
            )
        except Exception as e:
            self.logger.error(f"Ollama verification failed: {e}")
    
    def score_boundary(
        self, 
        current_sentence: str, 
        previous_sentences: List[str]
    ) -> Tuple[float, bool]:
        """
        Score semantic break strength using Ollama.
        
        Args:
            current_sentence: Sentence to evaluate
            previous_sentences: Previous context (1-N sentences)
            
        Returns:
            (score: float [0.0-1.0], success: bool)
        """
        # Format previous context
        if not previous_sentences:
            previous_text = "[Start of text]"
        elif len(previous_sentences) == 1:
            previous_text = previous_sentences[0]
        else:
            previous_text = " ".join(previous_sentences)
        
        # Build prompt
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            previous=previous_text,
            current=current_sentence
        )
        
        # Prepare payload
        payload = {
            "model": self.model,
            "prompt": f"{self.SYSTEM_PROMPT}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": 0.9,
                "num_predict": 10,
                "stop": ["\n", "explanation", "Explanation", "because", "Because"]
            }
        }
        
        try:
            resp = requests.post(
                self.generate_url,
                json=payload,
                timeout=self.timeout
            )
            resp.raise_for_status()
            
            result = resp.json()
            raw_output = result.get("response", "").strip()
            
            # Parse float score
            score = self._parse_score(raw_output)
            
            if score is not None:
                return (score, True)
            else:
                self.logger.warning(f"Failed to parse score from: '{raw_output}'")
                return (0.5, False)  # Neutral fallback
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timeout after {self.timeout}s")
            return (0.5, False)
            
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to Ollama server")
            return (0.5, False)
            
        except Exception as e:
            self.logger.error(f"Unexpected error calling Ollama: {e}")
            return (0.5, False)
    
    def _parse_score(self, raw_output: str) -> float:
        """
        Parse float score from LLM output.
        
        Handles various formats:
        - "0.5"
        - "0.7."
        - "Score: 0.3"
        - etc.
        """
        import re
        
        # Try direct float conversion
        try:
            score = float(raw_output)
            return max(0.0, min(1.0, score))
        except ValueError:
            pass
        
        # Try extracting number from text
        match = re.search(r'(\d+\.?\d*)', raw_output)
        if match:
            try:
                score = float(match.group(1))
                # Handle "05" as "0.5"
                if score > 1.0 and score < 10.0:
                    score = score / 10.0
                return max(0.0, min(1.0, score))
            except ValueError:
                pass
        
        return None


class OpenAIBackend(LLMBackend):
    """OpenAI-compatible API backend for scoring."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 30,
        temperature: float = 0.2
    ):
        """Initialize OpenAI backend."""
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.temperature = temperature
        self.logger = logging.getLogger(__name__)
    
    def score_boundary(
        self, 
        current_sentence: str, 
        previous_sentences: List[str]
    ) -> Tuple[float, bool]:
        """Score using OpenAI API."""
        # Format context
        if not previous_sentences:
            previous_text = "[Start of text]"
        else:
            previous_text = " ".join(previous_sentences)
        
        # Build messages
        messages = [
            {
                "role": "system",
                "content": OllamaBackend.SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": f"PREVIOUS context: {previous_text}\n\nCURRENT sentence: {current_sentence}\n\nSemantic break strength (0.0-1.0):"
            }
        ]
        
        # Prepare payload
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 10
        }
        
        try:
            import requests
            
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout
            )
            resp.raise_for_status()
            
            result = resp.json()
            raw_output = result['choices'][0]['message']['content'].strip()
            
            # Parse score
            try:
                score = float(raw_output)
                score = max(0.0, min(1.0, score))
                return (score, True)
            except ValueError:
                self.logger.warning(f"Failed to parse score from: '{raw_output}'")
                return (0.5, False)
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return (0.5, False)
