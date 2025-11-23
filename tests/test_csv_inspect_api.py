#!/usr/bin/env python3
"""/api/v1/csv/inspect エンドポイントの簡易テスト

実ファイルを使って、CSV + 行ごとWAVに対してタイムライン可視化APIが最低限動くことを確認する。
外部サービスには依存せず、ローカルファイルのみを利用する。
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from src.server.api import app  # noqa: E402


def _create_silent_wav(path: Path, duration_sec: float = 1.0, sample_rate: int = 44100) -> None:
    import wave
    import struct

    n_channels = 1
    sampwidth = 2  # 16-bit
    n_frames = int(sample_rate * duration_sec)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(sampwidth)
        wf.setframerate(sample_rate)
        silence_frame = struct.pack("<h", 0)
        wf.writeframes(silence_frame * n_frames)


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_csv_inspect_basic(client: TestClient, tmp_path: Path) -> None:
    # 1) CSV 作成 (2行)
    csv_path = tmp_path / "timeline.csv"
    csv_content = "Speaker1,こんにちは世界\nSpeaker2,テストです\n"
    csv_path.write_text(csv_content, encoding="utf-8")

    # 2) 行ごとの音声ファイル (2本の無音WAV)
    audio_dir = tmp_path / "audio"
    _create_silent_wav(audio_dir / "001.wav", duration_sec=1.0)
    _create_silent_wav(audio_dir / "002.wav", duration_sec=2.0)

    payload = {
        "csv_path": str(csv_path),
        "audio_dir": str(audio_dir),
        "slides_max_chars_per_slide": 20,
        "max_slides": 10,
    }

    resp = client.post("/api/v1/csv/inspect", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "transcript" in data
    assert "slides" in data
    assert "stats" in data

    # Transcript が2セグメントで、stats にも反映されていること
    transcript = data["transcript"]
    assert transcript is not None
    assert len(transcript.get("segments", [])) == 2

    stats = data["stats"]
    assert stats.get("num_segments") == 2
    assert stats.get("num_slides") == len(data["slides"])
    assert stats.get("max_chars_per_slide") == 20
