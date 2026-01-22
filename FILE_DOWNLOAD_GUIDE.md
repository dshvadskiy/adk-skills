# File Download Support for Skills Framework

## Overview

This guide explains how to support file downloads for skills that generate files (e.g., PowerPoint presentations, PDFs, Excel files).

## Architecture

### 1. **File Output Protocol**

Skills that generate files use a standardized output marker:

```
FILE_OUTPUT: {"path": "/tmp/skill_outputs/{session_id}/{filename}", "filename": "{filename}", "mime_type": "application/..."}
```

### 2. **Backend Flow**

```
User Request → Agent + Skill → File Generated → Response Parsed → File Registered → Download Link Created
```

**Components:**

- **`extract_file_outputs()`**: Parses agent response for FILE_OUTPUT markers
- **`file_storage`**: In-memory dict mapping file IDs to file paths
- **`/api/files/{file_id}`**: Download endpoint serving files
- **`ChatResponse.files`**: Array of file metadata with download URLs

### 3. **Frontend Flow**

```
Response Received → Files Array Parsed → Download Buttons Rendered → User Clicks → File Downloaded
```

**UI Features:**
- File attachment cards with icons
- File type detection (PPTX, PDF, DOCX, etc.)
- Download buttons with hover effects
- Responsive design

## Implementation Details

### Backend (`chat_server.py`)

#### 1. Response Model Extension
```python
class ChatResponse(BaseModel):
    response: str
    session_id: str
    active_skills: list[str]
    files: list[dict[str, str]] | None = None
```

#### 2. File Extraction
```python
def extract_file_outputs(response: str, session_id: str) -> list[dict[str, str]] | None:
    pattern = r'FILE_OUTPUT:\s*\{"path":\s*"([^"]+)",\s*"filename":\s*"([^"]+)",\s*"mime_type":\s*"([^"]+)"\}'
    matches = re.findall(pattern, response)
    
    files = []
    for path_str, filename, mime_type in matches:
        file_path = Path(path_str)
        if file_path.exists():
            file_id = f"{session_id}_{uuid.uuid4().hex[:8]}"
            file_storage[file_id] = file_path
            files.append({
                "filename": filename,
                "url": f"/api/files/{file_id}",
                "mime_type": mime_type,
            })
    return files if files else None
```

#### 3. Download Endpoint
```python
@app.get("/api/files/{file_id}")
async def download_file(file_id: str):
    if file_id not in file_storage:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = file_storage[file_id]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File no longer exists")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )
```

### Frontend (`chat.html`)

#### 1. File Attachment UI
```javascript
function addMessage(role, content, files = null) {
    // ... existing code ...
    
    if (files && files.length > 0) {
        filesHtml = '<div class="file-attachments">';
        files.forEach(file => {
            const icon = getFileIcon(file.filename);
            const fileType = file.mime_type.split('/').pop().toUpperCase();
            filesHtml += `
                <div class="file-attachment">
                    <div class="file-icon">${icon}</div>
                    <div class="file-info">
                        <div class="file-name">${escapeHtml(file.filename)}</div>
                        <div class="file-type">${fileType}</div>
                    </div>
                    <a href="${file.url}" class="download-btn" download="${file.filename}">
                        ⬇️ Download
                    </a>
                </div>
            `;
        });
        filesHtml += '</div>';
    }
}
```

#### 2. File Icon Mapping
```javascript
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const iconMap = {
        'pptx': '📊', 'pdf': '📄', 'docx': '📝',
        'xlsx': '📈', 'zip': '🗜️', 'png': '🖼️',
        // ... more mappings
    };
    return iconMap[ext] || '📎';
}
```

## Creating File-Generating Skills

### SKILL.md Template

```yaml
---
name: your-skill-name
description: What your skill does
version: 1.0.0
required_tools:
  - python_execute  # or bash_tool
activation_mode: auto
output_type: file
output_formats:
  - pptx
  - pdf
---

# Your Skill Name

## File Output Protocol

**CRITICAL**: When generating files, follow this protocol:

1. **Save Location**: `/tmp/skill_outputs/{session_id}/{filename}`
2. **Output Marker**: 
   ```
   FILE_OUTPUT: {"path": "/tmp/skill_outputs/{session_id}/{filename}", "filename": "{filename}", "mime_type": "application/..."}
   ```
3. **User Message**: Provide friendly confirmation

## Example Code

```python
import os

session_id = os.environ.get('SESSION_ID', 'default')
output_dir = f'/tmp/skill_outputs/{session_id}'
os.makedirs(output_dir, exist_ok=True)

# Generate your file
filename = 'output.pptx'
filepath = os.path.join(output_dir, filename)

# ... file generation logic ...

print(f"File saved to: {filepath}")
```

Then in your response, include:
```
I've created your file!

