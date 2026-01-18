"""Tests for ToolRegistry - tool definition management."""

import pytest

from skill_framework.tools import ToolRegistry


class TestToolRegistry:
    """Test ToolRegistry"""

    @pytest.fixture
    def registry(self):
        """Create ToolRegistry instance"""
        return ToolRegistry()

    @pytest.fixture
    def tool_definition(self):
        """Sample tool definition"""
        return {
            "name": "test_tool",
            "description": "A test tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string"},
                },
            },
        }

    def test_registry_initialization(self, registry):
        """Test registry initializes empty"""
        assert registry.tools == {}

    def test_register_tool(self, registry, tool_definition):
        """Test registering a tool"""
        registry.register_tool("test_tool", tool_definition)
        assert "test_tool" in registry.tools
        assert registry.tools["test_tool"] == tool_definition

    def test_register_tool_overwrites(self, registry, tool_definition):
        """Test registering same tool name overwrites"""
        registry.register_tool("test_tool", tool_definition)
        new_definition = {
            "name": "test_tool",
            "description": "Updated description",
            "parameters": {},
        }
        registry.register_tool("test_tool", new_definition)
        assert registry.tools["test_tool"] == new_definition
        assert registry.tools["test_tool"]["description"] == "Updated description"

    def test_register_multiple_tools(self, registry):
        """Test registering multiple tools"""
        tool1 = {"name": "tool1", "description": "Tool 1", "parameters": {}}
        tool2 = {"name": "tool2", "description": "Tool 2", "parameters": {}}
        tool3 = {"name": "tool3", "description": "Tool 3", "parameters": {}}

        registry.register_tool("tool1", tool1)
        registry.register_tool("tool2", tool2)
        registry.register_tool("tool3", tool3)

        assert len(registry.tools) == 3
        assert "tool1" in registry.tools
        assert "tool2" in registry.tools
        assert "tool3" in registry.tools

    def test_get_tool_definition(self, registry, tool_definition):
        """Test getting a single tool definition"""
        registry.register_tool("test_tool", tool_definition)
        result = registry.get_tool_definition("test_tool")
        assert result == tool_definition

    def test_get_tool_definition_not_found(self, registry):
        """Test getting non-existent tool returns None"""
        result = registry.get_tool_definition("nonexistent")
        assert result is None

    def test_get_all_tool_definitions(self, registry):
        """Test getting all tool definitions"""
        tool1 = {"name": "tool1", "description": "Tool 1", "parameters": {}}
        tool2 = {"name": "tool2", "description": "Tool 2", "parameters": {}}

        registry.register_tool("tool1", tool1)
        registry.register_tool("tool2", tool2)

        all_tools = registry.get_all_tool_definitions()
        assert len(all_tools) == 2
        assert tool1 in all_tools
        assert tool2 in all_tools

    def test_get_all_tool_definitions_empty(self, registry):
        """Test getting all tools from empty registry"""
        all_tools = registry.get_all_tool_definitions()
        assert all_tools == []

    def test_remove_tool(self, registry, tool_definition):
        """Test removing a tool"""
        registry.register_tool("test_tool", tool_definition)
        assert "test_tool" in registry.tools

        registry.remove_tool("test_tool")
        assert "test_tool" not in registry.tools

    def test_remove_nonexistent_tool(self, registry):
        """Test removing non-existent tool doesn't raise"""
        registry.remove_tool("nonexistent")
        assert registry.tools == {}

    def test_has_tool_true(self, registry, tool_definition):
        """Test has_tool returns True for existing tool"""
        registry.register_tool("test_tool", tool_definition)
        assert registry.has_tool("test_tool") is True

    def test_has_tool_false(self, registry):
        """Test has_tool returns False for non-existent tool"""
        assert registry.has_tool("nonexistent") is False

    def test_clear(self, registry):
        """Test clearing all tools"""
        tool1 = {"name": "tool1", "description": "Tool 1", "parameters": {}}
        tool2 = {"name": "tool2", "description": "Tool 2", "parameters": {}}

        registry.register_tool("tool1", tool1)
        registry.register_tool("tool2", tool2)
        assert len(registry.tools) == 2

        registry.clear()
        assert registry.tools == {}
        assert len(registry.tools) == 0

    def test_tool_definition_with_complex_parameters(self, registry):
        """Test registering tool with complex parameter schema"""
        tool_definition = {
            "name": "complex_tool",
            "description": "Tool with complex parameters",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "First parameter",
                    },
                    "param2": {
                        "type": "integer",
                        "description": "Second parameter",
                        "minimum": 0,
                        "maximum": 100,
                    },
                    "param3": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["param1", "param2"],
            },
        }

        registry.register_tool("complex_tool", tool_definition)
        retrieved = registry.get_tool_definition("complex_tool")
        assert retrieved["parameters"]["required"] == ["param1", "param2"]
        assert retrieved["parameters"]["properties"]["param2"]["maximum"] == 100
