"""AnimationAssigner テスト (SP-033)"""
import pytest
from pathlib import Path

from src.core.visual.models import AnimationType, VisualResource, VisualResourcePackage
from src.core.visual.animation_assigner import AnimationAssigner


class TestAnimationType:
    def test_from_str_valid(self):
        assert AnimationType.from_str("ken_burns") == AnimationType.KEN_BURNS
        assert AnimationType.from_str("zoom_in") == AnimationType.ZOOM_IN
        assert AnimationType.from_str("pan_left") == AnimationType.PAN_LEFT
        assert AnimationType.from_str("static") == AnimationType.STATIC

    def test_from_str_case_insensitive(self):
        assert AnimationType.from_str("KEN_BURNS") == AnimationType.KEN_BURNS
        assert AnimationType.from_str("Zoom_In") == AnimationType.ZOOM_IN

    def test_from_str_unknown_falls_back(self):
        assert AnimationType.from_str("unknown") == AnimationType.KEN_BURNS
        assert AnimationType.from_str("") == AnimationType.KEN_BURNS

    def test_from_str_whitespace_trimmed(self):
        assert AnimationType.from_str("  pan_right  ") == AnimationType.PAN_RIGHT

    def test_cycle_types_excludes_static(self):
        cycle = AnimationType.cycle_types()
        assert AnimationType.STATIC not in cycle
        assert len(cycle) == 6


class TestAnimationAssigner:
    def test_empty_segments(self):
        assigner = AnimationAssigner()
        package = assigner.assign(0)
        assert len(package.resources) == 0

    def test_all_none_images_get_static(self):
        assigner = AnimationAssigner()
        package = assigner.assign(3, [None, None, None])
        for r in package.resources:
            assert r.animation_type == AnimationType.STATIC
            assert r.source == "none"

    def test_text_slides_default_all_static(self):
        """デフォルト (text_slides=True) では全画像が STATIC になる。"""
        assigner = AnimationAssigner()
        paths = [Path(f"slide_{i}.png") for i in range(3)]
        package = assigner.assign(3, paths)

        for r in package.resources:
            assert r.animation_type == AnimationType.STATIC
            assert r.image_path is not None
            assert r.source == "slide"

    def test_with_images_cycles_animations(self):
        assigner = AnimationAssigner(text_slides=False)
        paths = [Path(f"slide_{i}.png") for i in range(6)]
        package = assigner.assign(6, paths)

        # 6つのリソースが生成される
        assert len(package.resources) == 6

        # 全てに画像パスが設定される
        for r in package.resources:
            assert r.image_path is not None
            assert r.source == "slide"

        # サイクル順で割当される
        expected_cycle = AnimationType.cycle_types()
        for i, r in enumerate(package.resources):
            assert r.animation_type == expected_cycle[i]

    def test_no_consecutive_duplicates(self):
        """同一アニメーションが2回連続しないことを確認。"""
        assigner = AnimationAssigner(text_slides=False)
        # 7セグメント（サイクル長6 + 1）でも連続しない
        paths = [Path(f"slide_{i}.png") for i in range(7)]
        package = assigner.assign(7, paths)

        for i in range(1, len(package.resources)):
            prev = package.resources[i - 1].animation_type
            curr = package.resources[i].animation_type
            # STATICが挟まる場合は例外
            if prev != AnimationType.STATIC and curr != AnimationType.STATIC:
                assert prev != curr, f"Consecutive duplicate at index {i}: {curr}"

    def test_mixed_images_and_none(self):
        assigner = AnimationAssigner(text_slides=False)
        paths = [Path("slide_0.png"), None, Path("slide_1.png"), None]
        package = assigner.assign(4, paths)

        assert package.resources[0].animation_type != AnimationType.STATIC
        assert package.resources[1].animation_type == AnimationType.STATIC
        assert package.resources[2].animation_type != AnimationType.STATIC
        assert package.resources[3].animation_type == AnimationType.STATIC

    def test_single_image(self):
        assigner = AnimationAssigner(text_slides=False)
        package = assigner.assign(1, [Path("slide.png")])
        assert len(package.resources) == 1
        assert package.resources[0].animation_type == AnimationType.KEN_BURNS

    def test_image_paths_shorter_than_segments(self):
        """image_pathsがsegment_countより短い場合、Noneで埋められる。"""
        assigner = AnimationAssigner(text_slides=False)
        package = assigner.assign(5, [Path("a.png"), Path("b.png")])
        assert len(package.resources) == 5
        # 最初の2つは画像あり
        assert package.resources[0].image_path is not None
        assert package.resources[1].image_path is not None
        # 残り3つはSTATIC
        for r in package.resources[2:]:
            assert r.animation_type == AnimationType.STATIC

    def test_custom_cycle(self):
        custom = [AnimationType.ZOOM_IN, AnimationType.ZOOM_OUT]
        assigner = AnimationAssigner(cycle=custom, text_slides=False)
        paths = [Path(f"s{i}.png") for i in range(4)]
        package = assigner.assign(4, paths)

        assert package.resources[0].animation_type == AnimationType.ZOOM_IN
        assert package.resources[1].animation_type == AnimationType.ZOOM_OUT
        assert package.resources[2].animation_type == AnimationType.ZOOM_IN
        assert package.resources[3].animation_type == AnimationType.ZOOM_OUT

    def test_source_provider(self):
        assigner = AnimationAssigner()
        package = assigner.assign(2, [Path("a.png"), Path("b.png")])
        assert package.source_provider == "slide"


class TestAnimationAssignerFromSegments:
    def test_with_segments_and_slides(self):
        assigner = AnimationAssigner(text_slides=False)
        segments = [
            {"speaker": "A", "content": "text1"},
            {"speaker": "B", "content": "text2"},
        ]
        slides = [Path("s0.png"), Path("s1.png")]

        package = assigner.assign_from_segments(segments, slides)
        assert len(package.resources) == 2
        assert all(r.image_path is not None for r in package.resources)

    def test_with_mapping(self):
        assigner = AnimationAssigner(text_slides=False)
        segments = [
            {"speaker": "A", "content": "t1"},
            {"speaker": "B", "content": "t2"},
            {"speaker": "A", "content": "t3"},
        ]
        slides = [Path("s0.png"), Path("s1.png")]
        mapping = {0: 0, 1: 0, 2: 1}

        package = assigner.assign_from_segments(segments, slides, mapping)
        assert len(package.resources) == 3
        assert package.resources[0].image_path == Path("s0.png")
        assert package.resources[1].image_path == Path("s0.png")
        assert package.resources[2].image_path == Path("s1.png")

    def test_no_slides(self):
        assigner = AnimationAssigner()
        segments = [{"speaker": "A", "content": "t1"}]

        package = assigner.assign_from_segments(segments, None)
        assert len(package.resources) == 1
        assert package.resources[0].animation_type == AnimationType.STATIC

    def test_text_slides_all_static(self):
        """text_slides=True (デフォルト) では全画像がSTATICになる。"""
        assigner = AnimationAssigner()
        segments = [
            {"speaker": "A", "content": "text1"},
            {"speaker": "B", "content": "text2"},
        ]
        slides = [Path("s0.png"), Path("s1.png")]

        package = assigner.assign_from_segments(segments, slides)
        assert len(package.resources) == 2
        for r in package.resources:
            assert r.animation_type == AnimationType.STATIC
            assert r.image_path is not None
