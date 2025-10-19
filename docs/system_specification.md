# システム仕様書

## 1. システム概要

### 1.1 目的
YouTube や TikTok など複数プラットフォーム向けの動画制作を、素材用意・編集・投稿の 3 段階に分けてモジュラー化し、ユーザーの作業スタイル（手動・半自動・全自動）に合わせて柔軟に切り替えられるワークフロー基盤を提供する。

### 1.2 システム名
NLMandSlideVideoGenerator（NotebookLM and Slide Video Generator）

### 1.3 対象ユーザー
- YouTube/TikTok コンテンツクリエイター
- 企業/教育機関の動画制作担当者
- YukkuriMovieMaker4 (YMM4) を活用した編集者
- AI/MCP 連携による省力化を求めるワークフローエンジニア

### 1.4 ステージ構成
| Stage | 主目的 | 主なモジュール | モード切替 |
|-------|--------|----------------|------------|
| Stage 1: 素材用意 | 台本・音声・参考素材の準備 | `ScriptProvider`, `VoicePipeline`, `AssetRegistry` | manual / assist / auto |
| Stage 2: 編集生成 | タイムライン構築・映像生成 | `TimelinePlanner`, `SlideProvider`, `EditingBackend (MoviePy, YMM4)` | assist / auto |
| Stage 3: 投稿配信 | メタデータ生成・投稿 | `MetadataGenerator`, `Scheduler`, `PlatformAdapter` | manual / auto |

## 2. 機能要件

### 2.1 コア機能（Stage別）

#### 2.1.1 Stage 1: Script & Voice Orchestration
- **入力**: トピック、参考URL、NotebookLMエクスポート、ユーザーアップロード台本、Web MCP 経由の取得結果
- **処理**:
  - NotebookLM / Gemini API / ローカルプロンプトによる台本生成 (`IScriptProvider`)
  - DeepDive など NotebookLM 固有構造を一般化するコンテンツ正規化 (`ContentAdapter`)
  - ElevenLabs / OpenAI / Azure / ユーザー音声を用いた `VoicePipeline` と `AudioValidator`
  - 素材メタデータ管理 (`AssetRegistry`)
- **出力**: `ScriptBundle`, `AudioInfo`, クリップ用素材リスト
- **モード切替**: 完全手動入力、AI補完（人間レビュー必須）、完全自動収集

#### 2.1.2 Stage 2: Editing & Rendering
- **入力**: ScriptBundle, AudioInfo, ユーザー編集プリセット（YMM4テンプレート, スライド配置）
- **処理**:
  - `TimelinePlanner` によるセグメント時間配分とエフェクト指示
  - `Slide/Image Provider` による Google Slides / 手動画像 / NotebookLMスライドの選択
  - `SubtitleStyler` による装飾プリセット（縁取り、アニメーション対応）
  - `EffectProcessor` 拡張によるカメラワーク・テロップ・立ち絵制御
  - `EditingBackend`:
    - MoviePy 合成（現行実装）
    - YMM4 API を利用した `.y4mmp` / `.exo` テンプレート複製とタイムライン生成
- **出力**: `VideoInfo`, `TimelinePlan`, YMM4 プロジェクトファイル, プレビュー用動画
- **特徴**: YMM4 を利用する場合は GUI での手動調整を前提に、差分適用と再レンダリングを自動化

#### 2.1.3 Stage 3: Publishing Automation
- **入力**: VideoInfo, TimelinePlan, ScriptBundle, サムネイル素材
- **処理**:
  - `MetadataGenerator` による概要欄・タグ・チャプター・広告位置の生成
  - `Scheduler` による予約投稿、公開範囲、マルチプラットフォーム配信計画
  - `ThumbnailPipeline`（計画中）によるテンプレートベースのサムネイル生成
  - `PlatformAdapter` による YouTube / TikTok / ローカル書き出し切り替え
- **出力**: 投稿実行結果、ドラフト用メタデータJSON、サムネイルファイル
- **選択肢**: 自動投稿、ドラフト作成のみ、CSV/JSON 書き出しによる手動運用

### 2.2 補助機能

#### 2.2.1 コンテンツ管理
- `AssetRegistry` による素材ライフサイクル管理（参照元URL、ライセンス、更新履歴）
- プロジェクト別履歴と差分管理（テンプレート更新、YMM4プロファイル比較）
- 手動編集結果を AI 側にフィードバックするためのプロンプト調整ログ

