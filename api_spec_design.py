"""
OpenSpec API仕様定義
NLMandSlideVideoGeneratorのAPIインターフェース設計
"""

from openspec import OpenSpec, Schema, Parameter, Response, Operation
from typing import Dict, List, Optional, Any
import json

# API仕様の定義
spec = OpenSpec(
    title="NLMandSlideVideoGenerator API",
    version="1.1.0",
    description="YouTube解説動画自動生成システムのAPI"
)

# スキーマ定義
pipeline_request_schema = Schema(
    type="object",
    properties={
        "topic": {
            "type": "string",
            "description": "動画生成のトピック",
            "example": "AI技術の最新動向"
        },
        "urls": {
            "type": "array",
            "items": {"type": "string", "format": "uri"},
            "description": "参照するソースURLのリスト",
            "example": ["https://example.com/article1", "https://example.com/article2"]
        },
        "quality": {
            "type": "string",
            "enum": ["720p", "1080p", "4K"],
            "default": "1080p",
            "description": "動画品質設定"
        },
        "editing_backend": {
            "type": "string",
            "enum": ["moviepy", "ymm4"],
            "default": "moviepy",
            "description": "動画編集バックエンド"
        },
        "private_upload": {
            "type": "boolean",
            "default": True,
            "description": "YouTube非公開設定"
        }
    },
    required=["topic"]
)

pipeline_response_schema = Schema(
    type="object",
    properties={
        "success": {"type": "boolean"},
        "youtube_url": {"type": "string", "format": "uri"},
        "artifacts": {
            "type": "object",
            "properties": {
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"},
                            "title": {"type": "string"},
                            "relevance_score": {"type": "number"}
                        }
                    }
                },
                "audio": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "duration": {"type": "number"},
                        "quality_score": {"type": "number"}
                    }
                },
                "transcript": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "segments": {"type": "array"}
                    }
                },
                "slides": {
                    "type": "object",
                    "properties": {
                        "total_slides": {"type": "integer"},
                        "presentation_id": {"type": "string"}
                    }
                },
                "video": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "duration": {"type": "number"},
                        "resolution": {"type": "string"}
                    }
                }
            }
        }
    }
)

progress_response_schema = Schema(
    type="object",
    properties={
        "stage": {"type": "string", "description": "現在の処理ステージ"},
        "progress": {"type": "number", "minimum": 0, "maximum": 1, "description": "進捗率(0-1)"},
        "message": {"type": "string", "description": "詳細メッセージ"},
        "estimated_time_remaining": {"type": "number", "description": "推定残り時間(秒)"}
    }
)

# APIエンドポイント定義
pipeline_operation = Operation(
    method="POST",
    path="/api/v1/pipeline",
    summary="動画生成パイプライン実行",
    description="指定されたトピックから完全な動画生成を実行",
    parameters=[
        Parameter(
            name="request",
            in_="body",
            required=True,
            schema=pipeline_request_schema
        )
    ],
    responses={
        "200": Response(
            description="パイプライン実行成功",
            schema=pipeline_response_schema
        ),
        "400": Response(
            description="リクエストパラメータエラー"
        ),
        "500": Response(
            description="内部サーバーエラー"
        )
    }
)

progress_operation = Operation(
    method="GET",
    path="/api/v1/pipeline/{execution_id}/progress",
    summary="実行進捗取得",
    description="指定された実行IDの現在の進捗状況を取得",
    parameters=[
        Parameter(
            name="execution_id",
            in_="path",
            type="string",
            required=True,
            description="実行ID"
        )
    ],
    responses={
        "200": Response(
            description="進捗情報取得成功",
            schema=progress_response_schema
        ),
        "404": Response(
            description="実行IDが見つからない"
        )
    }
)

# 操作を仕様に追加
spec.add_operation(pipeline_operation)
spec.add_operation(progress_operation)

