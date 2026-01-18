"""Tool registry for managing tool definitions."""

from typing import Any


class ToolRegistry:
    """
    Manages tool definitions for agent use.

    Provides centralized tool registration and retrieval.
    """

    def __init__(self) -> None:
        """Initialize ToolRegistry with empty tool collection."""
        self.tools: dict[str, dict[str, Any]] = {}

    def register_tool(self, name: str, definition: dict[str, Any]) -> None:
        """
        Register a tool definition.

        Args:
            name: Tool identifier
            definition: Tool definition dict with name, description, parameters
        """
        self.tools[name] = definition

    def get_tool_definition(self, name: str) -> dict[str, Any] | None:
        """
        Get single tool definition.

        Args:
            name: Tool identifier

        Returns:
            Tool definition dict or None if not found
        """
        return self.tools.get(name)

    def get_all_tool_definitions(self) -> list[dict[str, Any]]:
        """
        Get all registered tool definitions.

        Returns:
            List of all tool definition dicts
        """
        return list(self.tools.values())

    def remove_tool(self, name: str) -> None:
        """
        Remove a tool from registry.

        Args:
            name: Tool identifier
        """
        if name in self.tools:
            del self.tools[name]

    def has_tool(self, name: str) -> bool:
        """
        Check if tool is registered.

        Args:
            name: Tool identifier

        Returns:
            True if tool is registered
        """
        return name in self.tools

    def clear(self) -> None:
        """Clear all tools from registry."""
        self.tools.clear()
