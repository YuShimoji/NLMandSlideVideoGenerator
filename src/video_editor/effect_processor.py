"""
エフェクト処理モジュール
スライド画像にズーム、パン、フェードエフェクトを適用
"""
import asyncio
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
import json

# 基本的なロガー設定（loguruの代替）
class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def success(self, msg): print(f"[SUCCESS] {msg}")
    def warning(self, msg): print(f"[WARNING] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def debug(self, msg): print(f"[DEBUG] {msg}")

logger = SimpleLogger()

# PILとnumpyは必要時にインポート
try:
    from PIL import Image, ImageEnhance
    import numpy as np
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL/Pillowまたはnumpyが利用できません。画像処理機能は制限されます。")

from config.settings import settings
from notebook_lm.transcript_processor import TranscriptInfo, TranscriptSegment

@dataclass
class EffectSettings:
    """エフェクト設定"""
    effect_type: str
    start_scale: float
    end_scale: float
    start_position: Tuple[float, float]
    end_position: Tuple[float, float]
    duration: float
    easing: str

@dataclass
class ProcessedSlide:
    """処理済みスライド"""
    slide_id: int
    original_path: Path
    processed_frames: List[Path]
    effect_applied: str
    duration: float

class EffectProcessor:
    """エフェクト処理クラス"""
    
    def __init__(self):
        self.effect_settings = settings.EFFECT_SETTINGS
        self.output_dir = settings.VIDEOS_DIR / "processed_slides"
        self.target_resolution = settings.VIDEO_SETTINGS["resolution"]
        self.fps = settings.VIDEO_SETTINGS["fps"]
        
    async def apply_effects(
        self, 
        slide_images: List[Path], 
        transcript: TranscriptInfo
    ) -> List[ProcessedSlide]:
        """
        スライド画像にエフェクトを適用
        
        Args:
            slide_images: スライド画像パス一覧
            transcript: 台本情報
            
        Returns:
            List[ProcessedSlide]: 処理済みスライド一覧
        """
        logger.info(f"エフェクト処理開始: {len(slide_images)}枚")
        
        try:
            # 出力ディレクトリ作成
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            processed_slides = []
            
            for i, slide_path in enumerate(slide_images):
                # 対応するセグメント情報を取得
                segment_info = self._get_segment_info(i, transcript)
                
                # エフェクト設定を決定
                effect_config = self._determine_effect_config(segment_info)
                
                # エフェクト適用
                processed_slide = await self._apply_effect_to_slide(
                    slide_path, i + 1, effect_config, segment_info
                )
                
                processed_slides.append(processed_slide)
            
            logger.success(f"エフェクト処理完了: {len(processed_slides)}枚")
            return processed_slides
            
        except (OSError, AttributeError, TypeError, ValueError, RuntimeError) as e:
            logger.error(f"エフェクト処理エラー: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"エフェクト処理エラー: {str(e)}")
            raise
    
    def _get_segment_info(self, slide_index: int, transcript: TranscriptInfo) -> Dict[str, Any]:
        """
        スライドに対応するセグメント情報を取得
        
        Args:
            slide_index: スライドインデックス
            transcript: 台本情報
            
        Returns:
            Dict[str, Any]: セグメント情報
        """
        if slide_index < len(transcript.segments):
            segment = transcript.segments[slide_index]
            return {
                "duration": segment.end_time - segment.start_time,
                "text_length": len(segment.text),
                "key_points": segment.key_points,
                "speaker": segment.speaker
            }
        else:
            # デフォルト情報
            return {
                "duration": 15.0,
                "text_length": 100,
                "key_points": [],
                "speaker": "ナレーター"
            }
    
    def _determine_effect_config(self, segment_info: Dict[str, Any]) -> EffectSettings:
        """
        セグメント情報に基づいてエフェクト設定を決定
        
        Args:
            segment_info: セグメント情報
            
        Returns:
            EffectSettings: エフェクト設定
        """
        duration = segment_info["duration"]
        text_length = segment_info["text_length"]
        
        # エフェクトタイプの決定
        if text_length > 150:
            effect_type = "zoom_in"  # 長いテキストはズームイン
        elif len(segment_info["key_points"]) > 2:
            effect_type = "pan_right"  # 重要ポイントが多い場合はパン
        else:
            effect_type = "zoom_out"  # デフォルトはズームアウト
        
        # エフェクト設定を構築
        base_settings = self.effect_settings
        
        if effect_type == "zoom_in":
            return EffectSettings(
                effect_type="zoom",
                start_scale=base_settings["zoom"]["start_scale"],
                end_scale=base_settings["zoom"]["end_scale"],
                start_position=(0.0, 0.0),
                end_position=(0.0, 0.0),
                duration=duration,
                easing=base_settings["zoom"]["easing"]
            )
        elif effect_type == "zoom_out":
            return EffectSettings(
                effect_type="zoom",
                start_scale=base_settings["zoom"]["end_scale"],
                end_scale=base_settings["zoom"]["start_scale"],
                start_position=(0.0, 0.0),
                end_position=(0.0, 0.0),
                duration=duration,
                easing=base_settings["zoom"]["easing"]
            )
        elif effect_type == "pan_right":
            return EffectSettings(
                effect_type="pan",
                start_scale=1.0,
                end_scale=1.0,
                start_position=(-base_settings["pan"]["max_horizontal"], 0.0),
                end_position=(base_settings["pan"]["max_horizontal"], 0.0),
                duration=duration,
                easing="linear"
            )
        else:
            # デフォルト設定
            return EffectSettings(
                effect_type="static",
                start_scale=1.0,
                end_scale=1.0,
                start_position=(0.0, 0.0),
                end_position=(0.0, 0.0),
                duration=duration,
                easing="linear"
            )
    
    async def _apply_effect_to_slide(
        self, 
        slide_path: Path, 
        slide_id: int, 
        effect_config: EffectSettings,
        segment_info: Dict[str, Any]
    ) -> ProcessedSlide:
        """
        単一スライドにエフェクトを適用
        
        Args:
            slide_path: スライド画像パス
            slide_id: スライドID
            effect_config: エフェクト設定
            segment_info: セグメント情報
            
        Returns:
            ProcessedSlide: 処理済みスライド
        """
        logger.debug(f"スライド{slide_id}にエフェクト適用中: {effect_config.effect_type}")
        
        # 元画像読み込み
        original_image = Image.open(slide_path)
        
        # 解像度調整
        resized_image = self._resize_image_to_target(original_image)
        
        # フレーム数計算
        total_frames = int(effect_config.duration * self.fps)
        
        # フレーム生成
        frame_paths = []
        for frame_idx in range(total_frames):
            progress = frame_idx / max(total_frames - 1, 1)
            
            # エフェクト適用
            processed_frame = self._apply_frame_effect(
                resized_image, progress, effect_config
            )
            
            # フレーム保存
            frame_path = self.output_dir / f"slide_{slide_id:03d}_frame_{frame_idx:04d}.png"
            processed_frame.save(frame_path)
            frame_paths.append(frame_path)
        
        processed_slide = ProcessedSlide(
            slide_id=slide_id,
            original_path=slide_path,
            processed_frames=frame_paths,
            effect_applied=effect_config.effect_type,
            duration=effect_config.duration
        )
        
        logger.debug(f"スライド{slide_id}エフェクト適用完了: {len(frame_paths)}フレーム")
        return processed_slide
    
    def _resize_image_to_target(self, image: Image.Image) -> Image.Image:
        """
        画像を目標解像度にリサイズ
        
        Args:
            image: 元画像
            
        Returns:
            Image.Image: リサイズ済み画像
        """
        target_width, target_height = self.target_resolution
        
        # アスペクト比を保持してリサイズ
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        
        # キャンバスサイズを目標解像度に合わせる
        canvas = Image.new('RGB', (target_width, target_height), (0, 0, 0))
        
        # 中央配置
        x_offset = (target_width - image.width) // 2
        y_offset = (target_height - image.height) // 2
        canvas.paste(image, (x_offset, y_offset))
        
        return canvas
    
    def _apply_frame_effect(
        self, 
        image: Image.Image, 
        progress: float, 
        effect_config: EffectSettings
    ) -> Image.Image:
        """
        単一フレームにエフェクトを適用
        
        Args:
            image: 元画像
            progress: 進行度 (0.0-1.0)
            effect_config: エフェクト設定
            
        Returns:
            Image.Image: エフェクト適用済み画像
        """
        # イージング関数適用
        eased_progress = self._apply_easing(progress, effect_config.easing)
        
        if effect_config.effect_type == "zoom":
            return self._apply_zoom_effect(image, eased_progress, effect_config)
        elif effect_config.effect_type == "pan":
            return self._apply_pan_effect(image, eased_progress, effect_config)
        else:
            return image.copy()
    
    def _apply_easing(self, progress: float, easing_type: str) -> float:
        """
        イージング関数を適用
        
        Args:
            progress: 進行度 (0.0-1.0)
            easing_type: イージングタイプ
            
        Returns:
            float: イージング適用済み進行度
        """
        if easing_type == "ease_in_out":
            return 0.5 * (1 - np.cos(progress * np.pi))
        elif easing_type == "ease_in":
            return progress * progress
        elif easing_type == "ease_out":
            return 1 - (1 - progress) * (1 - progress)
        else:  # linear
            return progress
    
    def _apply_zoom_effect(
        self, 
        image: Image.Image, 
        progress: float, 
        effect_config: EffectSettings
    ) -> Image.Image:
        """
        ズームエフェクトを適用
        
        Args:
            image: 元画像
            progress: 進行度
            effect_config: エフェクト設定
            
        Returns:
            Image.Image: ズーム適用済み画像
        """
        # スケール計算
        scale = (effect_config.start_scale + 
                (effect_config.end_scale - effect_config.start_scale) * progress)
        
        # 画像サイズ計算
        width, height = image.size
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # リサイズ
        scaled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 中央クロップまたはパディング
        canvas = Image.new('RGB', (width, height), (0, 0, 0))
        
        if scale > 1.0:  # ズームイン（クロップ）
            x_offset = (new_width - width) // 2
            y_offset = (new_height - height) // 2
            cropped = scaled_image.crop((x_offset, y_offset, x_offset + width, y_offset + height))
            canvas.paste(cropped, (0, 0))
        else:  # ズームアウト（パディング）
            x_offset = (width - new_width) // 2
            y_offset = (height - new_height) // 2
            canvas.paste(scaled_image, (x_offset, y_offset))
        
        return canvas
    
    def _apply_pan_effect(
        self, 
        image: Image.Image, 
        progress: float, 
        effect_config: EffectSettings
    ) -> Image.Image:
        """
        パンエフェクトを適用
        
        Args:
            image: 元画像
            progress: 進行度
            effect_config: エフェクト設定
            
        Returns:
            Image.Image: パン適用済み画像
        """
        width, height = image.size
        
        # 位置計算
        start_x, start_y = effect_config.start_position
        end_x, end_y = effect_config.end_position
        
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        
        # ピクセル単位の移動量
        offset_x = int(current_x * width)
        offset_y = int(current_y * height)
        
        # 少し拡大した画像を作成（パン用の余白確保）
        scale_factor = 1.2
        expanded_width = int(width * scale_factor)
        expanded_height = int(height * scale_factor)
        expanded_image = image.resize((expanded_width, expanded_height), Image.Resampling.LANCZOS)
        
        # パン適用（クロップ位置を調整）
        base_x = (expanded_width - width) // 2
        base_y = (expanded_height - height) // 2
        
        crop_x = base_x + offset_x
        crop_y = base_y + offset_y
        
        # 境界チェック
        crop_x = max(0, min(crop_x, expanded_width - width))
        crop_y = max(0, min(crop_y, expanded_height - height))
        
        cropped = expanded_image.crop((crop_x, crop_y, crop_x + width, crop_y + height))
        
        return cropped
    
    def add_transition_effects(
        self, 
        processed_slides: List[ProcessedSlide]
    ) -> List[ProcessedSlide]:
        """
        スライド間のトランジションエフェクトを追加
        
        Args:
            processed_slides: 処理済みスライド一覧
            
        Returns:
            List[ProcessedSlide]: トランジション追加済みスライド一覧
        """
        logger.info("トランジションエフェクト追加中...")
        
        if len(processed_slides) <= 1:
            return processed_slides
        
        transition_duration = self.effect_settings["fade"]["duration"]
        transition_frames = int(transition_duration * self.fps)
        
        enhanced_slides = []
        
        for i, slide in enumerate(processed_slides):
            enhanced_slide = slide
            
            # 最後のスライド以外にフェードアウトフレームを追加
            if i < len(processed_slides) - 1:
                next_slide = processed_slides[i + 1]
                fade_frames = self._create_fade_transition(
                    slide.processed_frames[-1],
                    next_slide.processed_frames[0],
                    transition_frames
                )
                
                # フェードフレームを追加
                enhanced_slide.processed_frames.extend(fade_frames)
                enhanced_slide.duration += transition_duration
            
            enhanced_slides.append(enhanced_slide)
        
        logger.info("トランジションエフェクト追加完了")
        return enhanced_slides
    
    def _create_fade_transition(
        self, 
        from_frame_path: Path, 
        to_frame_path: Path, 
        transition_frames: int
    ) -> List[Path]:
        """
        フェードトランジションフレームを作成
        
        Args:
            from_frame_path: 開始フレームパス
            to_frame_path: 終了フレームパス
            transition_frames: トランジションフレーム数
            
        Returns:
            List[Path]: トランジションフレームパス一覧
        """
        from_image = Image.open(from_frame_path)
        to_image = Image.open(to_frame_path)
        
        fade_frame_paths = []
        
        for i in range(transition_frames):
            alpha = i / (transition_frames - 1)
            
            # アルファブレンディング
            blended = Image.blend(from_image, to_image, alpha)
            
            # フレーム保存
            frame_path = self.output_dir / f"transition_{from_frame_path.stem}_to_{to_frame_path.stem}_{i:04d}.png"
            blended.save(frame_path)
            fade_frame_paths.append(frame_path)
        
        return fade_frame_paths
    
    def optimize_for_video_codec(self, processed_slides: List[ProcessedSlide]) -> List[ProcessedSlide]:
        """
        動画コーデック向けに最適化
        
        Args:
            processed_slides: 処理済みスライド一覧
            
        Returns:
            List[ProcessedSlide]: 最適化済みスライド一覧
        """
        logger.info("動画コーデック向け最適化実行")
        
        for slide in processed_slides:
            for frame_path in slide.processed_frames:
                # 画像を再保存（品質最適化）
                image = Image.open(frame_path)
                
                # JPEGで一時保存してノイズ除去
                temp_path = frame_path.with_suffix('.jpg')
                image.save(temp_path, 'JPEG', quality=95, optimize=True)
                
                # PNGに戻す
                optimized_image = Image.open(temp_path)
                optimized_image.save(frame_path, 'PNG', optimize=True)
                
                # 一時ファイル削除
                temp_path.unlink()
        
        logger.info("動画コーデック向け最適化完了")
        return processed_slides
