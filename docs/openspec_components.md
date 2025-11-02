# OpenSpec: Pipeline Components

## IScriptProvider
```openspec
component: IScriptProvider
version: 1.0.0
interface:
  generate_script(topic: str, sources: List[SourceInfo], mode: str) -> Dict[str, Any]
implementations:
  - GeminiScriptProvider
  - NotebookLMScriptProvider
validation:
  - topic must be non-empty string
  - sources must be valid SourceInfo list
  - mode must be one of: auto, assist, manual
```

## IVoicePipeline
```openspec
component: IVoicePipeline
version: 1.0.0
interface:
  synthesize(script: Dict[str, Any], preferred_provider: Optional[str]) -> AudioInfo
implementations:
  - TTSVoicePipeline
  - GeminiTTSVoicePipeline
providers:
  - elevenlabs
  - openai
  - azure
  - google_cloud
validation:
  - script must contain required fields
  - provider must be supported
  - output must be valid AudioInfo
```

## IEditingBackend
```openspec
component: IEditingBackend
version: 1.0.0
interface:
  render(timeline_plan: Dict[str, Any], audio: AudioInfo, slides: SlidesPackage, transcript: TranscriptInfo, quality: str) -> VideoInfo
implementations:
  - MoviePyEditingBackend
  - YMM4EditingBackend
quality_options:
  - 720p
  - 1080p
  - 4k
validation:
  - timeline_plan must be valid structure
  - all inputs must be present and valid
  - quality must be supported
```

## IPlatformAdapter
```openspec
component: IPlatformAdapter
version: 1.0.0
interface:
  upload(video: VideoInfo, metadata: UploadMetadata, schedule: Optional[datetime]) -> UploadResult
implementations:
  - YouTubePlatformAdapter
platforms:
  - youtube
  - tiktok
  - local
validation:
  - video file must exist and be valid
  - metadata must contain required fields
  - schedule must be future datetime if provided
```

## IThumbnailGenerator
```openspec
component: IThumbnailGenerator
version: 1.0.0
interface:
  generate(video: VideoInfo, script: Dict[str, Any], slides: SlidesPackage, style: str) -> ThumbnailInfo
implementations:
  - AIThumbnailGenerator
  - TemplateThumbnailGenerator
styles:
  - modern
  - classic
  - gaming
  - educational
validation:
  - video file must exist
  - script must contain title and key points
  - style must be supported
  - output must be valid image file
```
