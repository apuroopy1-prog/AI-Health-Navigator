"""
AWS Bedrock Client for Claude models
Supports both Claude 3 Haiku (fast) and Claude 3.5 Sonnet (powerful)
"""
import json
import logging
import os
from typing import Optional, Dict, Any, List

import boto3
from botocore.exceptions import ClientError

from config.settings import settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """
    AWS Bedrock client wrapper for Claude models.
    Supports dual-model architecture with Haiku and Sonnet.
    """

    def __init__(self, model_type: str = "haiku"):
        """
        Initialize Bedrock client.

        Args:
            model_type: "haiku" for fast responses, "sonnet" for complex analysis
        """
        self.model_type = model_type
        self.model_id = self._get_model_id(model_type)
        self.max_tokens = self._get_max_tokens(model_type)
        self.client = self._initialize_client()

    def _get_model_id(self, model_type: str) -> str:
        """Get the appropriate model ID based on type"""
        if model_type == "sonnet":
            return settings.models.sonnet_model_id
        return settings.models.haiku_model_id

    def _get_max_tokens(self, model_type: str) -> int:
        """Get max tokens based on model type"""
        if model_type == "sonnet":
            return settings.models.max_tokens_sonnet
        return settings.models.max_tokens_haiku

    def _initialize_client(self):
        """Initialize the Bedrock runtime client"""
        try:
            return boto3.client(
                service_name="bedrock-runtime",
                region_name=settings.aws_region
            )
        except Exception as e:
            logger.warning(f"Could not initialize Bedrock client: {e}")
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

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens or self.max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                body["system"] = system_prompt

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except ClientError as e:
            logger.error(f"Bedrock API error: {e}")
            return self._fallback_response(prompt)
        except Exception as e:
            logger.error(f"Unexpected error invoking Bedrock: {e}")
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
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            if system_prompt:
                body["system"] = system_prompt

            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except Exception as e:
            logger.error(f"Error in multi-turn conversation: {e}")
            return self._fallback_response(messages[-1]["content"] if messages else "")

    def _fallback_response(self, prompt: str) -> str:
        """
        Provide fallback responses when Bedrock is unavailable.
        Useful for local development and testing.
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
