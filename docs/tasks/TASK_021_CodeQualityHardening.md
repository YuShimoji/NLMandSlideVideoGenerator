# Task: コード品質ハードニング
Status: LAYER_A_DONE
Tier: 2
Branch: master
Owner: Worker-B
Created: 2026-03-02T22:00:00+09:00
Report: AI_CONTEXT.md (2026-03-03セクション参照)

## Objective
- プロジェクト全体の例外処理、型安全性、コード品質を本番運用グレードに引き上げる
- 静的解析ツール(mypy, pylint)のCI統合を完了し、品質ゲートを確立する

## Context
- 2026-03-02 総点検で97件の品質課題を検出（Critical 5, High 45, Medium 35, Low 12）
- 主要課題: bare except Exception（36件）、型ヒント不足（14件）、長大関数（6件）
- C#側: CsvReadResult.Warnings 欠落（修正済）、Dispatcher null安全性（修正済）

## Deliverables

### Layer A（AI完結）

#### A-1: Python例外処理の体系化
- [x] ドメイン固有例外クラスの作成（AudioGenerationError, VideoCompositionError, APIAuthenticationError等）
- [x] `src/server/api.py` のbare `except Exception:` をドメイン例外に置換（3箇所 Critical）
- [x] `src/youtube/uploader.py` の8箇所の例外処理を具体化 + QuotaExceededError/UploadError適用
- [x] `src/video_editor/video_composer.py` の14箇所の重複catch削除
- [x] `src/notebook_lm/audio_generator.py` - 監査の結果、正当な2段パターン確認（修正不要）
- [x] `src/core/pipeline.py` - 監査の結果、正当な2段パターン確認（修正不要）

#### A-2: 型安全性の強化

- [x] `src/core/interfaces.py` の ThumbnailInfo import追加（mypy error修正）
- [x] `src/core/__init__.py` の `__all__` 型注釈追加（mypy error修正）
- [x] mypy.ini 作成、core 3ファイル（exceptions, interfaces, models）strict check設定
- [ ] `src/core/pipeline.py` の内部関数に型ヒント追加（TASK_024で対応予定）
- [ ] `src/video_editor/video_composer.py` のtuple型をSpecific型に変更（将来対応）
- [ ] mypy --strict チェック対象の段階的拡大（将来対応）

#### A-3: コード複雑性の削減
- [x] `src/server/api.py::_to_dict` のネスト(5段)を3段以下に削減
- [x] 重複する try/except パターン削除（uploader 8箇所、video_composer 14箇所）
- [x] `src/notebook_lm/audio_generator.py::_check_generation_status` - 監査で正当確認

#### A-4: セキュリティ改善
- [x] `src/server/api.py` のパスアクセスに `Path.resolve()` + symlink検出追加
- [x] API キー設定時の入力バリデーション追加（制御文字排除）
- [ ] 動的インポート (`__import__`) を `importlib.import_module` に置換（将来対応）

#### A-5: 静的解析CI統合
- [x] `mypy` 設定ファイル(mypy.ini)作成、段階的strict化
- [x] `scripts/ci.ps1` にmypyステージ追加（Step 3）
- [x] mypy clean pass確認（core 3ファイル: 0 errors）

### Layer B（手動検証）
- [ ] mypy警告ゼロ確認（Core モジュール）
- [ ] CI パイプラインの完全実行確認

## DoD (Definition of Done)

- [x] bare `except Exception:` が Critical/High 箇所でゼロ（重複削除22箇所、残存73箇所は正当な2段パターン）
- [x] Core モジュール（exceptions, interfaces, models）の mypy パス（0 errors）
- [x] CI パイプライン（ci.ps1）に型チェックステージ追加済
- [x] 既存テスト全パス（109 passed, 7 skipped, 4 deselected）

## Constraints
- 既存テストを壊さない
- 外部向けAPIの振る舞いは変更しない
- 段階的に導入（一度に全ファイルを変更しない）

## Estimated Effort
- Layer A: 8-12時間
- Layer B: 1時間
