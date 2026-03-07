"""No-op TTS voice pipeline stub.

The full TTSVoicePipeline (ElevenLabs/OpenAI/Azure/Google Cloud) was removed
during dependency cleanup (2026-03-07). YMM4 built-in voice is the sole
recommended TTS method.

This stub satisfies the IVoicePipeline protocol to prevent ImportError and
maintain interface compliance in tests and pipeline construction.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from audio.tts_integration import TTSIntegration
from ..interfaces import IVoicePipeline


class TTSVoicePipeline(IVoicePipeline):
    """No-op voice pipeline. Raises NotImplementedError on synthesis."""

    def __init__(self, output_dir: Any = None) -> None:
        self.output_dir = output_dir
        self.tts = TTSIntegration()

    async def synthesize(
        self,
        script: Dict[str, Any],
        preferred_provider: Optional[str] = None,
    ) -> None:
        raise NotImplementedError(
            "External TTS providers have been removed. Use YMM4 built-in voice."
        )
