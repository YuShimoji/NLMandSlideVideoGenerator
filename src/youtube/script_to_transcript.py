"""ScriptBundle → TranscriptInfo 変換アダプタ (SP-038 Phase 1)

パイプラインが生成する script_bundle (Dict) を
MetadataGenerator が期待する TranscriptInfo へ変換する。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment


def script_bundle_to_transcript(
    bundle: Dict[str, Any],
    *,
    topic: str = "",
) -> TranscriptInfo:
    """ScriptBundle辞書をTranscriptInfoに変換する。

    Args:
        bundle: GeminiProvider等が出力するscript_bundle辞書。
            期待キー: title, segments[], total_duration (いずれもオプション)
        topic: フォールバック用トピック名。bundle に title がない場合に使用。

    Returns:
        TranscriptInfo
    """
    title = bundle.get("title") or topic or "Untitled"
    raw_segments: List[Dict[str, Any]] = bundle.get("segments", [])

    segments: List[TranscriptSegment] = []
    cumulative_time = 0.0

    for i, seg in enumerate(raw_segments):
        text = seg.get("text", seg.get("content", ""))
        speaker = seg.get("speaker", seg.get("speaker_id", f"Speaker{(i % 2) + 1}"))
        start_time = float(seg.get("start_time", cumulative_time))
        duration = float(seg.get("duration", 30.0))
        end_time = float(seg.get("end_time", start_time + duration))

        key_points: List[str] = seg.get("key_points", [])
        if not key_points:
            # タイトルやトピックからフォールバック
            seg_title = seg.get("title", "")
            if seg_title:
                key_points = [seg_title]

        segments.append(
            TranscriptSegment(
                id=i,
                start_time=start_time,
                end_time=end_time,
                speaker=str(speaker),
                text=str(text),
                key_points=key_points,
                slide_suggestion=seg.get("slide_suggestion", ""),
                confidence_score=float(seg.get("confidence_score", 0.9)),
            )
        )
        cumulative_time = end_time

    total_duration = float(
        bundle.get("total_duration", cumulative_time)
    )

    return TranscriptInfo(
        title=title,
        total_duration=total_duration,
        segments=segments,
        accuracy_score=float(bundle.get("accuracy_score", 0.9)),
        created_at=datetime.now(),
        source_audio_path=bundle.get("source_audio_path", ""),
    )
