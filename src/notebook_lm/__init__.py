"""
NotebookLM関連モジュール

根本ワークフロー (DESIGN_FOUNDATIONS.md Section 0):
  NLMソース投入 → Audio Overview → テキスト化 → Gemini構造化 → CSV → YMM4

主要クラス:
  AudioTranscriber  — 音声→構造化JSON (SP-051, Gemini Audio API)
  GeminiIntegration — テキスト→構造化JSON (メイン), ソース→台本 (フォールバック)
  NLMAutomation     — NotebookLM Web UI 半自動化 (SP-047, Playwright)
  NotebookLMClient  — notebooklm-py ラッパー (SP-047 Phase 2)
"""

from .research_models import SourceInfo
from .audio_generator import AudioGenerator, AudioInfo
from .transcript_processor import TranscriptProcessor, TranscriptInfo, TranscriptSegment

__all__ = [
    "SourceInfo",
    "AudioGenerator",
    "AudioInfo",
    "TranscriptProcessor",
    "TranscriptInfo",
    "TranscriptSegment",
]
