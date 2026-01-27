"""Artifact publisher for uploading generated files to S3 with download URLs."""

import os
import uuid
import zipfile
from pathlib import Path
from dataclasses import dataclass
from typing import Protocol

import boto3  # type: ignore[import-untyped]


@dataclass
class Artifact:
    """Published artifact with download URL."""

    filename: str
    url: str
    mime_type: str
    size: int


class StorageBackend(Protocol):
    """Protocol for storage backends."""

    def upload(self, file_path: Path, key: str, mime_type: str) -> str:
        """Upload file and return download URL."""
        ...


class S3Backend:
    """S3 storage backend with presigned URLs."""

    def __init__(
        self,
        bucket: str,
        path_prefix: str = "artifacts/",
        region: str | None = None,
        url_expiry: int = 604800,  # 7 days
    ):
        self.bucket = bucket
        self.path_prefix = path_prefix.rstrip("/") + "/"
        self.url_expiry = url_expiry
        self.s3 = boto3.client(
            "s3", region_name=region or os.getenv("AWS_REGION", "us-east-1")
        )

    def upload(self, file_path: Path, key: str, mime_type: str) -> str:
        """Upload to S3 and return presigned URL."""
        s3_key = f"{self.path_prefix}{key}"

        self.s3.upload_file(
            str(file_path),
            self.bucket,
            s3_key,
            ExtraArgs={"ContentType": mime_type},
        )

        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=self.url_expiry,
        )


class LocalBackend:
    """Local storage backend for development."""

    def __init__(self, base_url: str = "/api/files"):
        self.base_url = base_url.rstrip("/")
        self.files: dict[str, Path] = {}

    def upload(self, file_path: Path, key: str, mime_type: str) -> str:
        """Store file reference and return local URL."""
        self.files[key] = file_path
        return f"{self.base_url}/{key}"

    def get_file(self, key: str) -> Path | None:
        """Get file path by key."""
        return self.files.get(key)


class ArtifactPublisher:
    """Publishes artifacts to storage and returns download URLs."""

    MIME_TYPES = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".html": "text/html",
        ".json": "application/json",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".zip": "application/zip",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }

    def __init__(self, backend: StorageBackend | None = None):
        """Initialize with storage backend. Auto-configures from env if not provided."""
        if backend:
            self.backend = backend
        elif os.getenv("ARTIFACT_S3_BUCKET"):
            self.backend = S3Backend(
                bucket=os.environ["ARTIFACT_S3_BUCKET"],
                path_prefix=os.getenv("ARTIFACT_S3_PATH", "artifacts/"),
                region=os.getenv("AWS_REGION"),
            )
        else:
            self.backend = LocalBackend()

    def _get_mime_type(self, path: Path) -> str:
        """Get MIME type from file extension."""
        return self.MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")

    def _generate_key(self, filename: str) -> str:
        """Generate unique storage key."""
        return f"{uuid.uuid4().hex[:12]}_{filename}"

    def publish(self, file_path: Path | str) -> Artifact:
        """Publish single file and return artifact with download URL."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        mime_type = self._get_mime_type(path)
        key = self._generate_key(path.name)
        url = self.backend.upload(path, key, mime_type)

        return Artifact(
            filename=path.name,
            url=url,
            mime_type=mime_type,
            size=path.stat().st_size,
        )

    def publish_many(
        self, file_paths: list[Path | str], zip_name: str = "artifacts.zip"
    ) -> Artifact:
        """Publish multiple files as a zip archive."""
        paths = [Path(p) for p in file_paths]

        # Validate all files exist
        for p in paths:
            if not p.exists():
                raise FileNotFoundError(f"File not found: {p}")

        # Create temp zip
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            zip_path = Path(tmp.name)

        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for p in paths:
                    zf.write(p, p.name)

            return self.publish(zip_path)
        finally:
            zip_path.unlink(missing_ok=True)


# Singleton for easy access
_publisher: ArtifactPublisher | None = None


def get_publisher() -> ArtifactPublisher:
    """Get or create singleton publisher instance."""
    global _publisher
    if _publisher is None:
        _publisher = ArtifactPublisher()
    return _publisher


def publish_artifact(file_path: Path | str) -> Artifact:
    """Convenience function to publish single artifact."""
    return get_publisher().publish(file_path)


def publish_artifacts(
    file_paths: list[Path | str], zip_name: str = "artifacts.zip"
) -> Artifact:
    """Convenience function to publish multiple artifacts as zip."""
    return get_publisher().publish_many(file_paths, zip_name)
