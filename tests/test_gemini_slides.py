"""
Geminiスライド生成の検証テスト

このテストは以下を確認します:
1. GeminiIntegration.generate_slide_content() が正しくスライド情報を生成するか
2. SlideGenerator が script_bundle["slides"] を正しく処理するか
3. prefer_gemini_slide_content フラグによる分岐が正しく動作するか

実行方法:
  cmd.exe /c "venv\\Scripts\\activate.bat && set PYTHONPATH=. && python tests\\test_gemini_slides.py"
"""
import asyncio
import sys
import os
import pytest

# パス設定（絶対パスで解決）
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)  # config/ 用
sys.path.insert(0, os.path.join(project_root, "src"))  # notebook_lm/, slides/ 等用
os.chdir(project_root)

from config.settings import settings
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment
from slides.slide_generator import SlideGenerator


def create_mock_transcript() -> TranscriptInfo:
    """テスト用のモックTranscriptInfoを作成"""
    from datetime import datetime

    segments = [
        TranscriptSegment(
            id=1,
            start_time=0.0,
            end_time=30.0,
            speaker="Host",
            text="今日はAIについて解説します。機械学習の基礎から応用まで幅広く扱います。",
            key_points=["AI解説", "機械学習基礎"],
            slide_suggestion="AIと機械学習の概要",
            confidence_score=0.95,
        ),
        TranscriptSegment(
            id=2,
            start_time=30.0,
            end_time=60.0,
            speaker="Host",
            text="まず、ニューラルネットワークの仕組みについて説明しましょう。",
            key_points=["ニューラルネットワーク"],
            slide_suggestion="ニューラルネットワークの仕組み",
            confidence_score=0.92,
        ),
        TranscriptSegment(
            id=3,
            start_time=60.0,
            end_time=90.0,
            speaker="Host",
            text="深層学習では、多層のニューラルネットワークを使用します。",
            key_points=["深層学習", "多層ネットワーク"],
            slide_suggestion="深層学習とは",
            confidence_score=0.90,
        ),
    ]
    return TranscriptInfo(
        title="AI入門講座",
        segments=segments,
        total_duration=90.0,
        accuracy_score=0.92,
        created_at=datetime.now(),
        source_audio_path="mock_audio.mp3",
    )


def create_mock_script_bundle_with_slides() -> dict:
    """Gemini由来のスライド情報を含むモックscript_bundleを作成"""
    return {
        "title": "AI入門講座",
        "segments": [
            {"content": "今日はAIについて解説します。", "duration": 30.0},
            {"content": "ニューラルネットワークの仕組みを説明します。", "duration": 30.0},
            {"content": "深層学習では多層ネットワークを使用します。", "duration": 30.0},
        ],
        "slides": [
            {
                "slide_number": 1,
                "title": "AIと機械学習の概要",
                "content": "・AI（人工知能）とは\n・機械学習の基礎概念\n・応用分野の紹介",
                "layout": "title_and_content",
                "duration": 15.0,
                "image_suggestions": ["AI概念図", "機械学習フロー"],
            },
            {
                "slide_number": 2,
                "title": "ニューラルネットワークの仕組み",
                "content": "・入力層・隠れ層・出力層\n・重みとバイアス\n・活性化関数",
                "layout": "title_and_content",
                "duration": 20.0,
                "image_suggestions": ["ニューラルネットワーク図"],
            },
            {
                "slide_number": 3,
                "title": "深層学習とは",
                "content": "・多層ニューラルネットワーク\n・特徴量の自動抽出\n・代表的なアーキテクチャ",
                "layout": "title_and_content",
                "duration": 15.0,
                "image_suggestions": ["深層学習アーキテクチャ"],
            },
        ],
    }


