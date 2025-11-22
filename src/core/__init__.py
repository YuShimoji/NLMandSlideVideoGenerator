"""Core package for the modular video generation pipeline.

このモジュールでは **重い依存関係の即時インポートを行わない** ようにし、
`notebook_lm` やその他サブシステムとの循環インポートを防ぎます。

利用側は必要に応じて以下のように直接インポートしてください:

    from core.pipeline import ModularVideoPipeline
    from core.helpers import build_default_pipeline
    from core.exceptions import PipelineError
    from core.models import PipelineArtifacts

これにより、`core` パッケージを経由したインポート時でも安全に初期化できます。
"""

__all__ = []
