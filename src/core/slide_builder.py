"""スライド構築ユーティリティ

CSV 1行から1枚〜複数枚のサブスライドを展開し、
スライドペイロードを構築する純粋関数群。
pipeline.py から抽出。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from config.settings import settings


def expand_segment_into_slides(
    segment: Any,
    start_slide_id: int,
) -> List[Dict[str, Any]]:
    """CSV 1行を1枚または複数サブスライドに展開"""

    text = (segment.text or "").strip()
    text_length = len(text)
    segment_duration = max(float(segment.end_time - segment.start_time), 0.1)

    slides_settings = settings.SLIDES_SETTINGS
    auto_split = slides_settings.get("auto_split_long_lines", False)
    threshold = int(slides_settings.get("long_line_char_threshold", 9999))
    target_chars = int(slides_settings.get("long_line_target_chars_per_subslide", threshold))
    max_subslides = max(int(slides_settings.get("long_line_max_subslides", 1)), 1)
    min_duration = float(slides_settings.get("min_subslide_duration", 0.5))

    should_split = (
        auto_split
        and max_subslides > 1
        and target_chars > 0
        and text_length >= threshold
    )

    if should_split:
        chunks = split_text_for_subslides(text, target_chars, max_subslides)
    else:
        chunks = [text]

    durations = allocate_subslide_durations(
        total_duration=segment_duration,
        chunks=chunks,
        min_duration=min_duration,
    )

    total_subslides = len(chunks)
    slides: List[Dict[str, Any]] = []
    for idx, chunk in enumerate(chunks):
        slides.append(
            build_slide_dict(
                segment=segment,
                slide_id=start_slide_id + idx,
                text=chunk,
                duration=durations[idx],
                sub_index=idx,
                sub_total=total_subslides,
            )
        )
    return slides


def split_text_for_subslides(
    text: str,
    target_chars: int,
    max_subslides: int,
) -> List[str]:
    """句読点優先で長文を複数スライド用テキストに分割"""

    normalized = (text or "").strip()
    if not normalized:
        return [""]

    chunks: List[str] = []
    remaining = normalized

    while remaining and len(chunks) < max_subslides - 1:
        if len(remaining) <= target_chars:
            break

        split_index = find_split_index(remaining, target_chars)
        chunk = remaining[:split_index].strip()
        if not chunk:
            chunk = remaining[:target_chars]
            split_index = len(chunk)

        chunks.append(chunk)
        remaining = remaining[split_index:].lstrip()

    if remaining:
        chunks.append(remaining)

    return chunks[:max_subslides]


def find_split_index(text: str, preferred_length: int) -> int:
    if len(text) <= preferred_length:
        return len(text)

    search_window = min(len(text), preferred_length + 40)
    slice_text = text[:search_window]

    punctuation_patterns = ["。", "！", "？", "!", "?", "、", ",", " ", "\n"]
    for pattern in punctuation_patterns:
        idx = slice_text.rfind(pattern, 0, search_window)
        if idx != -1 and idx >= int(preferred_length * 0.6):
            return idx + 1

    return preferred_length


def allocate_subslide_durations(
    total_duration: float,
    chunks: List[str],
    min_duration: float,
) -> List[float]:
    if total_duration <= 0:
        total_duration = 0.1 * len(chunks)

    total_chars = sum(max(len(chunk.strip()), 1) for chunk in chunks)
    total_chars = max(total_chars, 1)

    remaining_duration = total_duration
    remaining_chars = total_chars
    durations: List[float] = []

    for idx, chunk in enumerate(chunks):
        chunk_chars = max(len(chunk.strip()), 1)
        slots_left = len(chunks) - idx - 1

        ratio = chunk_chars / remaining_chars if remaining_chars else 0
        duration = total_duration * ratio if ratio > 0 else remaining_duration / max(slots_left + 1, 1)
        duration = max(duration, min_duration)

        max_allowed = remaining_duration - (slots_left * min_duration)
        if max_allowed > 0:
            duration = min(duration, max_allowed)

        durations.append(duration)
        remaining_duration -= duration
        remaining_chars -= chunk_chars

    total_assigned = sum(durations)
    diff = total_duration - total_assigned
    if durations:
        durations[-1] += diff
        if durations[-1] < min_duration:
            deficit = min_duration - durations[-1]
            durations[-1] = min_duration
            for i in range(len(durations) - 2, -1, -1):
                available = durations[i] - min_duration
                if available <= 0:
                    continue
                take = min(available, deficit)
                durations[i] -= take
                deficit -= take
                if deficit <= 0:
                    break

    return durations


def build_slide_dict(
    segment: Any,
    slide_id: int,
    text: str,
    duration: float,
    sub_index: int,
    sub_total: int,
) -> Dict[str, Any]:
    base_title = getattr(segment, "slide_suggestion", None) or (segment.text[:30] if segment.text else f"Segment {segment.id}")
    if sub_total > 1 and sub_index > 0:
        title = f"{base_title}（続き {sub_index + 1}/{sub_total}）"
    else:
        title = base_title

    return {
        "slide_id": slide_id,
        "title": title,
        "text": text,
        "key_points": getattr(segment, "key_points", []),
        "duration": max(duration, 0.1),
        "source_segments": [segment.id],
        "speakers": [segment.speaker] if getattr(segment, "speaker", None) else [],
        "subslide_index": sub_index,
        "subslide_count": sub_total,
        "is_continued": sub_total > 1 and sub_index > 0,
    }


def build_slides_payload(
    segment_payloads: List[Dict[str, Any]],
    csv_path: Path,
) -> Dict[str, Any]:
    video_resolution = settings.VIDEO_SETTINGS.get("resolution", (1920, 1080))
    auto_split = settings.SLIDES_SETTINGS.get("auto_split_long_lines", False)

    payload_segments: List[Dict[str, Any]] = []
    for payload in segment_payloads:
        segment = payload.get("segment")
        slides = payload.get("slides", [])
        audio_file: Optional[Path] = payload.get("audio_file")

        if not segment:
            continue

        converted_slides: List[Dict[str, Any]] = []
        for idx, slide in enumerate(slides):
            converted_slides.append(
                {
                    "slide_id": slide.get("slide_id"),
                    "order": slide.get("subslide_index", idx),
                    "count": slide.get("subslide_count", len(slides)),
                    "title": slide.get("title"),
                    "text": slide.get("text"),
                    "duration": float(slide.get("duration", 0.0) or 0.0),
                    "is_continued": bool(slide.get("is_continued", False)),
                }
            )

        payload_segments.append(
            {
                "segment_id": getattr(segment, "id", None),
                "speaker": getattr(segment, "speaker", ""),
                "start_time": float(getattr(segment, "start_time", 0.0) or 0.0),
                "end_time": float(getattr(segment, "end_time", 0.0) or 0.0),
                "text": getattr(segment, "text", ""),
                "audio_file": str(audio_file) if audio_file else None,
                "subslides": converted_slides,
            }
        )

    return {
        "meta": {
            "source_csv": str(csv_path),
            "generated_at": datetime.now().isoformat(),
            "auto_split": auto_split,
            "video_resolution": list(video_resolution),
            "total_segments": len(payload_segments),
        },
        "segments": payload_segments,
    }
