"""
Model Router for task-based model selection
Routes tasks to either Claude 3 Haiku (fast) or Claude 3.5 Sonnet (powerful)
Supports both Anthropic API and AWS Bedrock
"""
from typing import Optional
from config.settings import settings
from .claude_client import get_llm_client


class ModelRouter:
    """
    Routes tasks to the appropriate Claude model based on complexity.

    - Haiku: Fast, cost-effective for simple tasks
    - Sonnet: Powerful reasoning for complex analysis
    """

    def __init__(self):
        self._haiku_client = None
        self._sonnet_client = None

    @property
    def haiku(self):
        """Get or create Haiku client (lazy initialization)"""
        if self._haiku_client is None:
            self._haiku_client = get_llm_client(model_type="haiku")
        return self._haiku_client

    @property
    def sonnet(self):
        """Get or create Sonnet client (lazy initialization)"""
        if self._sonnet_client is None:
            self._sonnet_client = get_llm_client(model_type="sonnet")
        return self._sonnet_client

    def get_client_for_task(self, task_type: str):
        """
        Get the appropriate client for a given task type.

        Args:
            task_type: Type of task (e.g., "intake_greeting", "specialist_consultation")

        Returns:
            LLM client configured for the appropriate model
        """
        model_type = settings.task_model_mapping.get(task_type, "haiku")

        if model_type == "sonnet":
            return self.sonnet
        return self.haiku

    def invoke_for_task(
        self,
        task_type: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Convenience method to invoke the appropriate model for a task.

        Args:
            task_type: Type of task
            prompt: User prompt
            system_prompt: Optional system instructions
            **kwargs: Additional arguments for invoke

        Returns:
            Model response text
        """
        client = self.get_client_for_task(task_type)
        return client.invoke(prompt, system_prompt=system_prompt, **kwargs)


# Global router instance
model_router = ModelRouter()
