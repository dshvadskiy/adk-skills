"""LLM integration adapters for various providers."""

from .base_adapter import BaseLLMAdapter, LLMResponse, ToolCall

# Conditionally import ADKAdapter if google-adk is available
try:
    from .adk_adapter import ADKAdapter

    __all__ = ["BaseLLMAdapter", "LLMResponse", "ToolCall", "ADKAdapter"]
except ImportError:
    # google-adk not installed
    __all__ = ["BaseLLMAdapter", "LLMResponse", "ToolCall"]
