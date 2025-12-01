#!/usr/bin/env python3
"""
運用・監視 API サーバー起動スクリプト
"""
import argparse
import uvicorn
import logging
from pathlib import Path

# プロジェクトルートをパスに追加
import sys
project_root = Path(__file__).parent  # NLMandSlideVideoGenerator/
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from server.api_server import app

def main():
    parser = argparse.ArgumentParser(description="NLMandSlideVideoGenerator Operational API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])

    args = parser.parse_args()

    print("Starting NLMandSlideVideoGenerator Operational API Server")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Reload: {args.reload}")
    print(f"Log Level: {args.log_level}")
    print()
    print("Available endpoints:")
    print("  GET  /health          - Health check")
    print("  GET  /metrics         - Prometheus metrics")
    print("  GET  /status          - System status")
    print("  GET  /jobs            - Active jobs")
    print("  GET  /logs            - System logs")
    print("  GET  /config          - Configuration")
    print("  POST /jobs/{id}/cancel - Cancel job")
    print("  POST /maintenance/cleanup - Cleanup old files")
    print()
    print("OpenAPI docs: http://localhost:8000/docs")
    print()

    uvicorn.run(
        "server.api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level
    )

if __name__ == "__main__":
    main()
