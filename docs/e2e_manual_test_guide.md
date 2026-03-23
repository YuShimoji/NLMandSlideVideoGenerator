# E2E手動テストガイド (YMM4以降)

Python側E2E dry-runが生成した成果物を使い、YMM4 → MP4 → YouTube公開までを手動確認する手順。

## 前提条件

### 環境
- Windows 11
- YMM4 (ゆっくりMovieMaker 4) インストール済み
- NLMSlidePlugin (ymm4-plugin/) がYMM4にデプロイ済み
  - デプロイ: `.\venv\Scripts\python.exe scripts\deploy_ymm4_plugin.ps1`
- FFprobe (FFmpeg同梱) がPATHに存在
- YouTube Data API v3 OAuth認証済み (SP-038)

### 入力成果物
E2E dry-run実行後の出力フォルダ:
```
output/e2e_dry_run_{timestamp}/
├── manifest.json
├── sources.json
├── script_bundle.json
├── validation.json
├── images/
├── image_credits.txt
└── timeline.csv          <-- YMM4への入力
```

---

## Phase 1: Python側成果物の確認 (5分)

### 1.1 manifest.json
- [ ] 全stageが `"status": "ok"` であること
- [ ] `total_elapsed_s` が記録されていること

### 1.2 script_bundle.json
- [ ] segmentsが存在し、各segmentにspeaker/contentがあること
- [ ] 台本の日本語が自然であること (モックでない場合)
- [ ] セグメント数がtarget_segmentsに近いこと

### 1.3 validation.json
- [ ] `is_ok` が true (またはwarningの理由が妥当)

### 1.4 images/
- [ ] 画像ファイルが存在すること
- [ ] 画像が1920px以上の横長であること
- [ ] トピックと関連のある画像であること

### 1.5 timeline.csv
- [ ] 4列形式: speaker, text, image_path, animation
- [ ] 画像パスが実在するファイルを指していること
- [ ] テキストに話者プレフィックス (Host1:) が重複していないこと

---

## Phase 2: YMM4インポート (10分)

### 2.1 CSVインポート
1. YMM4を起動
2. [ファイル] → [CSVインポート] (NLMSlidePluginメニュー)
3. `timeline.csv` を選択
4. インポート完了を確認

確認項目:
- [ ] 全行がタイムラインに配置されること
- [ ] 各アイテムに話者名が正しく設定されていること
- [ ] 画像パスが正しくImageItemとして配置されること
- [ ] アニメーション種別 (ken_burns/zoom_in/static等) が反映されること

### 2.2 ボイス設定
1. タイムライン上の各テキストアイテムを選択
2. ボイスライブラリが正しく割り当てられていることを確認
   - Host1 → 設定済みのボイス
   - Host2 → 設定済みのボイス

確認項目:
- [ ] 音声プレビューが正常に再生されること
- [ ] 読み上げ速度が自然であること

### 2.3 スタイルテンプレート適用
- [ ] `config/style_template.json` のカラー設定が字幕に反映されていること
- [ ] 背景色、フォントサイズ、ボーダーが設定通りであること

---

## Phase 3: レンダリング → MP4 (15-30分)

### 3.1 レンダリング実行
1. YMM4 [ファイル] → [動画出力]
2. 出力設定:
   - 解像度: 1920x1080
   - フレームレート: 30fps
   - コーデック: H.264
   - 品質: 高
3. 出力先: `output/e2e_dry_run_{timestamp}/final.mp4`
4. レンダリング開始

### 3.2 レンダリング結果確認
- [ ] MP4ファイルが正常に生成されること
- [ ] ファイルサイズが妥当であること (5分動画で50-200MB目安)
- [ ] エラーなくレンダリングが完了すること

---

## Phase 4: MP4品質検証 - SP-039 (5分)

### 4.1 FFprobe自動検証
```bash
.\venv\Scripts\python.exe -c "
from src.core.mp4_quality_checker import MP4QualityChecker
checker = MP4QualityChecker()
result = checker.check('output/e2e_dry_run_{timestamp}/final.mp4')
print(result)
"
```

確認項目 (10項目):
- [ ] 解像度: 1920x1080
- [ ] フレームレート: >= 24fps
- [ ] コーデック: H.264/H.265
- [ ] 音声: AAC
- [ ] サンプルレート: 44100/48000 Hz
- [ ] ビットレート: >= 2Mbps
- [ ] 尺: target_segments * 20秒 前後
- [ ] 破損なし (probe成功)
- [ ] 音声/映像ストリーム両方存在
- [ ] CRITICAL/ERROR なし

### 4.2 手動視聴確認
- [ ] 冒頭5秒を再生し、映像と音声が同期していること
- [ ] 字幕が読みやすいこと
- [ ] 画像切り替えのタイミングが自然であること
- [ ] 音声が途切れないこと
- [ ] 最後まで通しで再生できること

---

## Phase 5: YouTube公開 (SP-038) (10分)

### 5.1 メタデータ準備
```bash
.\venv\Scripts\python.exe -c "
import asyncio
from src.youtube.metadata_generator import MetadataGenerator
gen = MetadataGenerator()
# script_bundle.json を読み込んでメタデータ生成
import json
bundle = json.load(open('output/e2e_dry_run_{timestamp}/script_bundle.json'))
# ... (手順は SP-038 仕様参照)
"
```

確認項目:
- [ ] タイトルが適切であること
- [ ] 説明文にクレジット (image_credits.txt) が含まれること
- [ ] タグが設定されていること
- [ ] サムネイルが生成されていること (任意)

### 5.2 アップロード (非公開)
1. OAuth認証: `.\venv\Scripts\python.exe scripts\google_auth_setup.py`
2. アップロード:
```bash
.\venv\Scripts\python.exe -c "
# YouTube Data API v3 でアップロード
# 初回は必ず 'private' で実施すること
"
```

確認項目:
- [ ] アップロードが正常に完了すること
- [ ] YouTube Studio で動画が非公開として表示されること
- [ ] メタデータ (タイトル/説明/タグ) が正しいこと
- [ ] 動画が正常に再生されること

### 5.3 公開判定
- [ ] 全Phase 1-5 の確認項目がパスしていること
- [ ] 公開設定を 'unlisted' または 'public' に変更

---

## チェックリストサマリー

| Phase | 項目数 | 推定時間 |
|-------|--------|----------|
| 1. Python成果物確認 | 7 | 5分 |
| 2. YMM4インポート | 7 | 10分 |
| 3. レンダリング | 3 | 15-30分 |
| 4. MP4品質検証 | 12 | 5分 |
| 5. YouTube公開 | 7 | 10分 |
| **合計** | **36** | **45-60分** |

## トラブルシューティング

### CSVインポートでエラー
- 画像パスの `\` を `/` に変更してみる
- CSV encoding が UTF-8 (BOMなし) であることを確認

### ボイスが割り当てられない
- YMM4のボイスライブラリが正しくインストールされているか確認
- `config/style_template.json` の speaker_name_colors にHost1/Host2が定義されているか確認

### レンダリングが途中で止まる
- メモリ不足の可能性 → セグメント数を減らしてテスト
- 画像ファイルが破損していないか確認

### FFprobe検証でCRITICAL
- 解像度/コーデック設定をYMM4の出力設定で修正
- 音声なし → ボイス合成が正常に行われたか確認
