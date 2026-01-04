# Google API セットアップガイド

Google Slides API を使用するための設定手順です。

## 1. Google Cloud Console でプロジェクト作成

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成（または既存プロジェクトを選択）
3. プロジェクト名: `NLMandSlideVideoGenerator` など

## 2. API を有効化

1. 「APIとサービス」→「ライブラリ」
2. 以下のAPIを検索して有効化:
   - **Google Slides API**
   - **Google Drive API**

## 3. OAuth 2.0 認証情報を作成

1. 「APIとサービス」→「認証情報」
2. 「認証情報を作成」→「OAuth クライアント ID」
3. アプリケーションの種類: **デスクトップアプリ**
4. 名前: `NLMandSlide Desktop Client`
5. 「作成」をクリック

## 4. クライアントシークレットをダウンロード

1. 作成した OAuth クライアント ID の右側の「ダウンロード」アイコンをクリック
2. ダウンロードしたファイルを以下の場所に配置:

```text
google_client_secret.json
```

## 5. 初回認証（トークン取得）

以下のスクリプトを実行して OAuth フローを完了します:

```bash
python scripts/google_auth_setup.py
```

ブラウザが開き、Googleアカウントでの認証を求められます。
認証完了後、トークンが `token.json` に保存されます。

## 6. 認証状態の確認

```bash
python scripts/check_environment.py
```

## 必要なPythonパッケージ

```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

## トラブルシューティング

### エラー: "Access blocked: This app's request is invalid"

- OAuth 同意画面の設定が必要です
- 「APIとサービス」→「OAuth 同意画面」で設定

### エラー: "The caller does not have permission"

- APIが有効化されているか確認
- スコープが正しいか確認

### テスト環境での注意

- OAuth 同意画面を「テスト」モードにしている場合、テストユーザーに自分のメールアドレスを追加してください

## 設定ファイルの場所

| ファイル | パス | 説明 |
|---------|------|------|
| クライアントシークレット | `google_client_secret.json` | Google Cloud Console からダウンロード |
| OAuthトークン | `token.json` | 初回認証後に自動生成 |

※ 既定パスは `.env` の `GOOGLE_CLIENT_SECRETS_FILE` / `GOOGLE_OAUTH_TOKEN_FILE` で変更できます。

## フォールバック動作

Google Slides APIの認証ファイルが未設定の場合でも、システムは正常に動作します：

- **モックモード**: API未設定時は`python-pptx`を使用してPPTXファイルを生成
- **エラー回避**: APIなしワークフロー（CSV + WAV → 動画生成）は維持されます
- **段階的有効化**: OAuth認証を設定することで、Google Slides APIの機能を有効化できます

### 動作確認

認証ファイル未設定時でも、以下のコマンドでスライド生成が可能です：

```bash
python scripts/check_environment.py
```

「Google Slides API: 未設定 (モックモードで動作)」と表示されれば、フォールバック動作が有効です。

## 環境変数設定（オプション）

設定ファイルのパスを変更する場合は、`.env`ファイルに以下を追加：

```env
GOOGLE_CLIENT_SECRETS_FILE=path/to/google_client_secret.json
GOOGLE_OAUTH_TOKEN_FILE=path/to/token.json
```

## セキュリティ注意事項

- `google_client_secret.json` と `token.json` は `.gitignore` に追加してください
- これらのファイルをリポジトリにコミットしないでください
