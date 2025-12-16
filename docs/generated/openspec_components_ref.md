# OpenSpec Component Reference

This document provides detailed specifications for all OpenSpec components.

## Components

### IEditingBackend

**Version**: 1.0.0

**Interface**:
```python
async def render(
    timeline_plan: Dict[str, Any],
    audio: AudioInfo,
    slides: SlidesPackage,
    transcript: TranscriptInfo,
    quality: str
) -> VideoInfo:
```

**Implementations**:
- MoviePyEditingBackend
- YMM4EditingBackend

**Quality Options**:
- 480p
- 720p
- 1080p


**Validation Rules**:
- timeline_plan must be valid structure
- all inputs must be present and valid
- quality must be supported

### IPlatformAdapter

**Version**: 1.0.0

**Interface**:
```python
async def upload(
    video: VideoInfo,
    metadata: UploadMetadata,
    schedule: Optional[datetime]
) -> UploadResult:
```

**Implementations**:
- YouTubePlatformAdapter

**Supported Platforms**:
- youtube
- tiktok
- local

**Validation Rules**:
- video file must exist and be valid
- metadata must contain required fields
- schedule must be future datetime if provided

### IScriptProvider

**Version**: 1.0.0

**Interface**:
```python
async def generate_script(
    topic: str,
    sources: List[SourceInfo],
    mode: str
) -> Dict[str, Any]:
```

**Implementations**:
- GeminiScriptProvider
- NotebookLMScriptProvider

**Validation Rules**:
- topic must be non-empty string
- sources must be valid SourceInfo list
- mode must be one of: auto, assist, manual

### IVoicePipeline

**Version**: 1.0.0

**Interface**:
```python
async def synthesize(
    script: Dict[str, Any],
    preferred_provider: Optional[str]
) -> AudioInfo:
```

**Implementations**:
- TTSVoicePipeline
- GeminiTTSVoicePipeline

**Supported Providers**:
- elevenlabs
- openai
- azure
- google_cloud

**Validation Rules**:
- script must contain required fields
- provider must be supported
- output must be valid AudioInfo
