"""30分動画 実践テスト

モック台本(90セグメント) → Orchestrator → CsvAssembler → timeline.csv
Gemini APIクォータに依存しない、Orchestrator+StockImageの統合検証。
"""
import json
import sys
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(dotenv_path=project_root / ".env")

from core.csv_assembler import CsvAssembler
from core.visual.resource_orchestrator import VisualResourceOrchestrator
from core.visual.segment_classifier import SegmentClassifier
from core.visual.stock_image_client import StockImageClient


def generate_mock_script(topic: str, segment_count: int = 90) -> list[dict]:
    """30分動画想定のモック台本を生成 (Gemini不要)。

    90セグメント x ~20秒 = 30分
    リアルな構成: 導入 → 背景 → 本論(データ+事例+解説) → 応用 → まとめ
    """
    sections = [
        # 導入 (5セグメント)
        ("Introduction", ["overview", "motivation"], True),
        ("Introduction", ["key question"], True),
        ("Background", ["historical context"], True),
        ("Background", ["timeline", "milestones"], True),
        ("Background", ["current state"], True),
    ]

    # 本論 (70セグメント: データ、解説、事例の混合)
    main_topics = [
        ("Core Concept 1", ["fundamental principle"], False),
        ("Data Analysis", ["statistics", "accuracy 95%"], False),
        ("Technical Detail", ["architecture", "layers"], False),
        ("Case Study 1", ["real-world application"], True),
        ("Comparison", ["model A vs model B", "benchmark"], False),
        ("Core Concept 2", ["advanced technique"], False),
        ("Data Analysis", ["performance metrics", "latency 50ms"], False),
        ("Step by Step", ["implementation guide"], False),
        ("Case Study 2", ["industry adoption"], True),
        ("Expert Opinion", ["research findings"], True),
        ("Technical Detail", ["optimization", "efficiency"], False),
        ("Data Analysis", ["cost comparison", "ROI 300%"], False),
        ("Visualization", ["diagram explanation"], False),
        ("Case Study 3", ["success story"], True),
    ]

    for i in range(70):
        idx = i % len(main_topics)
        sections.append(main_topics[idx])

    # 応用+まとめ (15セグメント)
    ending = [
        ("Applications", ["medical", "healthcare"], True),
        ("Applications", ["finance", "trading"], True),
        ("Applications", ["education", "learning"], True),
        ("Future Outlook", ["predictions", "2030"], True),
        ("Future Outlook", ["challenges ahead"], True),
        ("Ethical Considerations", ["AI ethics", "bias"], True),
        ("Ethical Considerations", ["regulation", "governance"], False),
        ("Practical Tips", ["getting started"], False),
        ("Practical Tips", ["best practices"], False),
        ("Practical Tips", ["common mistakes"], False),
        ("Resources", ["recommended reading"], False),
        ("Resources", ["tools and frameworks"], False),
        ("Summary", ["key takeaways"], True),
        ("Summary", ["final thoughts"], True),
        ("Conclusion", ["call to action"], True),
    ]
    sections.extend(ending)

    # セグメント数を調整
    sections = sections[:segment_count]

    segments = []
    speakers = ["Host1", "Host2"]
    for i, (section, kps, is_narrative) in enumerate(sections):
        speaker = speakers[i % 2]
        if is_narrative:
            content = f"{topic}の{section}について説明します。ここでは{', '.join(kps)}に焦点を当てます。"
        else:
            content = f"- 項目1: {kps[0]}\n- 項目2: 数値データ {i * 3.2:.1f}%\n- 比較: 前年比 +{i * 1.5:.0f}%"
        segments.append({
            "speaker": speaker,
            "content": content,
            "section": section,
            "key_points": [f"{topic} {kp}" for kp in kps],
        })

    return segments