FILE_OUTPUT: {"path": "/tmp/skill_outputs/{session_id}/output.pptx", "filename": "output.pptx", "mime_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
```
```

## MIME Types Reference

| File Type | MIME Type |
|-----------|-----------|
| PPTX | `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| DOCX | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| XLSX | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` |
| PDF | `application/pdf` |
| ZIP | `application/zip` |
| PNG | `image/png` |
| JPEG | `image/jpeg` |
| CSV | `text/csv` |
| TXT | `text/plain` |

## Testing

### 1. Start the Chat Server
```bash
uv run python examples/chat_server.py
```

### 2. Test with PowerPoint Skill
Open http://localhost:8000 and try:
```
Create a 3-slide presentation about AI trends in 2024
```

### 3. Expected Behavior
1. Agent activates `powerpoint-generator` skill
2. Python code generates PPTX file
3. Response includes FILE_OUTPUT marker
4. UI displays download button
5. User clicks to download file

## Production Considerations

### 1. **File Storage**
- Current: In-memory dict (lost on restart)
- Production: Use Redis, database, or cloud storage (S3, GCS)

```python
# Example with Redis
import redis
redis_client = redis.Redis()

def register_file(session_id: str, file_path: Path) -> str:
    file_id = f"{session_id}_{uuid.uuid4().hex[:8]}"
    redis_client.setex(
        f"file:{file_id}",
        3600,  # 1 hour TTL
        str(file_path)
    )
    return file_id
```

### 2. **File Cleanup**
Implement automatic cleanup to prevent disk space issues:

```python
import asyncio
from datetime import datetime, timedelta

async def cleanup_old_files():
    while True:
        cutoff = datetime.now() - timedelta(hours=1)
        for file_id, file_path in list(file_storage.items()):
            if file_path.stat().st_mtime < cutoff.timestamp():
                file_path.unlink(missing_ok=True)
                del file_storage[file_id]
        await asyncio.sleep(300)  # Every 5 minutes

# Start cleanup task
@app.on_event("startup")
async def start_cleanup():
    asyncio.create_task(cleanup_old_files())
```

### 3. **Security**
- Validate file paths to prevent directory traversal
- Limit file sizes
- Scan for malware in production
- Use signed URLs for cloud storage

```python
def validate_file_path(file_path: Path) -> bool:
    """Ensure file is in allowed directory."""
    allowed_dir = Path("/tmp/skill_outputs").resolve()
    try:
        file_path.resolve().relative_to(allowed_dir)
        return True
    except ValueError:
        return False
```

### 4. **Multi-Session Support**
Pass session_id to agent execution context:

```python
# In agent execution
os.environ['SESSION_ID'] = session_id
response = await agent_instance.chat(request.message)
```

### 5. **Cloud Storage Integration**
For deployed agents (AWS Bedrock, GCP Vertex AI):

```python
import boto3

s3_client = boto3.client('s3')

def upload_to_s3(file_path: Path, session_id: str) -> str:
    key = f"skill_outputs/{session_id}/{file_path.name}"
    s3_client.upload_file(
        str(file_path),
        'your-bucket',
        key,
        ExtraArgs={'ContentType': 'application/octet-stream'}
    )
    
    # Generate presigned URL (expires in 1 hour)
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'your-bucket', 'Key': key},
        ExpiresIn=3600
    )
    return url
```

## WebSocket Support

For real-time streaming, update the WebSocket handler:

```python
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    # ... existing code ...
    
    response = await agent_instance.chat(user_message)
    active_skills = agent_instance.active_skills
    files = extract_file_outputs(response, session_id)
    
    await websocket.send_json({
        "type": "response",
        "content": response,
        "session_id": session_id,
        "active_skills": active_skills,
        "files": files,  # Add files to WebSocket response
    })
```

## Example Skills with File Output

### 1. **PowerPoint Generator** ✅
- Location: `skills/powerpoint-generator/SKILL.md`
- Output: `.pptx` files
- Tool: `python_execute` with `python-pptx`

### 2. **PDF Report Generator**
```yaml
---
name: pdf-report-generator
output_type: file
output_formats: [pdf]
required_tools: [python_execute]
---
# Uses reportlab or weasyprint
```

### 3. **Excel Data Exporter**
```yaml
---
name: excel-exporter
output_type: file
output_formats: [xlsx, csv]
required_tools: [python_execute]
---
# Uses openpyxl or pandas
```

### 4. **Image Generator**
```yaml
---
name: image-generator
output_type: file
output_formats: [png, jpg, svg]
required_tools: [python_execute]
---
# Uses PIL, matplotlib, or API calls
```

## Troubleshooting

### Files Not Appearing
1. Check agent response contains FILE_OUTPUT marker
2. Verify file path exists: `ls /tmp/skill_outputs/`
3. Check browser console for JavaScript errors
4. Verify `extract_file_outputs()` regex matches

### Download Fails
1. Check file_id exists in `file_storage`
2. Verify file still exists on disk
3. Check file permissions
4. Review server logs for errors

### UI Not Updating
1. Verify `ChatResponse.files` is populated
2. Check `addMessage()` receives files parameter
3. Inspect network response in browser DevTools
4. Verify CSS styles are loaded

## Summary

This implementation provides:
- ✅ Standardized file output protocol
- ✅ Automatic file registration and download links
- ✅ Beautiful UI with file attachments
- ✅ Support for multiple file types
- ✅ Example PowerPoint generator skill
- ✅ Production-ready patterns for scaling

The system is fully functional for local development. For production deployment, implement cloud storage, proper cleanup, and security measures as outlined above.
