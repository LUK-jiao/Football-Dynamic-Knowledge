"""
LLM Backend for RAG System

Provides a simple interface to Ollama for query parsing and answer generation.
"""

from typing import Dict, Any, Optional
import ollama


class RAGLLMBackend:
    """
    LLM backend for RAG system using Ollama.
    
    Provides chat interface for query parsing and answer generation.
    """
    
    def __init__(
        self,
        model: str = "llama3:latest",
        timeout: int = 60,
        default_temperature: float = 0.3
    ):
        """
        Initialize RAG LLM backend.
        
        Args:
            model: Ollama model name
            timeout: Request timeout in seconds
            default_temperature: Default sampling temperature
        """
        self.model = model
        self.timeout = timeout
        self.default_temperature = default_temperature
        
        # Verify model is available
        self._verify_model()
    
    def _verify_model(self):
        """Verify that the model is available."""
        try:
            # Try to list models to verify Ollama is running
            ollama.list()
        except Exception as e:
            print(f"Warning: Could not verify Ollama connection: {e}")
    
    def chat(
        self,
        prompt: str,
        temperature: Optional[float] = None,
        max_tokens: int = 2000,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Send a chat request to the LLM.
        
        Args:
            prompt: User prompt/question
            temperature: Sampling temperature (0.0-1.0), uses default if None
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            
        Returns:
            Generated response text
            
        Raises:
            RuntimeError: If API call fails
        """
        if temperature is None:
            temperature = self.default_temperature
        
        # Build messages
        messages = []
        
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        # Call Ollama
        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "num_ctx": 8192,
                    "top_p": 0.9
                }
            )
            
            content = response.get("message", {}).get("content", "")
            
            if not content:
                raise ValueError("Ollama returned empty response")
            
            return content.strip()
            
        except Exception as e:
            raise RuntimeError(f"Ollama API call failed: {str(e)}")
    
    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1500
    ) -> str:
        """
        Generate structured output (e.g., JSON).
        
        Uses lower temperature for more consistent output.
        
        Args:
            prompt: User prompt expecting structured output
            temperature: Low temperature for consistency
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated response text
        """
        return self.chat(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def generate_answer(
        self,
        query: str,
        context: str,
        system_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate an answer based on query and context.
        
        Args:
            query: User question
            context: Retrieved context from knowledge graph
            system_prompt: System instructions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated answer
        """
        # Build full prompt
        full_prompt = f"""Question:
{query}

Context:
{context}

Please answer the question based on the provided context."""
        
        return self.chat(
            prompt=full_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=system_prompt
        )