def main():
    topic = "Artificial Intelligence in 2026"
    segment_count = 90

    print(f"=== 30分動画実践テスト ===")
    print(f"トピック: {topic}")
    print(f"セグメント数: {segment_count}")
    print()

    # --- Step 1: モック台本生成 ---
    print("--- Step 1: Mock Script Generation ---")
    segments = generate_mock_script(topic, segment_count)
    print(f"  Generated {len(segments)} segments")
    print(f"  Sections: {', '.join(sorted(set(s['section'] for s in segments)))}")
    print()

    # --- Step 2: SegmentClassifier ---
    print("--- Step 2: Segment Classification ---")
    classifier = SegmentClassifier(visual_ratio_target=0.35)
    types = classifier.classify(segments)

    from core.visual.models import SegmentType
    visual_count = sum(1 for t in types if t == SegmentType.VISUAL)
    textual_count = len(types) - visual_count
    print(f"  Visual: {visual_count} ({visual_count/len(types)*100:.0f}%)")
    print(f"  Textual: {textual_count} ({textual_count/len(types)*100:.0f}%)")

    # 分類分布を表示
    section_dist: dict[str, dict[str, int]] = {}
    for seg, t in zip(segments, types):
        sec = seg["section"]
        if sec not in section_dist:
            section_dist[sec] = {"visual": 0, "textual": 0}
        section_dist[sec][t.value] += 1

    print("\n  Section distribution:")
    for sec in sorted(section_dist.keys()):
        d = section_dist[sec]
        print(f"    {sec:25s} visual={d['visual']:2d} textual={d['textual']:2d}")
    print()

    # --- Step 3: Orchestrator ---
    print("--- Step 3: Visual Resource Orchestration ---")
    stock_client = StockImageClient()
    orchestrator = VisualResourceOrchestrator(
        classifier=classifier,
        stock_client=stock_client,
        topic=topic,
    )

    # スライドなしでテスト (ストック画像のみ + noneフォールバック)
    package = orchestrator.orchestrate(segments, [])

    stock_count = sum(1 for r in package.resources if r.source == "stock")
    slide_count = sum(1 for r in package.resources if r.source == "slide")
    none_count = sum(1 for r in package.resources if r.source == "none")

    print(f"  Stock images: {stock_count}")
    print(f"  Slides: {slide_count}")
    print(f"  None (fallback): {none_count}")
    print()

    # アニメーション分布
    anim_dist: dict[str, int] = {}
    for r in package.resources:
        a = r.animation_type.value
        anim_dist[a] = anim_dist.get(a, 0) + 1
    print("  Animation distribution:")
    for anim, count in sorted(anim_dist.items()):
        print(f"    {anim:12s} {count:3d}")
    print()

    # 連続同一ソース確認
    max_stock_run = 0
    max_none_run = 0
    cur_stock = 0
    cur_none = 0
    for r in package.resources:
        if r.source == "stock":
            cur_stock += 1
            max_stock_run = max(max_stock_run, cur_stock)
            cur_none = 0
        elif r.source == "none":
            cur_none += 1
            max_none_run = max(max_none_run, cur_none)
            cur_stock = 0
        else:
            cur_stock = 0
            cur_none = 0

    print(f"  Max consecutive stock: {max_stock_run} (limit: {orchestrator.MAX_CONSECUTIVE_STOCK})")
    print(f"  Max consecutive none: {max_none_run}")
    print()

    # --- Step 4: CSV生成 ---
    print("--- Step 4: CSV Generation ---")
    output_dir = project_root / "data" / "test_30min"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "timeline.csv"

    assembler = CsvAssembler()
    assembler.assemble_from_package(
        script_segments=segments,
        package=package,
        output_path=csv_path,
        speaker_mapping={"Host1": "reimu", "Host2": "marisa"},
    )

    csv_lines = csv_path.read_text(encoding="utf-8").strip().split("\n")
    print(f"  CSV: {csv_path}")
    print(f"  Rows: {len(csv_lines)}")

    # 画像パス付きの行数
    lines_with_images = sum(1 for line in csv_lines if "stock_images" in line or "slide" in line)
    print(f"  Rows with images: {lines_with_images}")
    print()

    # サンプル出力
    print("--- Sample CSV rows ---")
    for line in csv_lines[:5]:
        print(f"  {line[:120]}")
    print(f"  ... ({len(csv_lines) - 5} more rows)")
    print()

    # --- 台本+クレジットも保存 ---
    script_path = output_dir / "mock_script.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump({"topic": topic, "segments": segments}, f, ensure_ascii=False, indent=2)
    print(f"  Script saved: {script_path}")

    # クレジット
    stock_resources = [r for r in package.resources if r.source == "stock" and r.image_path]
    if stock_resources:
        unique_paths = set(str(r.image_path) for r in stock_resources)
        print(f"  Unique stock images used: {len(unique_paths)}")

    print()
    print("=== 30分動画テスト完了 ===")
    print(f"  Output dir: {output_dir}")
    print(f"  Total segments: {len(segments)}")
    print(f"  Stock images fetched: {stock_count}")
    print(f"  Visual variety score: {stock_count / len(segments) * 100:.0f}% segments with stock photos")


if __name__ == "__main__":
    main()