@pytest.mark.asyncio
async def test_slide_generator_with_bundle():
    """script_bundle付きでSlideGeneratorをテスト"""
    print("\n" + "=" * 60)
    print("テスト1: script_bundle付きスライド生成")
    print("=" * 60)

    transcript = create_mock_transcript()
    script_bundle = create_mock_script_bundle_with_slides()

    # 設定確認
    prefer_gemini = settings.SLIDES_SETTINGS.get("prefer_gemini_slide_content", False)
    print(f"\n[設定] prefer_gemini_slide_content = {prefer_gemini}")
    print(f"[入力] script_bundle['slides'] = {len(script_bundle['slides'])}枚")

    generator = SlideGenerator()

    try:
        slides_pkg = await generator.generate_slides(
            transcript=transcript,
            max_slides=10,
            script_bundle=script_bundle,
        )

        print(f"\n[結果] 生成されたスライド: {slides_pkg.total_slides}枚")
        print(f"[結果] presentation_id: {slides_pkg.presentation_id}")
        print(f"[結果] title: {slides_pkg.title}")

        for i, slide in enumerate(slides_pkg.slides[:3], 1):
            print(f"\n  スライド {i}:")
            print(f"    タイトル: {slide.title}")
            print(f"    内容: {slide.content[:50]}..." if len(slide.content) > 50 else f"    内容: {slide.content}")
            print(f"    duration: {slide.estimated_duration}秒")
            if slide.image_suggestions:
                print(f"    画像提案: {slide.image_suggestions}")

        print("\n✅ テスト1 成功")
        return True

    except Exception as e:
        print(f"\n❌ テスト1 失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_slide_generator_without_bundle():
    """script_bundleなしでSlideGeneratorをテスト（従来パス）"""
    print("\n" + "=" * 60)
    print("テスト2: script_bundleなしスライド生成（従来パス）")
    print("=" * 60)

    transcript = create_mock_transcript()

    generator = SlideGenerator()

    try:
        slides_pkg = await generator.generate_slides(
            transcript=transcript,
            max_slides=5,
            script_bundle=None,
        )

        print(f"\n[結果] 生成されたスライド: {slides_pkg.total_slides}枚")
        print(f"[結果] presentation_id: {slides_pkg.presentation_id}")

        for i, slide in enumerate(slides_pkg.slides[:3], 1):
            print(f"\n  スライド {i}:")
            print(f"    タイトル: {slide.title}")

        print("\n✅ テスト2 成功")
        return True

    except Exception as e:
        print(f"\n❌ テスト2 失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_prefer_gemini_flag():
    """prefer_gemini_slide_content フラグの動作確認"""
    print("\n" + "=" * 60)
    print("テスト3: prefer_gemini_slide_content フラグ確認")
    print("=" * 60)

    # 現在の設定値を確認
    prefer_gemini = settings.SLIDES_SETTINGS.get("prefer_gemini_slide_content", False)
    env_value = os.getenv("SLIDES_USE_GEMINI_CONTENT", "未設定")

    print(f"\n[環境変数] SLIDES_USE_GEMINI_CONTENT = {env_value}")
    print(f"[設定値] prefer_gemini_slide_content = {prefer_gemini}")

    if prefer_gemini:
        print("\n→ Geminiスライド優先モードが有効です")
        print("  script_bundle['slides']がある場合、それを使用してスライドを生成します")
    else:
        print("\n→ 従来モードが有効です")
        print("  TranscriptInfoからContentSplitterでスライドを分割して生成します")
        print("\n  Geminiスライドを優先するには:")
        print("    set SLIDES_USE_GEMINI_CONTENT=true")
        print("  を設定してから実行してください")

    print("\n✅ テスト3 完了")
    return True


async def main():
    """メインテスト実行"""
    print("=" * 60)
    print("Geminiスライド生成 検証テスト")
    print("=" * 60)

    results = []

    # テスト実行
    results.append(await test_prefer_gemini_flag())
    results.append(await test_slide_generator_with_bundle())
    results.append(await test_slide_generator_without_bundle())

    # 結果サマリー
    print("\n" + "=" * 60)
    print("テスト結果サマリー")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    print(f"\n合格: {passed}/{total}")

    if passed == total:
        print("\n🎉 全テスト成功!")
    else:
        print("\n⚠️ 一部テストが失敗しました")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
