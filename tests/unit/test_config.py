"""Tests for configuration management."""

import os
from pathlib import Path
from unittest.mock import patch

from skill_framework.config import Config


class TestConfig:
    """Test configuration loading."""

    def test_get_skills_dir_from_env(self, tmp_path: Path) -> None:
        """Test loading skills directory from SKILLS_DIR environment variable."""
        test_dir = tmp_path / "custom_skills"
        test_dir.mkdir()

        with patch.dict(os.environ, {"SKILLS_DIR": str(test_dir)}):
            result = Config.get_skills_dir()

        assert result == test_dir.resolve()

    def test_get_skills_dir_default(self) -> None:
        """Test default skills directory when SKILLS_DIR not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = Config.get_skills_dir()

        # Should default to project_root/skills
        assert result.name == "skills"
        assert result.is_absolute()

    def test_get_skills_dir_with_explicit_default(self, tmp_path: Path) -> None:
        """Test providing explicit default path."""
        default_dir = tmp_path / "default_skills"
        default_dir.mkdir()

        with patch.dict(os.environ, {}, clear=True):
            result = Config.get_skills_dir(default=default_dir)

        assert result == default_dir.resolve()

    def test_get_skills_dir_relative_path(self, tmp_path: Path) -> None:
        """Test that relative paths are converted to absolute."""
        with patch.dict(os.environ, {"SKILLS_DIR": "my_skills"}):
            result = Config.get_skills_dir()

        # Should be absolute
        assert result.is_absolute()
        assert result.name == "my_skills"

    def test_get_artifact_s3_bucket(self) -> None:
        """Test loading S3 bucket from environment."""
        test_bucket = "test-bucket-123"

        with patch.dict(os.environ, {"ARTIFACT_S3_BUCKET": test_bucket}):
            result = Config.get_artifact_s3_bucket()

        assert result == test_bucket

    def test_get_artifact_s3_bucket_not_set(self) -> None:
        """Test S3 bucket returns None when not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = Config.get_artifact_s3_bucket()

        assert result is None

    def test_get_artifact_s3_path(self) -> None:
        """Test loading S3 path from environment."""
        test_path = "artifacts/test/"

        with patch.dict(os.environ, {"ARTIFACT_S3_PATH": test_path}):
            result = Config.get_artifact_s3_path()

        assert result == test_path

    def test_get_model_id(self) -> None:
        """Test loading model ID from environment."""
        test_model = "test-model-id"

        with patch.dict(os.environ, {"MODEL_ID": test_model}):
            result = Config.get_model_id()

        assert result == test_model

    def test_get_aws_region_default(self) -> None:
        """Test AWS region defaults to us-east-1."""
        with patch.dict(os.environ, {}, clear=True):
            result = Config.get_aws_region()

        assert result == "us-east-1"

    def test_get_aws_region_from_env(self) -> None:
        """Test loading AWS region from environment."""
        test_region = "eu-west-1"

        with patch.dict(os.environ, {"AWS_REGION": test_region}):
            result = Config.get_aws_region()

        assert result == test_region