#### 2.2.2 品質管理
- 音声品質自動評価（ノイズ、dB レベル、長さ）
- 台本校正支援（要約比較、ファクトチェックMCPとの連携余地）
- スライド/字幕スタイルのベンチマーク（標準テーマとの比較レポート）
- タイムライン整合性チェック（音声長と映像長の不一致検知）

#### 2.2.3 エラーハンドリング
- Stage単位のリトライとフォールバック（例: Gemini失敗時は NotebookLM へ切替）
- YMM4 API エラー時のテンプレート再同期と MoviePy フォールバック
- 投稿 API のクォータ監視とキューイング

### 2.3 拡張ターゲット
- **サムネイル自動生成**: テンプレート JSON + 文字/画像差分の自動反映
- **広告・チャプター挿入**: `TimelinePlan` から自動抽出
- **マルチプラットフォーム最適化**: 縦横比変更、ショート動画切り出し
- **MCP 連携**: Web 操作用 MCP、ドキュメント検索 MCP との共存

## 3. 非機能要件

### 3.1 性能要件
- **処理時間**: 5分動画で MoviePy 経路は 20 分以内、YMM4 バッチ生成は 10 分以内
- **同時処理**: 最大 3 プロジェクトの非同期実行をキュー管理で保証
- **ファイルサイズ**: 4K 動画 4GB までをサポート

### 3.2 可用性要件
- **ステージ単位の復旧**: 失敗ステージのみ再実行可能
- **テンプレート同期**: YMM4 テンプレートとスクリプトを Git/クラウド上でバージョン管理

### 3.3 セキュリティ要件
- API キーは `.env` と OS 環境変数で管理、MCP 経由の秘匿情報は保護ストレージに格納
- YMM4 テンプレートに含まれる素材（立ち絵、BGM）のライセンスメタ情報を `AssetRegistry` で追跡
- 投稿前チェックリストで NG ワード/著作権リスクをレビュー

### 3.4 保守性要件
- プロトコルベースの依存性注入（`src/core/interfaces.py`）により差し替えが容易
- Stage 別ユニットテスト + 統合テスト (`run_modular_demo.py` 等) を整備
- ドキュメントとテンプレートを `docs/` と `data/templates/` で同期管理

## 4. システム構成

### 4.1 アーキテクチャ概要
```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Stage 1       │   │ Stage 2       │   │ Stage 3       │
│ Script/Assets │──▶│ Editing       │──▶│ Publishing    │
│               │   │ (MoviePy/YMM4)│   │ (YouTube/TikTok)
└──────────────┘   └──────────────┘   └──────────────┘
        ▲                   ▲                    ▲
        │                   │                    │
  Manual Assist Auto  Manual Assist Auto   Manual Auto
```

### 4.2 データフロー
1. **素材入力**: ユーザー/MCP/NotebookLM/Gemini から素材取得
2. **台本正規化**: DeepDive JSON/Markdown を `ScriptBundle` に変換
3. **音声生成**: TTS or 収録音声を `AudioInfo` に統一
4. **タイムライン構築**: `TimelinePlanner` が YMM4/ MoviePy 両対応の指示書を生成
5. **レンダリング**: MoviePy or YMM4 API
6. **メタデータ生成**: 投稿テンプレートから概要欄/タグ/広告位置を生成
7. **投稿/書き出し**: プラットフォーム別アダプターで自動投稿 or ドラフト作成

### 4.3 外部システム連携
- **NotebookLM / Gemini API**: 台本生成・要約補完
- **MCP Agents**: Web 情報取得、翻訳、要約
- **TTS プロバイダー**: ElevenLabs / OpenAI / Azure / Google Cloud
- **Google Slides API**: スライド生成・画像エクスポート
- **YukkuriMovieMaker4 API**: テンプレートからタイムライン再構築
- **YouTube Data API / TikTok API**: 投稿・メタデータ設定

## 5. 技術仕様

### 5.1 開発環境
- **言語**: Python 3.10+
- **エントリポイント**: CLI (`main.py`, `run_modular_demo.py`)、将来のAPI化は FastAPI/Cloud Run を想定
- **テンプレート管理**: JSON/YAML（メタデータ）、YMM4 プロジェクトファイル
- **自動化スクリプト**: `scripts/` ディレクトリ（将来追加）で MCP 制御やテンプレ同期を提供

