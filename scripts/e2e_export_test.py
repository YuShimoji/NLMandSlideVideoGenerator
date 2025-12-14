#!/usr/bin/env python3
"""
E2E動画書き出し検証スクリプト

ExportFallbackManagerを使用して、実際の動画書き出しを検証する。
MoviePyバックエンドでの基本的な動画生成が動作することを確認。
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_PATH = PROJECT_ROOT / "src"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from config.settings import settings, create_directories
from core.editing import ExportFallbackManager, BackendType, BackendConfig
from core.utils.logger import logger
from notebook_lm.audio_generator import AudioInfo
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment
from slides.slide_generator import SlidesPackage


def create_test_audio(audio_path: Path = None) -> AudioInfo:
    """テスト用音声情報を作成"""
    return AudioInfo(
        file_path=audio_path or Path("mock_audio.wav"),
        duration=10.0,
        language="ja",
        sample_rate=44100,
        file_size=100000,
    )


def create_test_transcript() -> TranscriptInfo:
    """テスト用台本情報を作成"""
    segments = [
        TranscriptSegment(
            id=1,
            start_time=0.0,
            end_time=5.0,
            speaker="Speaker1",
            text="これはテストセグメント1です",
            key_points=["テスト"],
            slide_suggestion="スライド1",
            confidence_score=0.95,
        ),
        TranscriptSegment(
            id=2,
            start_time=5.0,
            end_time=10.0,
            speaker="Speaker1",
            text="これはテストセグメント2です",
            key_points=["テスト"],
            slide_suggestion="スライド2",
            confidence_score=0.95,
        ),
    ]
    return TranscriptInfo(
        title="E2Eテスト動画",
        total_duration=10.0,
        segments=segments,
        accuracy_score=0.95,
        created_at=datetime.now(),
        source_audio_path="mock_audio.wav",
    )


def create_test_slides() -> SlidesPackage:
    """テスト用スライド情報を作成"""
    return SlidesPackage(
        presentation_id="e2e_test",
        slides=[],
        total_slides=2,
    )


async def run_e2e_test(use_real_audio: bool = False) -> dict:
    """
    E2E動画書き出しテストを実行
    
    Args:
        use_real_audio: 実際のWAVファイルを使用するか（Falseの場合はモック）
        
    Returns:
        テスト結果の辞書
    """
    logger.info("=" * 60)
    logger.info("E2E動画書き出し検証開始")
    logger.info("=" * 60)
    
    create_directories()
    
    results = {
        "success": False,
        "backend_used": None,
        "output_path": None,
        "errors": [],
        "duration_seconds": 0,
    }
    
    start_time = datetime.now()
    
    # MoviePyのみ有効化（確実に動作するバックエンド）
    configs = [
        BackendConfig(
            backend_type=BackendType.MOVIEPY,
            enabled=True,
            priority=1,
            timeout_seconds=120.0,
        ),
    ]
    
    manager = ExportFallbackManager(configs=configs, auto_detect=False)
    
    logger.info(f"利用可能バックエンド: {manager.get_available_backends()}")
    
    # テスト用データ準備
    if use_real_audio:
        # 実際のWAVファイルを探す
        audio_candidates = list((PROJECT_ROOT / "data" / "audio").glob("*.wav"))
        if audio_candidates:
            audio_path = audio_candidates[0]
            logger.info(f"実際の音声ファイルを使用: {audio_path}")
        else:
            logger.warning("WAVファイルが見つかりません。モックを使用します。")
            audio_path = None
    else:
        audio_path = None
    
    test_audio = create_test_audio(audio_path)
    test_transcript = create_test_transcript()
    test_slides = create_test_slides()
    
    timeline_plan = {
        "total_duration": 10.0,
        "segments": [
            {
                "segment_id": "seg_1",
                "start": 0.0,
                "end": 5.0,
                "text": "セグメント1",
                "slide_index": 0,
            },
            {
                "segment_id": "seg_2", 
                "start": 5.0,
                "end": 10.0,
                "text": "セグメント2",
                "slide_index": 1,
            },
        ],
        "notes": "E2Eテスト用タイムライン",
    }
    
    logger.info("レンダリング開始...")
    
    try:
        result = await manager.render(
            timeline_plan=timeline_plan,
            audio=test_audio,
            slides=test_slides,
            transcript=test_transcript,
            quality="720p",  # テスト用に低解像度
        )
        
        end_time = datetime.now()
        results["duration_seconds"] = (end_time - start_time).total_seconds()
        
        if result.success:
            results["success"] = True
            results["backend_used"] = result.used_backend.value if result.used_backend else None
            results["output_path"] = str(result.video_info.file_path) if result.video_info else None
            
            logger.info("=" * 60)
            logger.info("E2E検証成功!")
            logger.info(f"使用バックエンド: {results['backend_used']}")
            logger.info(f"出力パス: {results['output_path']}")
            logger.info(f"所要時間: {results['duration_seconds']:.2f}秒")
            logger.info("=" * 60)
        else:
            results["errors"] = [f"{k.value}: {v}" for k, v in result.errors.items()]
            
            logger.error("=" * 60)
            logger.error("E2E検証失敗")
            logger.error(f"試行バックエンド: {[b.value for b in result.attempted_backends]}")
            logger.error(f"エラー: {results['errors']}")
            logger.error("=" * 60)
            
    except asyncio.CancelledError:
        raise
    except (FileNotFoundError, OSError, ValueError, TypeError, RuntimeError) as e:
        results["errors"].append(str(e))
        logger.exception(f"E2Eテスト中に例外発生: {e}")
    except Exception as e:
        results["errors"].append(str(e))
        logger.exception(f"E2Eテスト中に例外発生: {e}")
    
    return results


async def run_backend_availability_check() -> dict:
    """
    各バックエンドの利用可能性をチェック
    """
    logger.info("バックエンド利用可能性チェック...")
    
    manager = ExportFallbackManager(auto_detect=True)
    status = manager.get_status()
    
    logger.info("バックエンド状態:")
    for backend in status["backends"]:
        enabled_str = "✅" if backend["enabled"] else "❌"
        logger.info(f"  {enabled_str} {backend['type']} (優先度: {backend['priority']})")
    
    return status


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description="E2E動画書き出し検証")
    parser.add_argument("--real-audio", action="store_true", help="実際のWAVファイルを使用")
    parser.add_argument("--check-only", action="store_true", help="バックエンド確認のみ")
    
    args = parser.parse_args()
    
    if args.check_only:
        result = asyncio.run(run_backend_availability_check())
        print(f"\n利用可能バックエンド: {result['available']}")
    else:
        result = asyncio.run(run_e2e_test(use_real_audio=args.real_audio))
        
        print("\n" + "=" * 40)
        print("E2E検証結果サマリー")
        print("=" * 40)
        print(f"成功: {result['success']}")
        print(f"バックエンド: {result['backend_used']}")
        print(f"出力: {result['output_path']}")
        print(f"所要時間: {result['duration_seconds']:.2f}秒")
        if result['errors']:
            print(f"エラー: {result['errors']}")
        
        return 0 if result['success'] else 1


if __name__ == "__main__":
    sys.exit(main())
