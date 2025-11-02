# OpenSpec Integration Guide

This guide explains how to integrate OpenSpec components into your application.

## Pipeline Configuration
Components are configured through the pipeline configuration system:
```python
PIPELINE_COMPONENTS = {
    "script_provider": "gemini",
    "voice_pipeline": "tts",
    "editing_backend": "moviepy",
    "platform_adapter": "youtube"
}
```

## Component Injection
Components are automatically injected based on configuration:
```python
from src.core.pipeline import build_default_pipeline

pipeline = await build_default_pipeline()
result = await pipeline.run(topic="Your Topic")
```

## Custom Implementations
To add custom implementations:
1. Implement the required interface
2. Add to OpenSpec specification
3. Register in pipeline configuration

## Validation
Run validation to ensure compliance:
```bash
python scripts/validate_openspec.py
```

## Development Workflow
1. Define component specification in `docs/openspec_components.md`
2. Generate interface stubs with `scripts/generate_interfaces.py`
3. Implement the component following the interface
4. Validate implementation with `scripts/validate_openspec.py`
5. Generate documentation with `scripts/generate_docs.py`
6. Run tests with `python -m pytest`

## Best Practices
- Always implement all interface methods exactly
- Include comprehensive error handling
- Provide configuration options via constructor
- Document behavior and constraints clearly
- Test implementations thoroughly