### 5.2 主要ライブラリ
```python
# コア
asyncio
dataclasses

# 動画・音声
moviepy
pydub

# 画像・スライド
Pillow
google-api-python-client (Slides)

# MCP/AI
google-generativeai (Gemini)
httpx / requests

# YMM4 連携
requests (REST API)
```

### 5.3 API 仕様（将来拡張）
#### 5.3.1 パイプライン制御 API（想定）
```
POST /api/v1/pipelines/run
{
  "topic": "調査トピック",
  "sources": [...],
  "modes": {"stage1": "assist", "stage2": "auto", "stage3": "manual"},
  "editing_backend": "ymm4",
  "targets": ["youtube", "tiktok"],
  "schedule": "2025-01-01T12:00:00+09:00"
}
```

#### 5.3.2 テンプレート同期 API（想定）
```
POST /api/v1/templates/sync
{
  "template_id": "ymm4_default_v1",
  "assets": [...],
  "overrides": {"subtitle_style": "bold_glow"}
}
```

## 6. 運用要件

### 6.1 監視要件
- API 呼び出し上限・エラー率
- Stage 処理時間とキュー滞留状況
- テンプレート/素材のバージョン変化

### 6.2 バックアップ要件
- `data/` 配下の素材・テンプレート・YMM4 プロジェクトを定期バックアップ
- 投稿予約情報と API トークンを暗号化保管

### 6.3 ログ要件
- Stage 切り替えログ、MCP 操作ログ、API レスポンスログ
- 監査目的で素材出典と引用情報を JSON で保存

## 7. 制約事項・リスク

### 7.1 技術的制約
- NotebookLM の利用状況により API/MCP 実装切り替えが必須
- YMM4 API は Windows 環境依存・テンプレート整備が必要
- TikTok API は申請制であり、開発環境でのレート制限が厳しい

### 7.2 法的制約
- 引用元ライセンス遵守、AI 音声の利用規約チェック
- プラットフォームごとの広告・コンプライアンスルール

### 7.3 リスク要因
- **外部API依存**: NotebookLM/Gemini/TTS/YouTube/TikTok 停止時の影響
- **品質リスク**: 自動生成サムネイル・字幕スタイルがブランドガイドと乖離する可能性
- **コストリスク**: TTS/AI API のトークン消費

## 8. 今後の拡張計画

### 8.1 短期（1-2ヶ月）
- ScriptProvider / VoicePipeline の差し替え機構整備
- Slides 画像フォールバックと NotebookLM DeepDive 正規化
- YMM4 テンプレート差分適用プロトタイプ

### 8.2 中期（3-5ヶ月）
- サムネイルテンプレートエンジン、字幕装飾プリセット管理
- 投稿メタデータテンプレート JSON の編集 UI / CLI
- TikTok / Shorts 連携モジュール

### 8.3 長期（6ヶ月以降）
- Web ダッシュボード化 (FastAPI + Frontend)
- クリエイター向けレビュー/承認フロー
- 生成結果の A/B テストと最適化フィードバックループ

### 2.2 補助機能

#### 2.2.1 コンテンツ管理機能
- プロジェクト履歴管理
- 生成ファイルのバージョン管理
- 作業進捗の可視化

#### 2.2.2 品質管理機能
- 音声品質の自動評価
- 台本内容の整合性チェック
- スライドレイアウトの最適化

#### 2.2.3 エラーハンドリング機能
- API制限対応
- ネットワークエラー対応
- ファイル破損対応

## 3. 非機能要件

### 3.1 性能要件
- **処理時間**: 10分の音声に対して30分以内での動画生成
- **同時処理**: 最大3プロジェクトの並行処理
- **ファイルサイズ**: 最大2GBの動画ファイル対応

### 3.2 可用性要件
- **稼働率**: 99%以上
- **復旧時間**: 障害発生から1時間以内

### 3.3 セキュリティ要件
- **API キー管理**: 環境変数による安全な管理
- **ファイル暗号化**: 機密情報を含むファイルの暗号化
- **アクセス制御**: ユーザー認証機能

### 3.4 保守性要件
- **モジュール化**: 各機能の独立性確保
- **ログ管理**: 詳細な処理ログの記録
- **テスト**: 90%以上のテストカバレッジ

