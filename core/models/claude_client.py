"""
Anthropic Claude API Client
Direct integration with Claude API (not via AWS Bedrock)
"""
import json
import logging
import os
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# Try to import anthropic, gracefully handle if not installed
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("anthropic package not installed. Run: pip install anthropic")


class ClaudeClient:
    """
    Anthropic Claude API client wrapper.
    Supports Claude 3.5 Sonnet and Claude 3 Haiku models.
    """

    # Model IDs for Anthropic API
    MODELS = {
        "sonnet": "claude-sonnet-4-20250514",
        "haiku": "claude-3-haiku-20240307",
        "opus": "claude-3-opus-20240229"
    }

    def __init__(self, model_type: str = "sonnet"):
        """
        Initialize Claude client.

        Args:
            model_type: "haiku" for fast responses, "sonnet" for complex analysis
        """
        self.model_type = model_type
        self.model_id = self.MODELS.get(model_type, self.MODELS["sonnet"])
        self.max_tokens = 4096 if model_type == "sonnet" else 1024
        self.client = self._initialize_client()

    def _initialize_client(self):
        """Initialize the Anthropic client"""
        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic package not available")
            return None

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set in environment")
            return None

        try:
            return anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"Could not initialize Anthropic client: {e}")
            return None

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Invoke Claude model with the given prompt.

        Args:
            prompt: User message/prompt
            system_prompt: Optional system instructions
            temperature: Sampling temperature (0-1)
            max_tokens: Override default max tokens

        Returns:
            Model response text
        """
        if self.client is None:
            return self._fallback_response(prompt)

        try:
            messages = [{"role": "user", "content": prompt}]

            kwargs = {
                "model": self.model_id,
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            return self._fallback_response(prompt)
        except Exception as e:
            logger.error(f"Unexpected error invoking Claude: {e}")
            return self._fallback_response(prompt)

    def invoke_with_history(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> str:
        """
        Invoke with conversation history for multi-turn conversations.

        Args:
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system_prompt: Optional system instructions
            temperature: Sampling temperature

        Returns:
            Model response text
        """
        if self.client is None:
            return self._fallback_response(messages[-1]["content"] if messages else "")

        try:
            kwargs = {
                "model": self.model_id,
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                kwargs["system"] = system_prompt

            response = self.client.messages.create(**kwargs)
            return response.content[0].text

        except Exception as e:
            logger.error(f"Error in multi-turn conversation: {e}")
            return self._fallback_response(messages[-1]["content"] if messages else "")

    def _fallback_response(self, prompt: str) -> str:
        """
        Provide fallback responses when Claude API is unavailable.
        """
        prompt_lower = prompt.lower()

        if "intake" in prompt_lower or "greeting" in prompt_lower:
            return (
                "Hello! I'm your AI Health Navigator. I'm here to help understand "
                "your symptoms and guide you to appropriate care. "
                "Could you please tell me what brings you in today?"
            )

        if "supervisor" in prompt_lower or "route" in prompt_lower:
            return json.dumps({
                "specialists": ["general_practitioner"],
                "reasoning": "Routing to GP for initial evaluation.",
                "urgency": "routine"
            })

        if "cardiologist" in prompt_lower or "heart" in prompt_lower:
            return (
                "Based on the cardiac symptoms described, I recommend: "
                "1) ECG to assess heart rhythm, "
                "2) Basic cardiac markers, "
                "3) Follow-up with cardiology if symptoms persist. "
                "Confidence: 0.75"
            )

        if "neurologist" in prompt_lower or "headache" in prompt_lower:
            return (
                "Neurological assessment suggests: "
                "Primary headache disorder likely (migraine vs tension-type). "
                "Recommend: symptom diary, trial of OTC analgesics, "
                "and neurology referral if no improvement in 2 weeks. "
                "Confidence: 0.70"
            )

        if "consensus" in prompt_lower:
            return (
                "Consensus synthesis: Based on specialist input, "
                "the primary assessment suggests a moderate-risk condition "
                "requiring outpatient follow-up. Agreement level: majority."
            )

        if "care plan" in prompt_lower:
            return (
                "Care Plan: "
                "1) Continue current symptom management, "
                "2) Follow up with primary care in 1-2 weeks, "
                "3) Return immediately if symptoms worsen. "
                "Care Level: Primary Care"
            )

        return (
            "I've noted your information. Based on what you've shared, "
            "I recommend discussing these symptoms with a healthcare provider "
            "for a thorough evaluation."
        )

    @property
    def is_available(self) -> bool:
        """Check if the Claude API client is properly configured"""
        return self.client is not None


# Convenience function to get the best available client
def get_llm_client(model_type: str = "sonnet"):
    """
    Get the best available LLM client.
    Prefers Claude API, falls back to Bedrock if needed.
    """
    # Try Claude API first
    claude = ClaudeClient(model_type)
    if claude.is_available:
        logger.info(f"Using Claude API with model: {claude.model_id}")
        return claude

    # Fall back to Bedrock
    try:
        from .bedrock_client import BedrockClient
        bedrock = BedrockClient(model_type)
        if bedrock.client is not None:
            logger.info(f"Using AWS Bedrock with model: {bedrock.model_id}")
            return bedrock
    except Exception as e:
        logger.warning(f"Bedrock fallback failed: {e}")

    # Return Claude client anyway (will use fallback responses)
    logger.warning("No LLM backend available, using fallback responses")
    return claude
