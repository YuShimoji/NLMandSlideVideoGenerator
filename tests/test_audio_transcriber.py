"""AudioTranscriber のユニットテスト + モック統合テスト (SP-051)

テスト構成:
  - バリデーション: ファイル形式、サイズ、存在チェック
  - プロンプト構築: 1段階 / 文字起こしのみ
  - JSON パース + ScriptInfo 変換
  - speaker_mapping 適用
  - 中間テキスト保存
  - Gemini API モック統合テスト
"""
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from notebook_lm.audio_transcriber import AudioTranscriber
from notebook_lm.gemini_integration import ScriptInfo


# --- Fixtures ---

@pytest.fixture
def transcriber():
    return AudioTranscriber(api_key="test-key-123", model_name="gemini-2.5-flash")


@pytest.fixture
def sample_audio(tmp_path: Path) -> Path:
    """ダミー音声ファイル (中身はバイト列)"""
    audio = tmp_path / "test_audio.mp3"
    audio.write_bytes(b"\xff\xfb\x90\x00" * 1000)  # 4KB の疑似MP3
    return audio


@pytest.fixture
def large_audio(tmp_path: Path) -> Path:
    """20MB超のダミー音声ファイル"""
    audio = tmp_path / "large_audio.mp3"
    audio.write_bytes(b"\xff\xfb\x90\x00" * (6 * 1024 * 1024))  # ~24MB
    return audio


@pytest.fixture
def sample_gemini_response() -> str:
    """Gemini API のモックレスポンス (JSON文字列)"""
    return json.dumps({
        "title": "AI技術の最新動向",
        "segments": [
            {
                "id": 1,
                "speaker": "Host1",
                "text": "こんにちは、今日はAI技術の最新動向について解説します。",
                "key_points": ["AI技術"],
                "duration_hint": 15
            },
            {
                "id": 2,
                "speaker": "Host2",
                "text": "まず、機械学習の基本概念から始めましょう。",
                "key_points": ["機械学習"],
                "duration_hint": 12
            },
            {
                "id": 3,
                "speaker": "Host1",
                "text": "機械学習とは、データから自動的にパターンを学習する技術です。",
                "key_points": ["パターン学習"],
                "duration_hint": 18
            },
            {
                "id": 4,
                "speaker": "Host2",
                "text": "特に深層学習は、近年大きな注目を集めています。",
                "key_points": ["深層学習"],
                "duration_hint": 10
            },
        ],
        "total_duration_estimate": 55
    }, ensure_ascii=False)


@pytest.fixture
def wrapped_gemini_response(sample_gemini_response: str) -> str:
    """```json ... ``` でラップされたレスポンス"""
    return f"```json\n{sample_gemini_response}\n```"


# --- Validation Tests ---

