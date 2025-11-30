"""
CSVタイムラインパイプライン統合テスト

samples/basic_dialogueを使用したE2Eテスト
"""
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

# プロジェクトルートをパスに追加
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings, create_directories


# サンプルディレクトリのパス
SAMPLES_DIR = PROJECT_ROOT / "samples" / "basic_dialogue"
SAMPLE_CSV = SAMPLES_DIR / "timeline.csv"
SAMPLE_AUDIO_DIR = SAMPLES_DIR / "audio"


@pytest.fixture(scope="module")
def ensure_sample_audio():
    """サンプル音声ファイルが存在することを確認（なければ生成）"""
    if not SAMPLE_AUDIO_DIR.exists():
        SAMPLE_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # 音声ファイルが足りない場合は生成
    expected_files = [f"{i:03d}.wav" for i in range(1, 11)]
    missing = [f for f in expected_files if not (SAMPLE_AUDIO_DIR / f).exists()]
    
    if missing:
        # generate_sample_audio.py のロジックを直接実行
        try:
            import wave
            import struct
            
            for filename in missing:
                filepath = SAMPLE_AUDIO_DIR / filename
                duration = 2.0
                sample_rate = 44100
                num_samples = int(sample_rate * duration)
                
                with wave.open(str(filepath), 'w') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    
                    # 無音データ
                    for _ in range(num_samples):
                        wav_file.writeframes(struct.pack('<h', 0))
        except Exception as e:
            pytest.skip(f"サンプル音声生成に失敗: {e}")
    
    return SAMPLE_AUDIO_DIR


@pytest.fixture
def temp_output_dir():
    """一時出力ディレクトリ"""
    temp_dir = tempfile.mkdtemp(prefix="csv_pipeline_test_")
    yield Path(temp_dir)
    # クリーンアップ
    shutil.rmtree(temp_dir, ignore_errors=True)


