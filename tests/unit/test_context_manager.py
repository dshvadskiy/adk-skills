"""Tests for ContextManager - skill execution context modifications."""

import pytest

from skill_framework.core import ContextManager, SkillMetadata


class TestContextManager:
    """Test suite for ContextManager execution context modifications."""

    @pytest.fixture
    def context_manager(self) -> ContextManager:
        """Create ContextManager instance."""
        return ContextManager()

    @pytest.fixture
    def default_context(self, context_manager: ContextManager) -> dict:
        """Get default execution context."""
        return context_manager.default_context.copy()

    @pytest.fixture
    def sample_metadata(self) -> SkillMetadata:
        """Create sample skill metadata."""
        return SkillMetadata(
            name="test-skill",
            description="Test skill",
            required_tools=["bash_tool"],
            optional_tools=["file_read"],
            max_execution_time=60,
            max_memory=1024,
            network_access=False,
        )

    def test_default_context_has_expected_structure(
        self, context_manager: ContextManager
    ):
        """Test that default context has all required fields."""
        ctx = context_manager.default_context

        assert "allowed_tools" in ctx
        assert "file_permissions" in ctx
        assert "network_access" in ctx
        assert "max_execution_time" in ctx
        assert "max_memory" in ctx
        assert "working_directory" in ctx
        assert "environment_variables" in ctx

    def test_default_context_values(self, context_manager: ContextManager):
        """Test default context has correct initial values."""
        ctx = context_manager.default_context

        assert ctx["allowed_tools"] == []
        assert ctx["file_permissions"] == "none"
        assert ctx["network_access"] is False
        assert ctx["max_execution_time"] == 300
        assert ctx["max_memory"] == 2048
        assert ctx["working_directory"] == "/tmp"
        assert ctx["environment_variables"] == {}

    def test_modify_for_skill_adds_required_tools(
        self,
        context_manager: ContextManager,
        default_context: dict,
        sample_metadata: SkillMetadata,
    ):
        """Test that required tools are added to allowed_tools."""
        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, default_context
        )

        assert "bash_tool" in result["allowed_tools"]
        assert len(result["allowed_tools"]) == 1

    def test_modify_for_skill_adds_optional_tools_if_available(
        self, context_manager: ContextManager, sample_metadata: SkillMetadata
    ):
        """Test that optional tools are added if in all_available_tools."""
        current_context = {
            "allowed_tools": [],
            "all_available_tools": ["bash_tool", "file_read", "file_write"],
        }

        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, current_context
        )

        assert "bash_tool" in result["allowed_tools"]
        assert "file_read" in result["allowed_tools"]

    def test_modify_for_skill_does_not_add_unavailable_optional_tools(
        self, context_manager: ContextManager, sample_metadata: SkillMetadata
    ):
        """Test that optional tools not in all_available_tools are not added."""
        current_context = {
            "allowed_tools": [],
            "all_available_tools": ["bash_tool"],  # file_read not available
        }

        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, current_context
        )

        assert "bash_tool" in result["allowed_tools"]
        assert "file_read" not in result["allowed_tools"]

    def test_modify_for_skill_applies_max_execution_time_constraint(
        self,
        context_manager: ContextManager,
        default_context: dict,
        sample_metadata: SkillMetadata,
    ):
        """Test that max_execution_time takes minimum of current and skill requirement."""
        default_context["max_execution_time"] = 300

        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, default_context
        )

        assert result["max_execution_time"] == 60

    def test_modify_for_skill_applies_max_memory_constraint(
        self,
        context_manager: ContextManager,
        default_context: dict,
        sample_metadata: SkillMetadata,
    ):
        """Test that max_memory takes minimum of current and skill requirement."""
        default_context["max_memory"] = 4096

        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, default_context
        )

        assert result["max_memory"] == 1024

    def test_modify_for_skill_enables_network_access(
        self, context_manager: ContextManager, default_context: dict
    ):
        """Test that network_access is enabled if skill requires it."""
        metadata = SkillMetadata(
            name="network-skill",
            description="Network skill",
            network_access=True,
        )

        result = context_manager.modify_for_skill(
            "network-skill", metadata, default_context
        )

        assert result["network_access"] is True

    def test_modify_for_skill_preserves_existing_context(
        self, context_manager: ContextManager, sample_metadata: SkillMetadata
    ):
        """Test that existing context values are preserved when not overridden."""
        current_context = {
            "allowed_tools": [],
            "file_permissions": "read_write",
            "working_directory": "/custom/path",
        }

        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, current_context
        )

        assert result["file_permissions"] == "read_write"
        assert result["working_directory"] == "/custom/path"

    def test_modify_for_skill_tracks_active_skill(
        self,
        context_manager: ContextManager,
        default_context: dict,
        sample_metadata: SkillMetadata,
    ):
        """Test that active_skill and skill_version are tracked."""
        result = context_manager.modify_for_skill(
            "test-skill", sample_metadata, default_context
        )

        assert result["active_skill"] == "test-skill"
        assert result["skill_version"] == "1.0.0"

    def test_modify_for_skill_applies_pdf_skill_context(
        self, context_manager: ContextManager, default_context: dict
    ):
        """Test skill-specific context for PDF processing."""
        metadata = SkillMetadata(
            name="pdf",
            description="PDF skill",
            tags=["pdf"],
        )

        result = context_manager.modify_for_skill("pdf", metadata, default_context)

        assert result["file_permissions"] == "read_write"
        assert ".pdf" in result["allowed_file_extensions"]

    def test_modify_for_skill_applies_data_analysis_skill_context(
        self, context_manager: ContextManager, default_context: dict
    ):
        """Test skill-specific context for data analysis (higher memory)."""
        metadata = SkillMetadata(
            name="data-analysis",
            description="Data analysis skill",
            tags=["data-analysis"],
            max_memory=2048,
        )

        result = context_manager.modify_for_skill(
            "data-analysis", metadata, default_context
        )

        # Should be max of default (2048) and skill-specific (4096) = 4096
        assert result["max_memory"] == 4096

    def test_modify_for_skill_applies_report_generation_skill_context(
        self, context_manager: ContextManager, default_context: dict
    ):
        """Test skill-specific context for report generation."""
        metadata = SkillMetadata(
            name="report-generation",
            description="Report generation skill",
        )

        result = context_manager.modify_for_skill(
            "report-generation", metadata, default_context
        )

        assert result["output_directory"] == "/tmp/reports"
        assert result["file_permissions"] == "read_write"

    def test_modify_for_skill_applies_fraud_analysis_skill_context(
        self, context_manager: ContextManager, default_context: dict
    ):
        """Test skill-specific context for fraud analysis."""
        metadata = SkillMetadata(
            name="fraud-analysis",
            description="Fraud analysis skill",
        )

        result = context_manager.modify_for_skill(
            "fraud-analysis", metadata, default_context
        )

        assert result["database_access"] is True
        assert "transactions" in result["allowed_tables"]
        assert "users" in result["allowed_tables"]
        assert "alerts" in result["allowed_tables"]

    def test_restore_default_context_returns_copy(
        self, context_manager: ContextManager
    ):
        """Test that restore_default_context returns a deep copy."""
        ctx1 = context_manager.restore_default_context()
        ctx2 = context_manager.restore_default_context()

        # Modifying one shouldn't affect the other
        ctx1["allowed_tools"].append("test_tool")

        assert "test_tool" not in ctx2["allowed_tools"]
        assert ctx1 != ctx2

    def test_restore_default_context_matches_default(
        self, context_manager: ContextManager
    ):
        """Test that restored context matches default context."""
        restored = context_manager.restore_default_context()

        assert restored == context_manager.default_context

    def test_modify_for_skill_with_minimal_metadata(
        self, context_manager: ContextManager, default_context: dict
    ):
        """Test modification with minimal skill metadata."""
        metadata = SkillMetadata(
            name="minimal",
            description="Minimal skill",
        )

        result = context_manager.modify_for_skill("minimal", metadata, default_context)

        # Should only add tracking fields
        assert result["active_skill"] == "minimal"
        assert result["skill_version"] == "1.0.0"
        assert result["allowed_tools"] == default_context["allowed_tools"]
