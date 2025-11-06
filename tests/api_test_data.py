"""
APIテスト用データ
"""
def get_test_sources():
    """Gemini APIテスト用のソースデータ"""
    return [
        {
            "title": "AI技術の進歩",
            "url": "https://example.com/ai-progress",
            "content_preview": "人工知能技術は急速に発展しています...",
            "relevance_score": 0.9,
            "reliability_score": 0.8,
            "source_type": "article"
        }
    ]


def get_test_slides_content():
    """Google Slides APIテスト用のスライド内容"""
    return [
        {
            "slide_id": 1,
            "title": "テストスライド",
            "content": "これはAPI連携テスト用のスライドです。",
            "layout": "title_slide",
            "duration": 10.0
        }
    ]


def get_test_text():
    """TTSテスト用のテキスト"""
    return "これは音声生成のテストです。"


def get_test_voice_config():
    """TTSテスト用の音声設定"""
    from audio.tts_integration import VoiceConfig
    return VoiceConfig(
        voice_id="default",
        language="ja",
        gender="female",
        age_range="adult",
        accent="japanese",
        quality="high"
    )
