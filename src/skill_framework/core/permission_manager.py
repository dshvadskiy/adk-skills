"""Permission manager for tool access control."""

from enum import Enum
from typing import Any, Dict

from ..observability.logging_config import get_logger

logger = get_logger(__name__)


class PermissionLevel(Enum):
    """Permission levels for tools"""

    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class PermissionManager:
    """
    Manages fine-grained tool permissions for skills.

    Different skills need different tool access:
    - PDF skill needs file read/write
    - Fraud analysis needs database query
    - Report generation needs file write only
    """

    def __init__(self):
        # Tool permission matrix
        self.tool_permissions = {
            "bash_tool": PermissionLevel.EXECUTE,
            "file_read": PermissionLevel.READ,
            "file_write": PermissionLevel.WRITE,
            "python_execute": PermissionLevel.EXECUTE,
            "database_query": PermissionLevel.READ,
            "database_write": PermissionLevel.WRITE,
            "network_request": PermissionLevel.EXECUTE,
        }

        # Skill-specific permission profiles
        self.skill_profiles = {
            "pdf": {
                "bash_tool": PermissionLevel.EXECUTE,
                "file_read": PermissionLevel.READ,
                "file_write": PermissionLevel.WRITE,
                "python_execute": PermissionLevel.EXECUTE,
            },
            "fraud-analysis": {
                "bash_tool": PermissionLevel.EXECUTE,
                "python_execute": PermissionLevel.EXECUTE,
                "database_query": PermissionLevel.READ,
                "file_read": PermissionLevel.READ,
            },
            "report-generation": {
                "bash_tool": PermissionLevel.EXECUTE,
                "python_execute": PermissionLevel.EXECUTE,
                "file_read": PermissionLevel.READ,
                "file_write": PermissionLevel.WRITE,
            },
            "data-validation": {
                "bash_tool": PermissionLevel.EXECUTE,
                "python_execute": PermissionLevel.EXECUTE,
                "file_read": PermissionLevel.READ,
            },
        }

    def apply_permissions(
        self, skill_name: str, skill_metadata: Any, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply tool permissions for skill.

        Returns modified context with permission constraints.
        """
        logger.debug(f"Applying permissions for skill: {skill_name}")
        # Get skill profile or use metadata
        if skill_name in self.skill_profiles:
            permissions = self.skill_profiles[skill_name]
            logger.debug(f"Using predefined permission profile for {skill_name}")
        else:
            permissions = self._build_permissions_from_metadata(skill_metadata)
            logger.debug(f"Built permissions from metadata for {skill_name}")

        # Apply to context
        context["tool_permissions"] = permissions
        context["allowed_tools"] = list(permissions.keys())

        logger.info(
            f"Permissions applied for skill: {skill_name}, "
            f"allowed_tools={list(permissions.keys())}"
        )

        return context

    def _build_permissions_from_metadata(
        self, metadata: Any
    ) -> Dict[str, PermissionLevel]:
        """Build permission dict from skill metadata"""
        permissions = {}

        for tool in metadata.required_tools:
            # Default to EXECUTE for required tools
            permissions[tool] = PermissionLevel.EXECUTE

        for tool in metadata.optional_tools or []:
            # Optional tools get limited permissions
            permissions[tool] = PermissionLevel.READ

        return permissions

    def check_permission(
        self, tool_name: str, required_level: PermissionLevel, context: Dict[str, Any]
    ) -> bool:
        """
        Check if tool can be used with required permission level.

        Args:
            tool_name: Name of tool to check
            required_level: Minimum required permission
            context: Current execution context

        Returns:
            True if permission granted, False otherwise
        """
        permissions = context.get("tool_permissions", {})

        if tool_name not in permissions:
            logger.warning(
                f"Permission denied: tool '{tool_name}' not in allowed tools"
            )
            return False

        granted_level = permissions[tool_name]

        # Permission hierarchy
        hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.WRITE: 2,
            PermissionLevel.EXECUTE: 3,
            PermissionLevel.ADMIN: 4,
        }

        allowed = hierarchy[granted_level] >= hierarchy[required_level]

        if allowed:
            logger.info(
                f"Permission granted: tool='{tool_name}', "
                f"granted={granted_level.value}, required={required_level.value}"
            )
        else:
            logger.warning(
                f"Permission denied: tool='{tool_name}', "
                f"granted={granted_level.value}, required={required_level.value}"
            )

        return allowed
