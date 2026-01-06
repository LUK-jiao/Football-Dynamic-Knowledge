"""
Ollama Backend for Semantic Chunker

Implements LLMBackend interface using local Ollama server.

Features:
- Strict prompt engineering for binary output
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
    Ollama-based LLM backend for semantic boundary detection.
    
    Uses localhost Ollama server for inference.
    """
    
    # Strict system prompt
    SYSTEM_PROMPT = """You are a semantic boundary classifier for news text.

Your ONLY task: decide if sentence B continues the SAME narrow information unit as sentence A.

Rules for SAME_UNIT:
- B directly continues or elaborates A's specific point
- B uses pronouns/references clearly pointing back to A
- Same time frame, same actor, same sub-event

Rules for NEW_UNIT (be sensitive to these):
- Time shift ("After the match", "Earlier", "Previously")
- Speaker change (narrator → quote, one person → another)
- Topic shift (match action → statistics, goal → other goal)
- Different event phase (regular time → penalties → post-match)
- New paragraph structure (usually signals topic change)
- Statistical info after narrative
- Quotes after description

Default to NEW_UNIT when in doubt.

CRITICAL: Output ONLY ONE TOKEN.
- Output "SAME_UNIT" or "NEW_UNIT"
- NO explanation
- NO punctuation
- NO additional text"""

    USER_PROMPT_TEMPLATE = """Sentence A:
{previous}

Sentence B:
{current}

Decision:"""
    
    def __init__(
        self,
        model: str = "llama3:latest",
        base_url: str = "http://localhost:11434",
        timeout: int = 30,
        temperature: float = 0.0
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
    ) -> Tuple[str, bool]:
        """
        Ask Ollama to decide semantic boundary.
        
        Args:
            current_sentence: Current sentence
            previous_sentences: 1-N previous sentences
            
        Returns:
            (raw_output, success)
        """
        # Use only the most recent sentence for context
        previous_text = previous_sentences[-1] if previous_sentences else ""
        
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
                "num_predict": 10,  # Limit output tokens
                "stop": ["\n", ".", "!"]  # Stop at first token
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
            
            return (raw_output, True)
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Ollama request timeout after {self.timeout}s")
            return ("", False)
            
        except requests.exceptions.ConnectionError:
            self.logger.error("Cannot connect to Ollama server")
            return ("", False)
            
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"Ollama HTTP error: {e}")
            return ("", False)
            
        except Exception as e:
            self.logger.error(f"Unexpected error calling Ollama: {e}")
            return ("", False)
    
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
