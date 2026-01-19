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

    def test_load_skill_parses_complete_content(self, loader: SkillLoader, skills_dir: Path):
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
