"""Tests for PermissionManager - tool access control."""

from dataclasses import dataclass

import pytest

from skill_framework.core import PermissionLevel, PermissionManager


@dataclass
class MockSkillMetadata:
    """Mock SkillMetadata for testing."""

    required_tools: list[str]
    optional_tools: list[str] = None


class TestPermissionManager:
    """Test suite for PermissionManager."""

    @pytest.fixture
    def permission_manager(self) -> PermissionManager:
        """Create PermissionManager instance."""
        return PermissionManager()

    @pytest.fixture
    def base_context(self) -> dict:
        """Create base execution context."""
        return {"session_id": "test-session-123"}

    def test_permission_level_enum_values(self):
        """Test that PermissionLevel enum has all required values."""
        assert PermissionLevel.NONE.value == "none"
        assert PermissionLevel.READ.value == "read"
        assert PermissionLevel.WRITE.value == "write"
        assert PermissionLevel.EXECUTE.value == "execute"
        assert PermissionLevel.ADMIN.value == "admin"

    def test_default_tool_permissions_initialized(
        self, permission_manager: PermissionManager
    ):
        """Test that default tool permission matrix is initialized."""
        assert (
            permission_manager.tool_permissions["bash_tool"] == PermissionLevel.EXECUTE
        )
        assert permission_manager.tool_permissions["file_read"] == PermissionLevel.READ
        assert (
            permission_manager.tool_permissions["file_write"] == PermissionLevel.WRITE
        )
        assert (
            permission_manager.tool_permissions["python_execute"]
            == PermissionLevel.EXECUTE
        )
        assert (
            permission_manager.tool_permissions["database_query"]
            == PermissionLevel.READ
        )
        assert (
            permission_manager.tool_permissions["database_write"]
            == PermissionLevel.WRITE
        )
        assert (
            permission_manager.tool_permissions["network_request"]
            == PermissionLevel.EXECUTE
        )

    def test_skill_profiles_initialized(self, permission_manager: PermissionManager):
        """Test that predefined skill profiles are initialized."""
        assert "pdf" in permission_manager.skill_profiles
        assert "fraud-analysis" in permission_manager.skill_profiles
        assert "report-generation" in permission_manager.skill_profiles
        assert "data-validation" in permission_manager.skill_profiles

    def test_pdf_skill_profile_permissions(self, permission_manager: PermissionManager):
        """Test PDF skill has appropriate permissions."""
        profile = permission_manager.skill_profiles["pdf"]
        assert profile["bash_tool"] == PermissionLevel.EXECUTE
        assert profile["file_read"] == PermissionLevel.READ
        assert profile["file_write"] == PermissionLevel.WRITE
        assert profile["python_execute"] == PermissionLevel.EXECUTE

    def test_fraud_analysis_skill_profile_permissions(
        self, permission_manager: PermissionManager
    ):
        """Test fraud-analysis skill has appropriate permissions."""
        profile = permission_manager.skill_profiles["fraud-analysis"]
        assert profile["bash_tool"] == PermissionLevel.EXECUTE
        assert profile["python_execute"] == PermissionLevel.EXECUTE
        assert profile["database_query"] == PermissionLevel.READ
        assert profile["file_read"] == PermissionLevel.READ
        assert "file_write" not in profile

    def test_report_generation_skill_profile_permissions(
        self, permission_manager: PermissionManager
    ):
        """Test report-generation skill has appropriate permissions."""
        profile = permission_manager.skill_profiles["report-generation"]
        assert profile["bash_tool"] == PermissionLevel.EXECUTE
        assert profile["python_execute"] == PermissionLevel.EXECUTE
        assert profile["file_read"] == PermissionLevel.READ
        assert profile["file_write"] == PermissionLevel.WRITE

    def test_data_validation_skill_profile_permissions(
        self, permission_manager: PermissionManager
    ):
        """Test data-validation skill has read-only permissions."""
        profile = permission_manager.skill_profiles["data-validation"]
        assert profile["bash_tool"] == PermissionLevel.EXECUTE
        assert profile["python_execute"] == PermissionLevel.EXECUTE
        assert profile["file_read"] == PermissionLevel.READ
        assert "file_write" not in profile

    def test_apply_permissions_known_skill(
        self, permission_manager: PermissionManager, base_context: dict
    ):
        """Test apply_permissions with known skill profile."""
        mock_metadata = MockSkillMetadata(
            required_tools=["bash_tool"], optional_tools=["file_read"]
        )

        result = permission_manager.apply_permissions(
            "fraud-analysis", mock_metadata, base_context
        )

        assert "tool_permissions" in result
        assert "allowed_tools" in result
        assert "bash_tool" in result["tool_permissions"]
        assert "python_execute" in result["tool_permissions"]
        assert isinstance(result["allowed_tools"], list)

    def test_apply_permissions_unknown_skill_uses_metadata(
        self, permission_manager: PermissionManager, base_context: dict
    ):
        """Test apply_permissions with unknown skill builds from metadata."""
        mock_metadata = MockSkillMetadata(
            required_tools=["python_execute", "bash_tool"],
            optional_tools=["file_read", "file_write"],
        )

        result = permission_manager.apply_permissions(
            "unknown-skill", mock_metadata, base_context
        )

        # Required tools get EXECUTE
        assert result["tool_permissions"]["python_execute"] == PermissionLevel.EXECUTE
        assert result["tool_permissions"]["bash_tool"] == PermissionLevel.EXECUTE

        # Optional tools get READ
        assert result["tool_permissions"]["file_read"] == PermissionLevel.READ
        assert result["tool_permissions"]["file_write"] == PermissionLevel.READ

    def test_build_permissions_from_metadata_required_tools(
        self, permission_manager: PermissionManager
    ):
        """Test _build_permissions_from_metadata assigns EXECUTE to required tools."""
        mock_metadata = MockSkillMetadata(
            required_tools=["tool_a", "tool_b"], optional_tools=[]
        )

        permissions = permission_manager._build_permissions_from_metadata(mock_metadata)

        assert permissions["tool_a"] == PermissionLevel.EXECUTE
        assert permissions["tool_b"] == PermissionLevel.EXECUTE

    def test_build_permissions_from_metadata_optional_tools(
        self, permission_manager: PermissionManager
    ):
        """Test _build_permissions_from_metadata assigns READ to optional tools."""
        mock_metadata = MockSkillMetadata(
            required_tools=[], optional_tools=["tool_c", "tool_d"]
        )

        permissions = permission_manager._build_permissions_from_metadata(mock_metadata)

        assert permissions["tool_c"] == PermissionLevel.READ
        assert permissions["tool_d"] == PermissionLevel.READ

    def test_build_permissions_from_metadata_mixed_tools(
        self, permission_manager: PermissionManager
    ):
        """Test _build_permissions_from_metadata handles mixed required/optional tools."""
        mock_metadata = MockSkillMetadata(
            required_tools=["bash_tool"], optional_tools=["file_read"]
        )

        permissions = permission_manager._build_permissions_from_metadata(mock_metadata)

        assert permissions["bash_tool"] == PermissionLevel.EXECUTE
        assert permissions["file_read"] == PermissionLevel.READ

    def test_build_permissions_from_metadata_empty_optional(
        self, permission_manager: PermissionManager
    ):
        """Test _build_permissions_from_metadata handles empty optional tools."""
        mock_metadata = MockSkillMetadata(
            required_tools=["bash_tool"], optional_tools=None
        )

        permissions = permission_manager._build_permissions_from_metadata(mock_metadata)

        assert permissions["bash_tool"] == PermissionLevel.EXECUTE
        assert len(permissions) == 1

    def test_check_permission_tool_not_in_context(
        self, permission_manager: PermissionManager
    ):
        """Test check_permission returns False for tool not in context."""
        context = {"tool_permissions": {"bash_tool": PermissionLevel.EXECUTE}}

        result = permission_manager.check_permission(
            "unknown_tool", PermissionLevel.READ, context
        )

        assert result is False

    def test_check_permission_exact_match(self, permission_manager: PermissionManager):
        """Test check_permission allows exact permission level match."""
        context = {"tool_permissions": {"bash_tool": PermissionLevel.EXECUTE}}

        result = permission_manager.check_permission(
            "bash_tool", PermissionLevel.EXECUTE, context
        )

        assert result is True

    def test_check_permission_higher_permission(
        self, permission_manager: PermissionManager
    ):
        """Test check_permission allows higher permission level."""
        context = {"tool_permissions": {"bash_tool": PermissionLevel.ADMIN}}

        result = permission_manager.check_permission(
            "bash_tool", PermissionLevel.EXECUTE, context
        )

        assert result is True

    def test_check_permission_lower_permission_denied(
        self, permission_manager: PermissionManager
    ):
        """Test check_permission denies lower permission level."""
        context = {"tool_permissions": {"bash_tool": PermissionLevel.READ}}

        result = permission_manager.check_permission(
            "bash_tool", PermissionLevel.WRITE, context
        )

        assert result is False

    def test_check_permission_hierarchy_none_to_admin(
        self, permission_manager: PermissionManager
    ):
        """Test permission hierarchy from NONE to ADMIN."""
        context = {"tool_permissions": {"bash_tool": PermissionLevel.ADMIN}}

        assert (
            permission_manager.check_permission(
                "bash_tool", PermissionLevel.NONE, context
            )
            is True
        )
        assert (
            permission_manager.check_permission(
                "bash_tool", PermissionLevel.READ, context
            )
            is True
        )
        assert (
            permission_manager.check_permission(
                "bash_tool", PermissionLevel.WRITE, context
            )
            is True
        )
        assert (
            permission_manager.check_permission(
                "bash_tool", PermissionLevel.EXECUTE, context
            )
            is True
        )
        assert (
            permission_manager.check_permission(
                "bash_tool", PermissionLevel.ADMIN, context
            )
            is True
        )

    def test_check_permission_hierarchy_execute_to_read_denied(
        self, permission_manager: PermissionManager
    ):
        """Test EXECUTE permission doesn't allow lower levels."""
        context = {"tool_permissions": {"bash_tool": PermissionLevel.EXECUTE}}

        assert (
            permission_manager.check_permission(
                "bash_tool", PermissionLevel.ADMIN, context
            )
            is False
        )

    def test_apply_permissions_modifies_context_in_place(
        self, permission_manager: PermissionManager, base_context: dict
    ):
        """Test apply_permissions modifies context dict."""
        mock_metadata = MockSkillMetadata(required_tools=["bash_tool"])
        original_id = base_context["session_id"]

        result = permission_manager.apply_permissions(
            "pdf", mock_metadata, base_context
        )

        # Same dict reference
        assert result is base_context
        # Original values preserved
        assert result["session_id"] == original_id
        # New values added
        assert "tool_permissions" in result

    def test_allowed_tools_list_matches_permissions(
        self, permission_manager: PermissionManager, base_context: dict
    ):
        """Test allowed_tools list contains all permission keys."""
        mock_metadata = MockSkillMetadata(required_tools=["bash_tool"])

        result = permission_manager.apply_permissions(
            "pdf", mock_metadata, base_context
        )

        assert set(result["allowed_tools"]) == set(result["tool_permissions"].keys())