## 4. システム構成

### 4.1 アーキテクチャ概要
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   入力層        │    │   処理層        │    │   出力層        │
│                 │    │                 │    │                 │
│ ・URL/トピック  │───▶│ ・NotebookLM    │───▶│ ・動画ファイル  │
│ ・設定パラメータ│    │ ・Google Slide  │    │ ・YouTube URL   │
│                 │    │ ・動画編集      │    │ ・ログファイル  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 4.2 データフロー
1. **入力フェーズ**: ユーザー入力の受付・検証
2. **収集フェーズ**: NotebookLMによるソース収集
3. **生成フェーズ**: 音声・台本・スライドの生成
4. **編集フェーズ**: 動画編集・エフェクト適用
5. **出力フェーズ**: YouTube アップロード・結果通知

### 4.3 外部システム連携
- **NotebookLM**: 音声生成・文字起こし
- **Google Slides**: スライド生成
- **YouTube API**: 動画アップロード
- **外部ニュースサイト**: ソース記事取得

## 5. 技術仕様

### 5.1 開発環境
- **言語**: Python 3.9+
- **フレームワーク**: FastAPI（API サーバー）
- **データベース**: SQLite（開発）/ PostgreSQL（本番）
- **キューシステム**: Celery + Redis

### 5.2 主要ライブラリ
```python
# 動画・音声処理
moviepy==1.0.3
pydub==0.25.1

# 画像処理
Pillow==10.0.0
opencv-python==4.8.0

# API クライアント
google-api-python-client==2.100.0
google-auth-oauthlib==1.0.0

# Web スクレイピング
requests==2.31.0
beautifulsoup4==4.12.2

# 非同期処理
celery==5.3.1
redis==4.6.0

# テスト・品質管理
pytest==7.4.0
black==23.7.0
flake8==6.0.0
mypy==1.5.0
```

### 5.3 API 仕様
#### 5.3.1 メイン処理API
```
POST /api/v1/generate-video
Content-Type: application/json

{
  "topic": "調査トピック",
  "urls": ["https://example.com/news1", "https://example.com/news2"],
  "settings": {
    "max_slides": 20,
    "video_quality": "1080p",
    "subtitle_language": "ja",
    "upload_schedule": "2024-01-01T12:00:00Z"
  }
}
```

#### 5.3.2 進捗確認API
```
GET /api/v1/status/{job_id}

Response:
{
  "job_id": "uuid",
  "status": "processing|completed|failed",
  "progress": 75,
  "current_stage": "video_editing",
  "estimated_completion": "2024-01-01T13:30:00Z"
}
```

## 6. 運用要件

### 6.1 監視要件
- **システム監視**: CPU、メモリ、ディスク使用量
- **API監視**: 外部API の応答時間・エラー率
- **品質監視**: 生成動画の品質指標

### 6.2 バックアップ要件
- **データバックアップ**: 日次自動バックアップ
- **設定バックアップ**: 週次設定ファイルバックアップ
- **復旧手順**: 災害復旧計画書の整備

### 6.3 ログ要件
- **アプリケーションログ**: INFO レベル以上
- **エラーログ**: ERROR レベル以上、詳細スタックトレース
- **監査ログ**: ユーザー操作、API呼び出し履歴

## 7. 制約事項・リスク

### 7.1 技術的制約
- NotebookLM の利用制限（1日あたりの処理回数）
- Google Slides API の制限
- YouTube API のクォータ制限

### 7.2 法的制約
- 著作権法の遵守
- 各プラットフォームの利用規約遵守
- 個人情報保護法の遵守

### 7.3 リスク要因
- **外部API依存**: サービス停止時の影響
- **品質リスク**: AI生成コンテンツの品質ばらつき
- **コスト リスク**: API 利用料金の変動

## 8. 今後の拡張計画

### 8.1 短期計画（3ヶ月以内）
- 基本機能の実装・テスト
- ユーザーインターフェースの構築
- 初期ユーザーでのβテスト

### 8.2 中期計画（6ヶ月以内）
- 多言語対応
- カスタムテンプレート機能
- 高度な動画エフェクト

### 8.3 長期計画（1年以内）
- AI による自動最適化機能
- 他プラットフォーム対応（TikTok、Instagram等）
- エンタープライズ向け機能
