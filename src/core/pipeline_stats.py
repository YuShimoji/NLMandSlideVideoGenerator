"""パイプライン品質トラッキング (SP-042)

パイプライン実行結果の統計を自動収集し、pipeline_stats.json に保存する。
品質4軸: 制作スピード / 情報密度 / 視覚完成度 / 一貫性
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class StepTimer:
    """個別ステップのタイマー。"""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0

    def start(self) -> None:
        self.start_time = time.monotonic()

    def stop(self) -> None:
        self.end_time = time.monotonic()
        self.duration = self.end_time - self.start_time


@dataclass
class PipelineStats:
    """パイプライン実行統計。"""
    pipeline_id: str = ""
    topic: str = ""
    style: str = "default"
    target_duration: float = 300.0
    timestamp: str = ""

    # 制作スピード
    total_duration: float = 0.0
    step_durations: Dict[str, float] = field(default_factory=dict)
    bottleneck_step: str = ""

    # 情報密度
    source_count: int = 0
    segment_count: int = 0
    alignment_supported: int = 0
    alignment_orphaned: int = 0
    alignment_conflict: int = 0
    alignment_rate: float = 0.0

    # 視覚完成度
    stock_image_count: int = 0
    ai_image_count: int = 0
    text_slide_count: int = 0
    image_hit_rate: float = 0.0
    visual_ratio: float = 0.0

    # 一貫性
    pre_export_errors: int = 0
    pre_export_warnings: int = 0
    speaker_mapping_applied: bool = False
    style_preset: str = ""

    # フォールバック追跡 (F-004)
    fallback_events: List[str] = field(default_factory=list)
    llm_provider_used: str = ""

    # 内部管理
    _timers: Dict[str, StepTimer] = field(default_factory=dict, repr=False)
    _pipeline_start: float = field(default=0.0, repr=False)

    def start_pipeline(self, pipeline_id: str, topic: str, style: str = "default",
                       target_duration: float = 300.0) -> None:
        """パイプライン計測を開始する。"""
        self.pipeline_id = pipeline_id
        self.topic = topic
        self.style = style
        self.style_preset = style
        self.target_duration = target_duration
        self.timestamp = datetime.now().isoformat()
        self._pipeline_start = time.monotonic()

    def start_step(self, step_name: str) -> None:
        """ステップの計測を開始する。"""
        timer = StepTimer(name=step_name)
        timer.start()
        self._timers[step_name] = timer

    def stop_step(self, step_name: str) -> None:
        """ステップの計測を終了する。"""
        timer = self._timers.get(step_name)
        if timer:
            timer.stop()
            self.step_durations[step_name] = round(timer.duration, 2)

    def finalize(self) -> None:
        """全ステップ完了後に集約統計を計算する。"""
        if self._pipeline_start > 0 and self.total_duration == 0.0:
            self.total_duration = round(time.monotonic() - self._pipeline_start, 2)

        # ボトルネック特定
        if self.step_durations:
            self.bottleneck_step = max(self.step_durations, key=self.step_durations.get)  # type: ignore[arg-type]

        # alignment率
        total_alignment = self.alignment_supported + self.alignment_orphaned + self.alignment_conflict
        if total_alignment > 0:
            self.alignment_rate = round(self.alignment_supported / total_alignment, 3)

        # 画像ヒット率
        total_visual = self.stock_image_count + self.ai_image_count + self.text_slide_count
        if total_visual > 0:
            self.image_hit_rate = round(
                (self.stock_image_count + self.ai_image_count) / total_visual, 3
            )

        # 視覚カバー率
        if self.segment_count > 0:
            self.visual_ratio = round(total_visual / self.segment_count, 3)

    def record_sources(self, count: int) -> None:
        """ソース収集結果を記録する。"""
        self.source_count = count

    def record_segments(self, count: int) -> None:
        """セグメント数を記録する。"""
        self.segment_count = count

    def record_alignment(self, supported: int, orphaned: int, conflict: int) -> None:
        """alignment結果を記録する。"""
        self.alignment_supported = supported
        self.alignment_orphaned = orphaned
        self.alignment_conflict = conflict

    def record_visual(self, stock: int = 0, ai: int = 0, text_slide: int = 0) -> None:
        """視覚リソース結果を記録する。"""
        self.stock_image_count = stock
        self.ai_image_count = ai
        self.text_slide_count = text_slide

    def record_validation(self, errors: int = 0, warnings: int = 0) -> None:
        """Pre-Export検証結果を記録する。"""
        self.pre_export_errors = errors
        self.pre_export_warnings = warnings

    def record_fallback(self, event: str) -> None:
        """フォールバック発生を記録する。"""
        self.fallback_events.append(event)

    def record_llm_provider(self, provider: str) -> None:
        """使用されたLLMプロバイダーを記録する。"""
        self.llm_provider_used = provider

    def to_dict(self) -> Dict[str, Any]:
        """JSON シリアライズ用の辞書を返す。"""
        return {
            "pipeline_id": self.pipeline_id,
            "topic": self.topic,
            "style": self.style,
            "target_duration": self.target_duration,
            "timestamp": self.timestamp,
            "speed": {
                "total_duration": self.total_duration,
                "step_durations": self.step_durations,
                "bottleneck_step": self.bottleneck_step,
            },
            "density": {
                "source_count": self.source_count,
                "segment_count": self.segment_count,
                "alignment_supported": self.alignment_supported,
                "alignment_orphaned": self.alignment_orphaned,
                "alignment_conflict": self.alignment_conflict,
                "alignment_rate": self.alignment_rate,
            },
            "visual": {
                "stock_image_count": self.stock_image_count,
                "ai_image_count": self.ai_image_count,
                "text_slide_count": self.text_slide_count,
                "image_hit_rate": self.image_hit_rate,
                "visual_ratio": self.visual_ratio,
            },
            "consistency": {
                "pre_export_errors": self.pre_export_errors,
                "pre_export_warnings": self.pre_export_warnings,
                "speaker_mapping_applied": self.speaker_mapping_applied,
                "style_preset": self.style_preset,
            },
            "fallback": {
                "events": self.fallback_events,
                "llm_provider_used": self.llm_provider_used,
                "fallback_count": len(self.fallback_events),
            },
        }

    def save(self, work_dir: Path) -> Path:
        """pipeline_stats.json を保存する。"""
        path = work_dir / "pipeline_stats.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    @classmethod
    def load(cls, work_dir: Path) -> Optional["PipelineStats"]:
        """pipeline_stats.json を読み込む。"""
        path = work_dir / "pipeline_stats.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        stats = cls()
        stats.pipeline_id = data.get("pipeline_id", "")
        stats.topic = data.get("topic", "")
        stats.style = data.get("style", "default")
        stats.target_duration = data.get("target_duration", 300.0)
        stats.timestamp = data.get("timestamp", "")

        speed = data.get("speed", {})
        stats.total_duration = speed.get("total_duration", 0.0)
        stats.step_durations = speed.get("step_durations", {})
        stats.bottleneck_step = speed.get("bottleneck_step", "")

        density = data.get("density", {})
        stats.source_count = density.get("source_count", 0)
        stats.segment_count = density.get("segment_count", 0)
        stats.alignment_supported = density.get("alignment_supported", 0)
        stats.alignment_orphaned = density.get("alignment_orphaned", 0)
        stats.alignment_conflict = density.get("alignment_conflict", 0)
        stats.alignment_rate = density.get("alignment_rate", 0.0)

        visual = data.get("visual", {})
        stats.stock_image_count = visual.get("stock_image_count", 0)
        stats.ai_image_count = visual.get("ai_image_count", 0)
        stats.text_slide_count = visual.get("text_slide_count", 0)
        stats.image_hit_rate = visual.get("image_hit_rate", 0.0)
        stats.visual_ratio = visual.get("visual_ratio", 0.0)

        consistency = data.get("consistency", {})
        stats.pre_export_errors = consistency.get("pre_export_errors", 0)
        stats.pre_export_warnings = consistency.get("pre_export_warnings", 0)
        stats.speaker_mapping_applied = consistency.get("speaker_mapping_applied", False)
        stats.style_preset = consistency.get("style_preset", "")

        fallback = data.get("fallback", {})
        stats.fallback_events = fallback.get("events", [])
        stats.llm_provider_used = fallback.get("llm_provider_used", "")

        return stats

    def summary(self) -> str:
        """人間可読なサマリーを返す。"""
        lines = [
            f"Pipeline Stats: {self.pipeline_id}",
            f"  Topic: {self.topic}",
            f"  Style: {self.style}, Duration target: {self.target_duration/60:.0f}min",
            f"  Speed: {self.total_duration:.1f}s total, bottleneck={self.bottleneck_step}",
        ]
        if self.step_durations:
            for step, dur in self.step_durations.items():
                pct = (dur / self.total_duration * 100) if self.total_duration > 0 else 0
                lines.append(f"    {step:15s} {dur:6.1f}s ({pct:4.1f}%)")
        lines.extend([
            f"  Density: {self.source_count} sources, {self.segment_count} segments, "
            f"alignment={self.alignment_rate:.0%}",
            f"  Visual: stock={self.stock_image_count}, ai={self.ai_image_count}, "
            f"textslide={self.text_slide_count}, hit_rate={self.image_hit_rate:.0%}",
            f"  Quality: {self.pre_export_errors} errors, {self.pre_export_warnings} warnings",
        ])
        if self.llm_provider_used:
            lines.append(f"  LLM Provider: {self.llm_provider_used}")
        if self.fallback_events:
            lines.append(f"  !! FALLBACK WARNING: {len(self.fallback_events)} fallback(s) triggered:")
            for event in self.fallback_events:
                lines.append(f"    - {event}")
        return "\n".join(lines)
