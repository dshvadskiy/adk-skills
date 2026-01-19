"""Base adapter interface for LLM integrations."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    """Represents a tool call from the LLM."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    """Standardized response from LLM."""

    content: Optional[str] = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: Optional[str] = None
    usage: Optional[dict[str, int]] = None
    raw_response: Optional[Any] = None
    is_streaming: bool = False

    @property
    def has_tool_calls(self) -> bool:
        """Check if response contains tool calls."""
        return len(self.tool_calls) > 0


class BaseLLMAdapter(ABC):
    """
    Abstract base class for LLM integrations.

    Provides a standardized interface for interacting with different
    LLM providers (Google ADK, Anthropic, AWS Bedrock, etc.).

    The adapter handles:
    - Message formatting for the specific provider
    - Tool definition formatting
    - Response parsing and normalization
    - Streaming (optional)
    """

    @abstractmethod
    async def send_message(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send messages to the LLM and get a response.

        Args:
            messages: List of conversation messages
            system_prompt: System instruction
            tools: List of tool definitions
            **kwargs: Provider-specific options

        Returns:
            Standardized LLMResponse
        """
        pass

    @abstractmethod
    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
    ) -> dict[str, Any]:
        """
        Format a tool result for the provider.

        Args:
            tool_call_id: ID of the tool call being responded to
            result: Tool execution result

        Returns:
            Formatted tool result message
        """
        pass

    @abstractmethod
    def format_tools(
        self,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Format tool definitions for the provider.

        Args:
            tools: List of tool definitions in standard format

        Returns:
            Tool definitions in provider-specific format
        """
        pass

    def format_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Format messages for the provider.

        Default implementation returns messages as-is.
        Override for provider-specific formatting.

        Args:
            messages: List of messages in standard format

        Returns:
            Messages in provider-specific format
        """
        return messages

    async def send_message_streaming(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponse]:
        """
        Stream responses from the LLM.

        Default implementation yields a single non-streaming response.
        Override for true streaming support.

        Args:
            messages: List of conversation messages
            system_prompt: System instruction
            tools: List of tool definitions
            **kwargs: Provider-specific options

        Yields:
            LLMResponse chunks with is_streaming=True for intermediate
            chunks, and is_streaming=False for the final response.
        """
        response = await self.send_message(messages, system_prompt, tools, **kwargs)
        yield response
