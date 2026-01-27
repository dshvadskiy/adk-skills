# Artifact Publishing

## Overview
Skills that generate files (PDF, DOCX, PPTX, etc.) should output them using the `FILE_OUTPUT` marker pattern. The chat server automatically uploads to S3 (production) or serves locally (development).

## Configuration

Set environment variables:
```bash
# S3 storage (production)
ARTIFACT_S3_BUCKET=my-bucket
ARTIFACT_S3_PATH=artifacts/      # optional, default: artifacts/
AWS_REGION=us-east-1             # optional

# Local storage (development) - no config needed, auto-fallback
```

## Skill Output Pattern

When your skill generates a file, output this marker:
```
FILE_OUTPUT: {"path": "/absolute/path/to/file.pdf", "filename": "report.pdf", "mime_type": "application/pdf"}
```

### Example Skill Script
```python
#!/usr/bin/env python3
from pathlib import Path

# Generate file
output_path = Path("/tmp/report.pdf")
# ... create file ...

# Output marker for chat server
print(f'FILE_OUTPUT: {{"path": "{output_path}", "filename": "{output_path.name}", "mime_type": "application/pdf"}}')
```

## Multiple Files

Output multiple `FILE_OUTPUT` markers - they'll be automatically zipped:
```
FILE_OUTPUT: {"path": "/tmp/doc1.pdf", "filename": "doc1.pdf", "mime_type": "application/pdf"}
FILE_OUTPUT: {"path": "/tmp/doc2.docx", "filename": "doc2.docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
```

## Supported MIME Types

| Extension | MIME Type |
|-----------|-----------|
| .pdf | application/pdf |
| .docx | application/vnd.openxmlformats-officedocument.wordprocessingml.document |
| .pptx | application/vnd.openxmlformats-officedocument.presentationml.presentation |
| .xlsx | application/vnd.openxmlformats-officedocument.spreadsheetml.sheet |
| .html | text/html |
| .json | application/json |
| .csv | text/csv |
| .png | image/png |
| .jpg/.jpeg | image/jpeg |
| .zip | application/zip |

## Programmatic Usage

```python
from skill_framework.artifact_publisher import publish_artifact, publish_artifacts

# Single file
artifact = publish_artifact("/path/to/file.pdf")
print(artifact.url)  # S3 presigned URL or /api/files/xxx

# Multiple files (auto-zipped)
artifact = publish_artifacts(["/path/to/a.pdf", "/path/to/b.docx"])
print(artifact.url)  # URL to zip file
```
