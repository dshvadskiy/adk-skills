"""Tests for SkillLoader - SKILL.md parsing and progressive disclosure."""

from pathlib import Path

import pytest

from skill_framework.core import SkillLoader, SkillMetadata, SkillContent


class TestSkillLoader:
    """Test suite for SkillLoader using real hello-world fixture."""

    @pytest.fixture
    def skills_dir(self) -> Path:
        """Return the project's skills directory."""
        return Path(__file__).parent.parent.parent / "skills"

    @pytest.fixture
    def loader(self, skills_dir: Path) -> SkillLoader:
        """Create SkillLoader instance."""
        return SkillLoader(skills_dir=skills_dir)

    def test_load_skill_parses_complete_content(
        self, loader: SkillLoader, skills_dir: Path
    ):
        """Test that load_skill returns SkillContent with all parsed data."""
        result = loader.load_skill("hello-world")

        # Returns correct type
        assert isinstance(result, SkillContent)
        assert result.name == "hello-world"

        # Metadata parsed from YAML frontmatter
        assert result.metadata.name == "hello-world"
        assert result.metadata.description == "A simple test skill that greets the user"
        assert result.metadata.version == "1.0.0"
        assert result.metadata.author == "ADK Skills Team"
        assert result.metadata.tags == ["test", "example"]
        assert result.metadata.activation_mode == "auto"
        assert result.metadata.max_execution_time == 30
        assert result.metadata.network_access is False

        # Instructions (markdown body) parsed
        assert "# Hello World Skill" in result.instructions
        assert "greeting-related requests" in result.instructions

        # Raw content preserved
        assert result.raw_content.startswith("---")
        assert "name: hello-world" in result.raw_content

        # File path stored
        assert result.file_path == skills_dir / "hello-world" / "SKILL.md"

    def test_load_metadata_returns_only_metadata(self, loader: SkillLoader):
        """Test progressive disclosure: load_metadata returns SkillMetadata only."""
        result = loader.load_metadata("hello-world")

        assert isinstance(result, SkillMetadata)
        assert result.name == "hello-world"
        assert result.description == "A simple test skill that greets the user"

    def test_load_nonexistent_skill_raises(self, loader: SkillLoader):
        """Test that loading nonexistent skill raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load_skill("nonexistent-skill")

        with pytest.raises(FileNotFoundError, match="not found"):
            loader.load_metadata("nonexistent-skill")

    def test_parse_new_metadata_fields(self, loader: SkillLoader, tmp_path: Path):
        """Test parsing of new metadata fields: allowed-tools, license, compatibility, metadata."""
        # Create a test skill with all new fields
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        skill_content = """---
name: test-skill
description: Test skill with new fields
version: 1.0.0
allowed-tools: "Bash(python:*),Read,Write"
license: MIT
compatibility: "Python 3.10+"
metadata:
  custom_field: "custom_value"
  another_field: "another_value"
max_execution_time: 60
network_access: false
---

# Test Skill
Test instructions here.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create loader for temp directory
        temp_loader = SkillLoader(skills_dir=tmp_path)
        result = temp_loader.load_skill("test-skill")

        # Verify new fields are parsed correctly
        assert result.metadata.allowed_tools == "Bash(python:*),Read,Write"
        assert result.metadata.license == "MIT"
        assert result.metadata.compatibility == "Python 3.10+"
        assert result.metadata.metadata == {
            "custom_field": "custom_value",
            "another_field": "another_value",
        }

    def test_backward_compatibility_without_new_fields(
        self, loader: SkillLoader, tmp_path: Path
    ):
        """Test that skills without new fields still parse correctly (backward compatibility)."""
        # Create a minimal skill without new fields
        skill_dir = tmp_path / "minimal-skill"
        skill_dir.mkdir()

        skill_content = """---
name: minimal-skill
description: Minimal skill without new fields
---

# Minimal Skill
Basic instructions.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create loader for temp directory
        temp_loader = SkillLoader(skills_dir=tmp_path)
        result = temp_loader.load_skill("minimal-skill")

        # Verify new fields have default values
        assert result.metadata.allowed_tools is None
        assert result.metadata.license is None
        assert result.metadata.compatibility is None
        assert result.metadata.metadata is None
        assert result.metadata.max_execution_time is None
        assert result.metadata.network_access is False

    def test_hyphenated_yaml_keys_map_to_underscored_attributes(
        self, loader: SkillLoader, tmp_path: Path
    ):
        """Test that hyphenated YAML keys (allowed-tools) map to underscored Python attributes."""
        skill_dir = tmp_path / "hyphen-test"
        skill_dir.mkdir()

        skill_content = """---
name: hyphen-test
description: Test hyphenated keys
allowed-tools: "Bash(git:*)"
---

# Test
Instructions.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        temp_loader = SkillLoader(skills_dir=tmp_path)
        result = temp_loader.load_metadata("hyphen-test")

        # Verify hyphenated YAML key maps to underscored attribute
        assert hasattr(result, "allowed_tools")
        assert result.allowed_tools == "Bash(git:*)"
