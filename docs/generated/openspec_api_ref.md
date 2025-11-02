# OpenSpec API Reference

Complete API reference for OpenSpec components.

## Core Interfaces

### IEditingBackend
Detailed API for IEditingBackend.

#### Methods
- See interface definition for method signatures

#### Error Handling
- Implementations should raise appropriate exceptions

#### Async Support
- All methods are async for non-blocking operations

### IPlatformAdapter
Detailed API for IPlatformAdapter.

#### Methods
- See interface definition for method signatures

#### Error Handling
- Implementations should raise appropriate exceptions

#### Async Support
- All methods are async for non-blocking operations

### IScriptProvider
Detailed API for IScriptProvider.

#### Methods
- See interface definition for method signatures

#### Error Handling
- Implementations should raise appropriate exceptions

#### Async Support
- All methods are async for non-blocking operations

### IVoicePipeline
Detailed API for IVoicePipeline.

#### Methods
- See interface definition for method signatures

#### Error Handling
- Implementations should raise appropriate exceptions

#### Async Support
- All methods are async for non-blocking operations

## Data Types

### AudioInfo
Represents audio file information and metadata.

### VideoInfo
Represents video file information and metadata.

### SlidesPackage
Contains slide presentation data and metadata.

### TranscriptInfo
Contains transcription data and timing information.

### UploadResult
Contains upload operation results and metadata.

### UploadMetadata
Contains metadata required for upload operations.

## Error Types

### ValidationError
Raised when component validation fails.

### ConfigurationError
Raised when pipeline configuration is invalid.

### ProcessingError
Raised when component processing fails.

### NetworkError
Raised when network operations fail.
