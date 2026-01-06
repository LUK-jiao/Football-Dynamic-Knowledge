"""
Ollama Backend for Semantic Chunker (v2 - Continuous Scoring)

Implements LLMBackend interface using local Ollama server.

Features:
- Continuous semantic break strength scoring (0.0 - 1.0)
- Timeout handling
- Connection error recovery
- Minimal context to reduce latency
"""

from typing import List, Tuple
import requests
import logging
from .semantic_chunker import LLMBackend


class OllamaBackend(LLMBackend):
    """
    Ollama-based LLM backend for semantic boundary strength scoring.
    
    Returns a continuous score (0.0-1.0) instead of binary decision.
    """
    
    # Semantic break strength scoring prompt
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
        temperature: float = 0.1  # Low for consistency
    ):
        """
        Initialize Ollama backend.
        
        Args:
            model: Ollama model name (e.g., "llama3:latest", "qwen3:8b")
            base_url: Ollama server URL
            timeout: Request timeout in seconds
            temperature: LLM temperature (0.0 for deterministic)
        """
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.temperature = temperature
        self.generate_url = f"{self.base_url}/api/generate"
        self.logger = logging.getLogger(__name__)
        
        # Verify connection on init
        self._verify_connection()
    
    def _verify_connection(self):
        """Verify Ollama server is accessible."""
        try:
            tags_url = f"{self.base_url}/api/tags"
            resp = requests.get(tags_url, timeout=5)
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
    
    def decide_boundary(
        self, 
        current_sentence: str, 
        previous_sentences: List[str]
    ) -> Tuple[float, bool]:
        """
        Ask Ollama to score semantic break strength.
        
        Args:
            current_sentence: Current sentence
            previous_sentences: 1-N previous sentences (dynamic context)
            
        Returns:
            (score: float [0.0-1.0], success: bool)
            - score=0.0: same semantic unit
            - score=1.0: completely new topic
            - success=False if parsing failed
        """
        # Use ALL previous sentences as context (dynamic window)
        if not previous_sentences:
            previous_text = "[No previous context]"
        elif len(previous_sentences) == 1:
            previous_text = previous_sentences[0]
        else:
            # Multiple sentences: join as single context
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
                "num_predict": 10,  # Need a bit more for floating point
                "stop": ["\n", " ", "explanation", "Explanation"]
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
            
            # Parse float score from output
            try:
                score = float(raw_output)
                # Clamp to [0.0, 1.0]
                score = max(0.0, min(1.0, score))
                return (score, True)
            except ValueError:
                # Failed to parse - return error
                self.logger.warning(f"Failed to parse score from: '{raw_output}'")
                return (0.5, False)  # Default to neutral score
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timeout after {self.timeout}s")
            return (0.5, False)
            
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to Ollama server")
            return (0.5, False)
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Ollama HTTP error: {e}")
            return (0.5, False)
            
        except Exception as e:
            self.logger.error(f"Unexpected error calling Ollama: {e}")
            return (0.5, False)
    
    def test_connection(self) -> bool:
        """
        Test if Ollama server is accessible.
        
        Returns:
            True if connection successful
        """
        try:
            tags_url = f"{self.base_url}/api/tags"
            resp = requests.get(tags_url, timeout=5)
            resp.raise_for_status()
            return True
        except:
            return False


# ============================================================================
# Alternative: OpenAI-compatible Backend
# ============================================================================

class OpenAIBackend(LLMBackend):
    """
    OpenAI-compatible backend (for GPT, DeepSeek, etc.).
    
    Can be used as drop-in replacement for OllamaBackend.
    """
    
    SYSTEM_PROMPT = OllamaBackend.SYSTEM_PROMPT
    USER_PROMPT_TEMPLATE = OllamaBackend.USER_PROMPT_TEMPLATE
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str = None,
        base_url: str = None,
        timeout: int = 30
    ):
        """
        Initialize OpenAI-compatible backend.
        
        Args:
            model: Model name
            api_key: API key (or set OPENAI_API_KEY env var)
            base_url: Optional custom base URL (for DeepSeek, etc.)
            timeout: Request timeout
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI package required. Install: pip install openai"
            )
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )
        self.model = model
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"✓ OpenAI backend initialized with model '{model}'")
    
    def decide_boundary(
        self,
        current_sentence: str,
        previous_sentences: List[str]
    ) -> Tuple[str, bool]:
        """Ask OpenAI to decide semantic boundary."""
        previous_text = previous_sentences[-1] if previous_sentences else ""
        
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            previous=previous_text,
            current=current_sentence
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=10
            )
            
            raw_output = response.choices[0].message.content.strip()
            return (raw_output, True)
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return ("", False)
