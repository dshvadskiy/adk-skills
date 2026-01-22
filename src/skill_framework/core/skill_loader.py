"""Skill loader for parsing SKILL.md files."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict

import yaml


@dataclass
class SkillMetadata:
    """Skill metadata from YAML frontmatter."""

    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    activation_mode: str = "auto"  # auto | manual | preload
    required_tools: list[str] = field(default_factory=list)
    optional_tools: list[str] = field(default_factory=list)
    allowed_tools: Optional[str] = None  # Comma-separated allowed tools string
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None  # Custom metadata map
    max_execution_time: Optional[int] = None
    max_memory: Optional[int] = None
    network_access: bool = False
    python_packages: list[str] = field(default_factory=list)
    system_packages: list[str] = field(default_factory=list)


@dataclass
class SkillContent:
    """Full skill content loaded on-demand."""

    name: str
    metadata: SkillMetadata
    instructions: str
    raw_content: str
    file_path: Path


class SkillLoader:
    """
    Loads and parses SKILL.md files.

    Implements progressive disclosure:
    - Load metadata immediately (frontmatter only)
    - Load full content on-demand when skill activated
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = Path(skills_dir)

    def load_skill(self, skill_name: str) -> SkillContent:
        """
        Load full skill content.

        Args:
            skill_name: Name of skill to load

        Returns:
            SkillContent with metadata and instructions

        Raises:
            FileNotFoundError: If SKILL.md not found
            ValueError: If SKILL.md format is invalid
        """
        skill_path = self._find_skill_file(skill_name)
        if not skill_path:
            raise FileNotFoundError(f"SKILL.md not found for '{skill_name}'")

        raw_content = skill_path.read_text(encoding="utf-8")
        metadata, instructions = self._parse_skill_md(raw_content)

        return SkillContent(
            name=skill_name,
            metadata=metadata,
            instructions=instructions,
            raw_content=raw_content,
            file_path=skill_path,
        )

    def load_metadata(self, skill_name: str) -> SkillMetadata:
        """
        Load only skill metadata (progressive disclosure).

        Args:
            skill_name: Name of skill

        Returns:
            SkillMetadata from frontmatter only
        """
        skill_path = self._find_skill_file(skill_name)
        if not skill_path:
            raise FileNotFoundError(f"SKILL.md not found for '{skill_name}'")

        raw_content = skill_path.read_text(encoding="utf-8")
        metadata, _ = self._parse_skill_md(raw_content)
        return metadata

    def _find_skill_file(self, skill_name: str) -> Optional[Path]:
        """Find SKILL.md file for given skill name."""
        direct_path = self.skills_dir / skill_name / "SKILL.md"
        if direct_path.exists():
            return direct_path
        return None

    def _parse_skill_md(self, content: str) -> tuple[SkillMetadata, str]:
        """Parse SKILL.md: metadata + instructions."""
        if not content.startswith("---"):
            raise ValueError("SKILL.md must start with YAML frontmatter (---)")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid SKILL.md format: missing closing ---")

        frontmatter = yaml.safe_load(parts[1])
        instructions = parts[2].strip()

        metadata = SkillMetadata(
            name=frontmatter["name"],
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            author=frontmatter.get("author"),
            tags=frontmatter.get("tags", []),
            activation_mode=frontmatter.get("activation_mode", "auto"),
            required_tools=frontmatter.get("required_tools", []),
            optional_tools=frontmatter.get("optional_tools", []),
            allowed_tools=frontmatter.get("allowed-tools"),  # Note: hyphenated in YAML
            license=frontmatter.get("license"),
            compatibility=frontmatter.get("compatibility"),
            metadata=frontmatter.get("metadata"),
            max_execution_time=frontmatter.get("max_execution_time"),
            max_memory=frontmatter.get("max_memory"),
            network_access=frontmatter.get("network_access", False),
            python_packages=frontmatter.get("python_packages", []),
            system_packages=frontmatter.get("system_packages", []),
        )

        return metadata, instructions
