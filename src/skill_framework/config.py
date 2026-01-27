"""Configuration management for skill framework."""

import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration loader for skill framework."""

    @staticmethod
    def get_skills_dir(default: Optional[Path] = None) -> Path:
        """
        Get skills directory from environment or default.

        Checks SKILLS_DIR environment variable. If not set, uses provided default
        or falls back to 'skills' directory relative to project root.

        Args:
            default: Optional default path if SKILLS_DIR not set

        Returns:
            Path to skills directory (absolute)
        """
        skills_dir_str = os.getenv("SKILLS_DIR")

        if skills_dir_str:
            skills_path = Path(skills_dir_str)
        elif default:
            skills_path = default
        else:
            # Default to 'skills' directory in project root
            # Assumes config.py is in src/skill_framework/
            project_root = Path(__file__).parent.parent.parent
            skills_path = project_root / "skills"

        # Convert to absolute path if relative
        if not skills_path.is_absolute():
            project_root = Path(__file__).parent.parent.parent
            skills_path = project_root / skills_path

        return skills_path.resolve()

    @staticmethod
    def get_artifact_s3_bucket() -> Optional[str]:
        """Get S3 bucket for artifact storage."""
        return os.getenv("ARTIFACT_S3_BUCKET")

    @staticmethod
    def get_artifact_s3_path() -> Optional[str]:
        """Get S3 path prefix for artifacts."""
        return os.getenv("ARTIFACT_S3_PATH")

    @staticmethod
    def get_model_id() -> Optional[str]:
        """Get model ID from environment."""
        return os.getenv("MODEL_ID")

    @staticmethod
    def get_aws_region() -> str:
        """Get AWS region from environment."""
        return os.getenv("AWS_REGION", "us-east-1")