# アセット一覧取得
assets_operation = Operation(
    method="GET",
    path="/api/v1/assets/{kind}",
    summary="アセット一覧取得",
    description="生成済みのアセット（audio/videos/slides）の一覧を取得",
    parameters=[
        Parameter(name="kind", in_="path", type="string", required=True, description="アセット種別", enum=["audio", "videos", "slides"]),
        Parameter(name="limit", in_="query", type="integer", required=False, description="最大取得数")
    ],
    responses={
        "200": Response(description="取得成功", schema=Schema(type="array", items=asset_info_schema))
    }
)
spec.add_operation(assets_operation)

# 設定の取得・更新
get_settings_operation = Operation(
    method="GET",
    path="/api/v1/settings",
    summary="現在の設定取得",
    description="現在有効なシステム設定を取得",
    responses={
        "200": Response(description="取得成功", schema=settings_schema)
    }
)
spec.add_operation(get_settings_operation)

update_settings_operation = Operation(
    method="POST",
    path="/api/v1/settings",
    summary="設定更新",
    description="TTSプロバイダーやパイプライン構成、APIキーを更新",
    parameters=[
        Parameter(name="request", in_="body", required=True, schema=settings_update_schema)
    ],
    responses={
        "200": Response(description="更新成功", schema=settings_schema),
        "400": Response(description="更新内容が不正")
    }
)
spec.add_operation(update_settings_operation)

# 接続テスト
connection_tests_operation = Operation(
    method="POST",
    path="/api/v1/test/connections",
    summary="API接続テストの実行",
    description="設定されているAPIキーで接続テストを実行",
    responses={
        "200": Response(description="テスト結果", schema=connection_tests_response_schema)
    }
)
spec.add_operation(connection_tests_operation)

# 実行履歴
list_runs_operation = Operation(
    method="GET",
    path="/api/v1/runs",
    summary="実行履歴一覧",
    description="過去のパイプライン実行履歴を取得",
    parameters=[
        Parameter(name="limit", in_="query", type="integer", required=False),
        Parameter(name="status", in_="query", type="string", required=False)
    ],
    responses={
        "200": Response(description="取得成功", schema=Schema(type="array", items=run_record_schema))
    }
)
spec.add_operation(list_runs_operation)

get_run_operation = Operation(
    method="GET",
    path="/api/v1/runs/{execution_id}",
    summary="実行詳細取得",
    description="指定された実行IDの詳細を取得",
    parameters=[
        Parameter(name="execution_id", in_="path", type="string", required=True)
    ],
    responses={
        "200": Response(description="取得成功", schema=run_record_schema),
        "404": Response(description="見つからない")
    }
)
spec.add_operation(get_run_operation)

get_run_artifacts_operation = Operation(
    method="GET",
    path="/api/v1/runs/{execution_id}/artifacts",
    summary="実行のアーティファクト取得",
    description="指定された実行の生成物を取得",
    parameters=[
        Parameter(name="execution_id", in_="path", type="string", required=True)
    ],
    responses={
        "200": Response(description="取得成功", schema=Schema(type="object")),
        "404": Response(description="見つからない")
    }
)
spec.add_operation(get_run_artifacts_operation)

# 仕様取得
get_spec_operation = Operation(
    method="GET",
    path="/api/v1/spec",
    summary="OpenAPI仕様の取得",
    description="本システムのOpenAPI仕様を返す",
    responses={
        "200": Response(description="取得成功", schema=Schema(type="object"))
    }
)
spec.add_operation(get_spec_operation)

def generate_openapi_spec():
    """OpenAPI 3.0仕様を生成"""
    return spec.to_dict()

def save_api_spec(filepath: str):
    """API仕様をファイルに保存"""
    spec_dict = generate_openapi_spec()
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(spec_dict, f, indent=2, ensure_ascii=False)
    print(f"API specification saved to {filepath}")

if __name__ == "__main__":
    # API仕様を生成して保存
    save_api_spec("api_specification.json")

    # コンソールに出力
    spec_dict = generate_openapi_spec()
    print(json.dumps(spec_dict, indent=2, ensure_ascii=False))
