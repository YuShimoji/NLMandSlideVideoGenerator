"""
エクスポートフォールバックマネージャー
複数の編集バックエンドを優先順位付きで試行し、失敗時に自動フォールバックする

フォールバック戦略:
1. YMM4 REST API (将来実装) - 最高品質、完全自動化
2. YMM4 AutoHotkey - 中品質、GUI操作による自動化
3. MoviePy/FFmpeg - 基本品質、確実な動作

設計思想:
- 各バックエンドは IEditingBackend インターフェースを実装
- 失敗時は次のバックエンドに自動切替
- ユーザーは単一のrender()呼び出しで済む
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from ..interfaces import IEditingBackend
from ..utils.logger import logger
from notebook_lm.audio_generator import AudioInfo
from slides.slide_generator import SlidesPackage
from notebook_lm.transcript_processor import TranscriptInfo
from video_editor.video_composer import VideoInfo


class BackendType(Enum):
    """バックエンドタイプ"""
    YMM4_API = "ymm4_api"       # 将来実装
    YMM4_AHK = "ymm4_ahk"       # AutoHotkey
    MOVIEPY = "moviepy"         # MoviePy/FFmpeg


@dataclass
class BackendConfig:
    """バックエンド設定"""
    backend_type: BackendType
    enabled: bool = True
    priority: int = 0  # 小さいほど優先
    timeout_seconds: float = 300.0  # 5分
    retry_count: int = 1
    extra_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FallbackResult:
    """フォールバック結果"""
    success: bool
    video_info: Optional[VideoInfo] = None
    used_backend: Optional[BackendType] = None
    attempted_backends: List[BackendType] = field(default_factory=list)
    errors: Dict[BackendType, str] = field(default_factory=dict)


class ExportFallbackManager:
    """
    エクスポートフォールバックマネージャー
    
    複数のバックエンドを優先順位付きで管理し、
    失敗時に自動的に次のバックエンドにフォールバックする
    """
    
    def __init__(
        self,
        configs: Optional[List[BackendConfig]] = None,
        auto_detect: bool = True
    ):
        """
        Args:
            configs: バックエンド設定リスト（Noneの場合はデフォルト）
            auto_detect: 利用可能なバックエンドを自動検出するか
        """
        self.configs = configs or self._default_configs()
        self.backends: Dict[BackendType, IEditingBackend] = {}
        
        if auto_detect:
            self._detect_available_backends()
        
        # 優先順位でソート
        self.configs.sort(key=lambda c: c.priority)
        
        logger.info(f"ExportFallbackManager初期化: {len(self.configs)}個のバックエンド設定")
    
    def _default_configs(self) -> List[BackendConfig]:
        """デフォルト設定"""
        return [
            BackendConfig(
                backend_type=BackendType.YMM4_API,
                enabled=False,  # 未実装
                priority=1,
                timeout_seconds=600.0,
            ),
            BackendConfig(
                backend_type=BackendType.YMM4_AHK,
                enabled=True,
                priority=2,
                timeout_seconds=300.0,
                retry_count=2,
            ),
            BackendConfig(
                backend_type=BackendType.MOVIEPY,
                enabled=True,
                priority=3,
                timeout_seconds=180.0,
            ),
        ]
    
    def _detect_available_backends(self) -> None:
        """利用可能なバックエンドを検出"""
        # YMM4 AutoHotkey: AutoHotkey.exeの存在確認
        ahk_paths = [
            Path("C:/Program Files/AutoHotkey/AutoHotkey.exe"),
            Path("C:/Program Files/AutoHotkey/v2/AutoHotkey.exe"),
        ]
        ahk_available = any(p.exists() for p in ahk_paths)
        
        # YMM4本体の確認
        ymm4_paths = [
            Path("C:/Program Files/YMM4/YMM4.exe"),
            Path("D:/Program Files/YMM4/YMM4.exe"),
        ]
        ymm4_available = any(p.exists() for p in ymm4_paths)
        
        for config in self.configs:
            if config.backend_type == BackendType.YMM4_AHK:
                if not (ahk_available and ymm4_available):
                    config.enabled = False
                    logger.info("YMM4 AHKバックエンド: AutoHotkeyまたはYMM4が見つかりません")
            elif config.backend_type == BackendType.YMM4_API:
                # 未実装
                config.enabled = False
    
    def _get_backend(self, backend_type: BackendType) -> IEditingBackend:
        """バックエンドインスタンスを取得（遅延初期化）"""
        if backend_type not in self.backends:
            if backend_type == BackendType.YMM4_AHK:
                from .ymm4_backend import YMM4EditingBackend
                self.backends[backend_type] = YMM4EditingBackend()
            elif backend_type == BackendType.MOVIEPY:
                from .moviepy_backend import MoviePyEditingBackend
                self.backends[backend_type] = MoviePyEditingBackend()
            elif backend_type == BackendType.YMM4_API:
                # 将来実装
                raise NotImplementedError("YMM4 REST APIバックエンドは未実装です")
        
        return self.backends[backend_type]
    
    async def render(
        self,
        timeline_plan: Dict[str, Any],
        audio: AudioInfo,
        slides: SlidesPackage,
        transcript: TranscriptInfo,
        quality: str = "1080p",
        extras: Optional[Dict[str, Any]] = None,
        preferred_backend: Optional[BackendType] = None,
    ) -> FallbackResult:
        """
        動画をレンダリング（フォールバック付き）
        
        Args:
            timeline_plan: タイムライン計画
            audio: 音声情報
            slides: スライドパッケージ
            transcript: 台本情報
            quality: 出力品質
            extras: 追加オプション
            preferred_backend: 優先バックエンド（指定時は最初に試行）
            
        Returns:
            FallbackResult: 結果（成功/失敗、使用バックエンド、エラー情報）
        """
        result = FallbackResult(success=False)
        
        # 有効なバックエンドを優先順位順に取得
        enabled_configs = [c for c in self.configs if c.enabled]
        
        # 優先バックエンドがある場合は先頭に
        if preferred_backend:
            preferred_config = next(
                (c for c in enabled_configs if c.backend_type == preferred_backend),
                None
            )
            if preferred_config:
                enabled_configs.remove(preferred_config)
                enabled_configs.insert(0, preferred_config)
        
        if not enabled_configs:
            logger.error("有効なバックエンドがありません")
            return result
        
        logger.info(f"レンダリング開始: {len(enabled_configs)}個のバックエンドを試行")
        
        for config in enabled_configs:
            backend_type = config.backend_type
            result.attempted_backends.append(backend_type)
            
            for attempt in range(config.retry_count):
                try:
                    logger.info(
                        f"バックエンド試行: {backend_type.value} "
                        f"(試行{attempt + 1}/{config.retry_count})"
                    )
                    
                    backend = self._get_backend(backend_type)
                    
                    # タイムアウト付きで実行
                    video_info = await asyncio.wait_for(
                        backend.render(
                            timeline_plan=timeline_plan,
                            audio=audio,
                            slides=slides,
                            transcript=transcript,
                            quality=quality,
                            extras=extras,
                        ),
                        timeout=config.timeout_seconds
                    )
                    
                    # 成功
                    result.success = True
                    result.video_info = video_info
                    result.used_backend = backend_type
                    
                    logger.info(f"レンダリング成功: {backend_type.value}")
                    return result
                    
                except asyncio.TimeoutError:
                    error_msg = f"タイムアウト ({config.timeout_seconds}秒)"
                    logger.warning(f"{backend_type.value}: {error_msg}")
                    result.errors[backend_type] = error_msg
                    
                except NotImplementedError as e:
                    error_msg = str(e)
                    logger.warning(f"{backend_type.value}: {error_msg}")
                    result.errors[backend_type] = error_msg
                    break  # リトライ不要
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"{backend_type.value} エラー: {error_msg}")
                    result.errors[backend_type] = error_msg
                    
                    if attempt < config.retry_count - 1:
                        # リトライ前に待機
                        await asyncio.sleep(2.0)
            
            # 次のバックエンドへフォールバック
            logger.info(f"{backend_type.value} 失敗、次のバックエンドへ")
        
        logger.error(f"全バックエンドが失敗: {list(result.errors.keys())}")
        return result
    
    def get_available_backends(self) -> List[BackendType]:
        """利用可能なバックエンドのリストを取得"""
        return [c.backend_type for c in self.configs if c.enabled]
    
    def set_backend_enabled(self, backend_type: BackendType, enabled: bool) -> None:
        """バックエンドの有効/無効を設定"""
        for config in self.configs:
            if config.backend_type == backend_type:
                config.enabled = enabled
                logger.info(f"{backend_type.value}: {'有効' if enabled else '無効'}化")
                return
    
    def get_status(self) -> Dict[str, Any]:
        """マネージャーの状態を取得"""
        return {
            "backends": [
                {
                    "type": c.backend_type.value,
                    "enabled": c.enabled,
                    "priority": c.priority,
                    "timeout_seconds": c.timeout_seconds,
                    "retry_count": c.retry_count,
                }
                for c in self.configs
            ],
            "available": [bt.value for bt in self.get_available_backends()],
        }