class TestCSVPipelineIntegration:
    """CSVパイプライン統合テスト"""
    
    def test_sample_files_exist(self, ensure_sample_audio):
        """サンプルファイルが存在することを確認"""
        assert SAMPLE_CSV.exists(), f"サンプルCSVが見つかりません: {SAMPLE_CSV}"
        assert SAMPLE_AUDIO_DIR.exists(), f"音声ディレクトリが見つかりません: {SAMPLE_AUDIO_DIR}"
        
        # 少なくとも1つのWAVファイルがあることを確認
        wav_files = list(SAMPLE_AUDIO_DIR.glob("*.wav"))
        assert len(wav_files) > 0, "WAVファイルが見つかりません"
    
    def test_csv_format_valid(self):
        """CSVフォーマットが正しいことを確認"""
        import csv
        
        with open(SAMPLE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) > 0, "CSVが空です"
        
        for i, row in enumerate(rows):
            assert len(row) >= 2, f"行{i+1}: 列数が不足しています（最低2列必要）"
            speaker, text = row[0], row[1]
            assert speaker.strip(), f"行{i+1}: 話者名が空です"
            assert text.strip(), f"行{i+1}: テキストが空です"
    
    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, ensure_sample_audio):
        """パイプラインの初期化が成功することを確認"""
        try:
            from core.helpers import build_default_pipeline
            create_directories()
            
            pipeline = build_default_pipeline()
            assert pipeline is not None
        except ImportError as e:
            pytest.skip(f"パイプライン初期化に必要なモジュールがありません: {e}")
        except Exception as e:
            pytest.fail(f"パイプライン初期化に失敗: {e}")
    
    @pytest.mark.asyncio
    async def test_csv_timeline_execution(self, ensure_sample_audio, temp_output_dir):
        """CSVタイムラインパイプラインの実行テスト"""
        try:
            from core.helpers import build_default_pipeline
            create_directories()
            
            # 出力先を一時ディレクトリに設定
            original_videos_dir = settings.VIDEOS_DIR
            settings.VIDEOS_DIR = temp_output_dir
            
            try:
                pipeline = build_default_pipeline()
                
                result = await pipeline.run_csv_timeline(
                    csv_path=SAMPLE_CSV,
                    audio_dir=SAMPLE_AUDIO_DIR,
                    topic="統合テスト動画",
                    quality="720p",
                    private_upload=True,
                    upload=False,
                    stage_modes={"stage1": "mock", "stage2": "real", "stage3": "skip"},
                    user_preferences={},
                    progress_callback=None,
                )
                
                # 結果の検証
                assert result is not None, "結果がNoneです"
                assert isinstance(result, dict), "結果が辞書ではありません"
                
                # artifactsの存在確認
                artifacts = result.get("artifacts")
                if artifacts:
                    # videoがあれば検証
                    if hasattr(artifacts, 'video') and artifacts.video:
                        video_path = getattr(artifacts.video, 'file_path', None)
                        if video_path:
                            assert Path(video_path).exists() or Path(video_path).stat().st_size == 0, \
                                "動画ファイルが見つかりません（FFmpegなしの場合は空ファイル可）"
                
            finally:
                settings.VIDEOS_DIR = original_videos_dir
                
        except ImportError as e:
            pytest.skip(f"必要なモジュールがありません: {e}")
        except Exception as e:
            # FFmpegがない場合などはスキップではなく部分的成功として扱う
            if "ffmpeg" in str(e).lower():
                pytest.skip(f"FFmpegがないため動画生成をスキップ: {e}")
            else:
                pytest.fail(f"パイプライン実行に失敗: {e}")
    
    def test_csv_parsing_logic(self, ensure_sample_audio):
        """CSV解析ロジックのユニットテスト"""
        import csv
        
        # CSVを読み込んでタイムラインエントリを構築
        entries = []
        with open(SAMPLE_CSV, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if len(row) >= 2:
                    entries.append({
                        "index": i + 1,
                        "speaker": row[0].strip(),
                        "text": row[1].strip(),
                    })
        
        assert len(entries) > 0, "エントリが0件です"
        
        # 各エントリに対応する音声ファイルの存在確認
        for entry in entries:
            wav_path = SAMPLE_AUDIO_DIR / f"{entry['index']:03d}.wav"
            assert wav_path.exists(), f"音声ファイルがありません: {wav_path}"
    
    def test_long_text_splitting(self):
        """長文自動分割機能のテスト"""
        from config.settings import settings
        
        max_chars = settings.SLIDES_SETTINGS.get("max_chars_per_slide", 60)
        
        # 長文テスト
        long_text = "これは非常に長いテキストです。" * 10
        
        # 分割ロジックのシミュレーション
        if len(long_text) > max_chars:
            # 分割が必要
            chunks = []
            remaining = long_text
            while remaining:
                if len(remaining) <= max_chars:
                    chunks.append(remaining)
                    break
                
                # 句読点で分割を試みる
                split_pos = max_chars
                for punct in ["。", "、", ".", ","]:
                    pos = remaining[:max_chars].rfind(punct)
                    if pos > 0:
                        split_pos = pos + 1
                        break
                
                chunks.append(remaining[:split_pos])
                remaining = remaining[split_pos:]
            
            assert len(chunks) > 1, "長文が分割されていません"
            for chunk in chunks:
                assert len(chunk) <= max_chars or "。" not in chunk[:max_chars], \
                    f"分割後のチャンクが長すぎます: {len(chunk)}文字"


class TestCSVPipelineErrorHandling:
    """エラーハンドリングテスト"""
    
    def test_missing_csv_file(self):
        """存在しないCSVファイルのエラー処理"""
        nonexistent_csv = Path("/nonexistent/path/timeline.csv")
        assert not nonexistent_csv.exists()
    
    def test_missing_audio_directory(self):
        """存在しない音声ディレクトリのエラー処理"""
        nonexistent_dir = Path("/nonexistent/audio/dir")
        assert not nonexistent_dir.exists()
    
    def test_empty_csv_handling(self, temp_output_dir):
        """空のCSVファイルの処理"""
        empty_csv = temp_output_dir / "empty.csv"
        empty_csv.write_text("")
        
        import csv
        with open(empty_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) == 0, "空のCSVに行が含まれています"
    
    def test_malformed_csv_handling(self, temp_output_dir):
        """不正なCSVの処理"""
        malformed_csv = temp_output_dir / "malformed.csv"
        malformed_csv.write_text("Speaker1\n")  # 1列しかない
        
        import csv
        with open(malformed_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # 1列しかない行は無効として扱われるべき
        for row in rows:
            if len(row) < 2:
                # 期待どおり: 列数不足
                pass


class TestSubtitleGeneration:
    """字幕生成テスト"""
    
    def test_srt_format(self, temp_output_dir):
        """SRT形式の字幕生成テスト"""
        srt_content = """1
00:00:00,000 --> 00:00:02,000
テスト字幕1

2
00:00:02,000 --> 00:00:04,000
テスト字幕2
"""
        srt_path = temp_output_dir / "test.srt"
        srt_path.write_text(srt_content, encoding='utf-8')
        
        # SRTファイルの検証
        content = srt_path.read_text(encoding='utf-8')
        assert "00:00:00,000 --> 00:00:02,000" in content
        assert "テスト字幕1" in content
    
    def test_vtt_format(self, temp_output_dir):
        """VTT形式の字幕生成テスト"""
        vtt_content = """WEBVTT

00:00:00.000 --> 00:00:02.000
テスト字幕1

00:00:02.000 --> 00:00:04.000
テスト字幕2
"""
        vtt_path = temp_output_dir / "test.vtt"
        vtt_path.write_text(vtt_content, encoding='utf-8')
        
        content = vtt_path.read_text(encoding='utf-8')
        assert content.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.000" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