class TestValidation:

    def test_supported_formats(self, transcriber: AudioTranscriber, tmp_path: Path):
        for ext in [".mp3", ".wav", ".aac", ".ogg", ".flac", ".m4a", ".webm"]:
            audio = tmp_path / f"test{ext}"
            audio.write_bytes(b"\x00" * 100)
            transcriber._validate_audio(audio)  # should not raise

    def test_unsupported_format(self, transcriber: AudioTranscriber, tmp_path: Path):
        audio = tmp_path / "test.txt"
        audio.write_bytes(b"not audio")
        with pytest.raises(ValueError, match="非対応の音声形式"):
            transcriber._validate_audio(audio)

    def test_file_not_found(self, transcriber: AudioTranscriber, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            transcriber._validate_audio(tmp_path / "nonexistent.mp3")

    def test_empty_file(self, transcriber: AudioTranscriber, tmp_path: Path):
        audio = tmp_path / "empty.mp3"
        audio.write_bytes(b"")
        with pytest.raises(ValueError, match="空です"):
            transcriber._validate_audio(audio)

    def test_oversized_file(self, transcriber: AudioTranscriber, tmp_path: Path):
        audio = tmp_path / "huge.mp3"
        # MAX_FILE_SIZE_MB + 1 MB
        audio.write_bytes(b"\x00" * ((transcriber.MAX_FILE_SIZE_MB + 1) * 1024 * 1024))
        with pytest.raises(ValueError, match="大きすぎます"):
            transcriber._validate_audio(audio)


# --- Prompt Construction Tests ---

class TestPromptConstruction:

    def test_structure_prompt_ja(self, transcriber: AudioTranscriber):
        prompt = transcriber._build_structure_prompt(
            topic="AI動向",
            target_duration=300,
            language="ja",
            style="default",
            speaker_mapping=None,
        )
        assert "日本語" in prompt
        assert "AI動向" in prompt
        assert "Host1" in prompt
        assert "Host2" in prompt
        assert "15-25" in prompt  # 5分のセグメントヒント

    def test_structure_prompt_en(self, transcriber: AudioTranscriber):
        prompt = transcriber._build_structure_prompt(
            topic="AI trends",
            target_duration=900,
            language="en",
            style="default",
            speaker_mapping=None,
        )
        assert "English" in prompt
        assert "30-50" in prompt  # 15分のセグメントヒント

    def test_structure_prompt_long_duration(self, transcriber: AudioTranscriber):
        prompt = transcriber._build_structure_prompt(
            topic="Deep dive",
            target_duration=3600,
            language="ja",
            style="default",
            speaker_mapping=None,
        )
        assert "90-150" in prompt  # 60分のセグメントヒント

    def test_structure_prompt_with_speaker_mapping(self, transcriber: AudioTranscriber):
        prompt = transcriber._build_structure_prompt(
            topic="test",
            target_duration=300,
            language="ja",
            style="default",
            speaker_mapping={"Host1": "ゆっくり霊夢", "Host2": "ゆっくり魔理沙"},
        )
        assert "ゆっくり霊夢" in prompt
        assert "ゆっくり魔理沙" in prompt

    def test_transcribe_only_prompt_ja(self, transcriber: AudioTranscriber):
        prompt = transcriber._build_transcribe_only_prompt("ja")
        assert "忠実に" in prompt
        assert "日本語" in prompt

    def test_transcribe_only_prompt_en(self, transcriber: AudioTranscriber):
        prompt = transcriber._build_transcribe_only_prompt("en")
        assert "English" in prompt


# --- Response Parsing Tests ---

class TestResponseParsing:

    def test_parse_valid_json(self, transcriber: AudioTranscriber, sample_gemini_response: str):
        result = transcriber._parse_response(sample_gemini_response, "AI動向", "ja")
        assert isinstance(result, ScriptInfo)
        assert result.title == "AI技術の最新動向"
        assert len(result.segments) == 4
        assert result.segments[0]["speaker"] == "Host1"
        assert result.total_duration_estimate == 55
        assert result.language == "ja"

    def test_parse_wrapped_json(self, transcriber: AudioTranscriber, wrapped_gemini_response: str):
        result = transcriber._parse_response(wrapped_gemini_response, "AI動向", "ja")
        assert len(result.segments) == 4

    def test_parse_invalid_json(self, transcriber: AudioTranscriber):
        with pytest.raises(ValueError, match="JSON パースに失敗"):
            transcriber._parse_response("This is not JSON", "test", "ja")

    def test_parse_empty_segments(self, transcriber: AudioTranscriber):
        json_str = json.dumps({"title": "Empty", "segments": [], "total_duration_estimate": 0})
        result = transcriber._parse_response(json_str, "test", "ja")
        assert len(result.segments) == 0

    def test_parse_missing_optional_fields(self, transcriber: AudioTranscriber):
        """セグメントにオプションフィールドがなくてもパースできる"""
        data = json.dumps({
            "title": "Test",
            "segments": [
                {"speaker": "Host1", "text": "Hello"},
                {"text": "World"},  # speaker 省略
            ],
        })
        result = transcriber._parse_response(data, "test", "ja")
        assert len(result.segments) == 2
        assert result.segments[0]["speaker"] == "Host1"
        assert result.segments[1]["speaker"] == "Host1"  # デフォルト
        assert result.total_duration_estimate == 30  # 15 * 2

    def test_parse_duration_from_hints(self, transcriber: AudioTranscriber):
        """total_duration_estimate が 0 の場合、duration_hint の合計を使う"""
        data = json.dumps({
            "title": "Test",
            "segments": [
                {"speaker": "Host1", "text": "A", "duration_hint": 20},
                {"speaker": "Host2", "text": "B", "duration_hint": 30},
            ],
            "total_duration_estimate": 0,
        })
        result = transcriber._parse_response(data, "test", "ja")
        assert result.total_duration_estimate == 50


# --- Speaker Mapping Tests ---

class TestSpeakerMapping:

    def test_apply_mapping(self, transcriber: AudioTranscriber, sample_gemini_response: str):
        script = transcriber._parse_response(sample_gemini_response, "test", "ja")
        mapping = {"Host1": "霊夢", "Host2": "魔理沙"}
        result = transcriber._apply_speaker_mapping(script, mapping)
        assert result.segments[0]["speaker"] == "霊夢"
        assert result.segments[1]["speaker"] == "魔理沙"

    def test_partial_mapping(self, transcriber: AudioTranscriber, sample_gemini_response: str):
        script = transcriber._parse_response(sample_gemini_response, "test", "ja")
        mapping = {"Host1": "霊夢"}  # Host2 はマッピングなし
        result = transcriber._apply_speaker_mapping(script, mapping)
        assert result.segments[0]["speaker"] == "霊夢"
        assert result.segments[1]["speaker"] == "Host2"  # 変更なし


# --- Save Intermediate Transcript Tests ---

class TestSaveTranscript:

    def test_save_creates_file(self, tmp_path: Path):
        save_path = tmp_path / "subdir" / "transcript.txt"
        AudioTranscriber._save_intermediate_transcript("Hello World", save_path)
        assert save_path.exists()
        assert save_path.read_text(encoding="utf-8") == "Hello World"


# --- MIME Type Tests ---

class TestMimeType:

    @pytest.mark.parametrize("ext,expected", [
        (".mp3", "audio/mpeg"),
        (".wav", "audio/wav"),
        (".aac", "audio/aac"),
        (".ogg", "audio/ogg"),
        (".flac", "audio/flac"),
        (".m4a", "audio/mp4"),
        (".webm", "audio/webm"),
    ])
    def test_mime_types(self, ext: str, expected: str):
        assert AudioTranscriber._get_mime_type(Path(f"test{ext}")) == expected

    def test_unknown_ext_defaults_to_mpeg(self):
        assert AudioTranscriber._get_mime_type(Path("test.xyz")) == "audio/mpeg"


# --- Mock Integration Tests ---

class TestGeminiIntegration:

    @pytest.mark.asyncio
    async def test_transcribe_and_structure_mock(
        self,
        transcriber: AudioTranscriber,
        sample_audio: Path,
        sample_gemini_response: str,
    ):
        """Gemini API をモックして transcribe_and_structure の全フローをテスト"""
        with patch.object(
            transcriber, "_call_gemini_audio",
            new_callable=AsyncMock,
            return_value=sample_gemini_response,
        ):
            result = await transcriber.transcribe_and_structure(
                audio_path=sample_audio,
                topic="AI技術の最新動向",
                target_duration=300,
                language="ja",
            )

        assert isinstance(result, ScriptInfo)
        assert len(result.segments) == 4
        assert result.title == "AI技術の最新動向"

    @pytest.mark.asyncio
    async def test_transcribe_and_structure_with_mapping(
        self,
        transcriber: AudioTranscriber,
        sample_audio: Path,
        sample_gemini_response: str,
    ):
        """speaker_mapping が適用されることを確認"""
        with patch.object(
            transcriber, "_call_gemini_audio",
            new_callable=AsyncMock,
            return_value=sample_gemini_response,
        ):
            result = await transcriber.transcribe_and_structure(
                audio_path=sample_audio,
                topic="test",
                speaker_mapping={"Host1": "霊夢", "Host2": "魔理沙"},
            )

        assert result.segments[0]["speaker"] == "霊夢"
        assert result.segments[1]["speaker"] == "魔理沙"

    @pytest.mark.asyncio
    async def test_transcribe_and_structure_save_transcript(
        self,
        transcriber: AudioTranscriber,
        sample_audio: Path,
        sample_gemini_response: str,
        tmp_path: Path,
    ):
        """save_transcript で中間テキストが保存されることを確認"""
        save_path = tmp_path / "transcript" / "transcript.txt"
        with patch.object(
            transcriber, "_call_gemini_audio",
            new_callable=AsyncMock,
            return_value=sample_gemini_response,
        ):
            await transcriber.transcribe_and_structure(
                audio_path=sample_audio,
                topic="test",
                save_transcript=save_path,
            )

        assert save_path.exists()
        saved = save_path.read_text(encoding="utf-8")
        assert "AI技術" in saved

    @pytest.mark.asyncio
    async def test_transcribe_only_mock(
        self,
        transcriber: AudioTranscriber,
        sample_audio: Path,
    ):
        """transcribe_only のモックテスト"""
        transcript = "Host1: こんにちは\n\nHost2: よろしくお願いします"
        with patch.object(
            transcriber, "_call_gemini_audio",
            new_callable=AsyncMock,
            return_value=transcript,
        ):
            result = await transcriber.transcribe_only(sample_audio, language="ja")

        assert "こんにちは" in result

    @pytest.mark.asyncio
    async def test_invalid_audio_path(self, transcriber: AudioTranscriber):
        """存在しないファイルでエラー"""
        with pytest.raises(FileNotFoundError):
            await transcriber.transcribe_and_structure(
                audio_path=Path("/nonexistent/audio.mp3"),
                topic="test",
            )

    @pytest.mark.asyncio
    async def test_wrong_format(self, transcriber: AudioTranscriber, tmp_path: Path):
        """非対応形式でエラー"""
        txt = tmp_path / "test.pdf"
        txt.write_bytes(b"%PDF-1.4")
        with pytest.raises(ValueError, match="非対応"):
            await transcriber.transcribe_and_structure(audio_path=txt, topic="test")


# --- Default Init Tests ---

class TestInit:

    def test_default_model(self):
        t = AudioTranscriber()
        assert t.model_name == "gemini-2.5-flash"

    def test_custom_model(self):
        t = AudioTranscriber(model_name="gemini-2.0-flash")
        assert t.model_name == "gemini-2.0-flash"

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "env-key-456")
        t = AudioTranscriber()
        assert t.api_key == "env-key-456"
