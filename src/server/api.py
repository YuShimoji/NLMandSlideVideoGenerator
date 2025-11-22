"""
FastAPI server exposing NLMandSlideVideoGenerator APIs per OpenSpec v1.1.0
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Path as FPath, Query
from fastapi.responses import JSONResponse

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_PATH))
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings  # noqa: E402
from src.core.pipeline import build_default_pipeline  # noqa: E402

app = FastAPI(title="NLMandSlideVideoGenerator API", version="1.1.0")

# In-memory stores (with persistence)
RUNS: Dict[str, Dict[str, Any]] = {}
ARTIFACTS: Dict[str, Any] = {}
PROGRESS: Dict[str, Dict[str, Any]] = {}

# Persistence paths
RUNS_FILE = PROJECT_ROOT / "data" / "runs.json"
ARTIFACTS_DIR = PROJECT_ROOT / "data" / "artifacts"
RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def _load_persistence():
    """Load persisted runs and artifacts on startup"""
    global RUNS, ARTIFACTS
    if RUNS_FILE.exists():
        try:
            with open(RUNS_FILE, 'r', encoding='utf-8') as f:
                RUNS = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load runs persistence: {e}")
    
    # Load artifacts from files
    for artifact_file in ARTIFACTS_DIR.glob("*.json"):
        try:
            execution_id = artifact_file.stem
            with open(artifact_file, 'r', encoding='utf-8') as f:
                ARTIFACTS[execution_id] = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load artifact {artifact_file}: {e}")

def _save_runs():
    """Persist runs to file"""
    try:
        with open(RUNS_FILE, 'w', encoding='utf-8') as f:
            json.dump(RUNS, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save runs: {e}")

def _save_artifact(execution_id: str, artifact: Any):
    """Persist artifact to file"""
    try:
        artifact_file = ARTIFACTS_DIR / f"{execution_id}.json"
        with open(artifact_file, 'w', encoding='utf-8') as f:
            json.dump(artifact, f, ensure_ascii=False, indent=2, default=_convert)
    except Exception as e:
        print(f"Warning: Failed to save artifact {execution_id}: {e}")

# Load persistence on startup
_load_persistence()

# Serializer helpers

def _convert(obj: Any) -> Any:
    from datetime import datetime as _dt
    if isinstance(obj, _dt):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, tuple):
        return list(obj)
    if is_dataclass(obj):
        return asdict(obj)
    return obj


def _to_dict(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj, default=_convert))
    except Exception:
        try:
            if is_dataclass(obj):
                return json.loads(json.dumps(asdict(obj), default=_convert))
        except Exception:
            return str(obj)


@app.get("/api/v1/spec")
async def get_spec():
    try:
        from api_spec_design import generate_openapi_spec  # type: ignore
        return JSONResponse(content=generate_openapi_spec())
    except Exception as e:
        # Fallback minimal spec
        return JSONResponse(
            content={
                "openapi": "3.0.0",
                "info": {"title": "NLMandSlideVideoGenerator API", "version": "1.1.0"},
                "paths": {
                    "/api/v1/pipeline": {"post": {"summary": "run pipeline", "responses": {"200": {"description": "OK"}}}},
                    "/api/v1/pipeline/{execution_id}/progress": {"get": {"summary": "progress", "responses": {"200": {"description": "OK"}}}},
                },
                "x_warning": f"OpenSpec not available: {str(e)}",
            }
        )


@app.get("/api/v1/settings")
async def get_settings():
    return {
        "pipeline_components": dict(settings.PIPELINE_COMPONENTS),
        "pipeline_stage_modes": dict(settings.PIPELINE_STAGE_MODES),
        "tts_provider": settings.TTS_SETTINGS.get("provider", "none"),
        "youtube_privacy_default": settings.YOUTUBE_SETTINGS.get("privacy_default", "private"),
    }


@app.post("/api/v1/settings")
async def update_settings(payload: Dict[str, Any]):
    # Apply TTS provider
    provider = payload.get("tts_provider")
    if provider:
        settings.TTS_SETTINGS["provider"] = provider
        os.environ["TTS_PROVIDER"] = provider
        # update pipeline voice
        settings.PIPELINE_COMPONENTS["voice_pipeline"] = "tts" if provider != "none" else "legacy"

    # Apply pipeline components
    comps = payload.get("pipeline_components", {})
    if isinstance(comps, dict):
        settings.PIPELINE_COMPONENTS.update(comps)

    # Apply stage modes
    modes = payload.get("pipeline_stage_modes", {})
    if isinstance(modes, dict):
        settings.PIPELINE_STAGE_MODES.update(modes)

    # Apply API keys (runtime only)
    api_keys = payload.get("api_keys", {})
    if isinstance(api_keys, dict):
        if api_keys.get("gemini"):
            settings.GEMINI_API_KEY = api_keys["gemini"]
            os.environ["GEMINI_API_KEY"] = api_keys["gemini"]
        if api_keys.get("openai"):
            settings.OPENAI_API_KEY = api_keys["openai"]
            os.environ["OPENAI_API_KEY"] = api_keys["openai"]
        if api_keys.get("youtube"):
            settings.YOUTUBE_API_KEY = api_keys["youtube"]
            os.environ["YOUTUBE_API_KEY"] = api_keys["youtube"]
        # TTS providers
        eleven = api_keys.get("elevenlabs")
        if eleven:
            settings.TTS_SETTINGS.setdefault("elevenlabs", {})["api_key"] = eleven
            os.environ["ELEVENLABS_API_KEY"] = eleven
        if api_keys.get("azure_speech_key"):
            settings.TTS_SETTINGS.setdefault("azure", {})["key"] = api_keys["azure_speech_key"]
            os.environ["AZURE_SPEECH_KEY"] = api_keys["azure_speech_key"]
        if api_keys.get("azure_speech_region"):
            settings.TTS_SETTINGS.setdefault("azure", {})["region"] = api_keys["azure_speech_region"]
            os.environ["AZURE_SPEECH_REGION"] = api_keys["azure_speech_region"]
        if api_keys.get("google_cloud_tts"):
            settings.TTS_SETTINGS.setdefault("google_cloud", {})["api_key"] = api_keys["google_cloud_tts"]
            os.environ["GOOGLE_CLOUD_TTS_KEY"] = api_keys["google_cloud_tts"]

    return await get_settings()


@app.get("/api/v1/assets/{kind}")
async def list_assets(kind: str = FPath(..., description="audio|videos|slides"), limit: Optional[int] = Query(None)):
    base_map = {
        "audio": settings.AUDIO_DIR,
        "videos": settings.VIDEOS_DIR,
        "slides": settings.SLIDES_DIR,
    }
    if kind not in base_map:
        raise HTTPException(status_code=400, detail="Unsupported kind")
    base = base_map[kind]
    items = []
    if base.exists():
        for p in sorted(base.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.is_file():
                items.append(
                    {
                        "path": str(p),
                        "name": p.name,
                        "size": p.stat().st_size,
                        "modified_at": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
                    }
                )
                if limit and len(items) >= limit:
                    break
    return items


@app.post("/api/v1/test/connections")
async def run_connection_tests():
    results: Dict[str, Dict[str, Any]] = {}

    # Gemini
    try:
        if settings.GEMINI_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-pro")
            _ = model.generate_content("ping")
            results["gemini"] = {"success": True, "message": "ok"}
        else:
            results["gemini"] = {"success": False, "message": "no key"}
    except Exception as e:
        results["gemini"] = {"success": False, "message": str(e)}

    # OpenAI
    try:
        if settings.OPENAI_API_KEY:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            _ = client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": "ping"}], max_tokens=5)
            results["openai"] = {"success": True, "message": "ok"}
        else:
            results["openai"] = {"success": False, "message": "no key"}
    except Exception as e:
        results["openai"] = {"success": False, "message": str(e)}

    # YouTube
    try:
        if settings.YOUTUBE_API_KEY:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=settings.YOUTUBE_API_KEY)
            _ = youtube.search().list(part="snippet", q="test", maxResults=1).execute()
            results["youtube"] = {"success": True, "message": "ok"}
        else:
            results["youtube"] = {"success": False, "message": "no key"}
    except Exception as e:
        results["youtube"] = {"success": False, "message": str(e)}

    # ElevenLabs
    try:
        key = settings.TTS_SETTINGS.get("elevenlabs", {}).get("api_key")
        if key:
            import requests
            r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=10)
            results["elevenlabs"] = {"success": r.status_code == 200, "message": f"HTTP {r.status_code}"}
        else:
            results["elevenlabs"] = {"success": False, "message": "no key"}
    except Exception as e:
        results["elevenlabs"] = {"success": False, "message": str(e)}

    # Azure Speech
    try:
        key = settings.TTS_SETTINGS.get("azure", {}).get("key")
        region = settings.TTS_SETTINGS.get("azure", {}).get("region")
        if key and region:
            try:
                import azure.cognitiveservices.speech as speechsdk  # type: ignore
                _ = speechsdk.SpeechConfig(subscription=key, region=region)
                results["azure"] = {"success": True, "message": "ok"}
            except Exception as e:
                results["azure"] = {"success": True, "message": f"sdk missing or other: {e}"}
        else:
            results["azure"] = {"success": False, "message": "no key/region"}
    except Exception as e:
        results["azure"] = {"success": False, "message": str(e)}

    # Google Cloud TTS (HTTP check)
    try:
        key = settings.TTS_SETTINGS.get("google_cloud", {}).get("api_key")
        if key:
            import requests
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key}"
            data = {
                "input": {"text": "Hello"},
                "voice": {"languageCode": "en-US", "name": "en-US-Neural2-D"},
                "audioConfig": {"audioEncoding": "MP3"},
            }
            r = requests.post(url, json=data, timeout=10)
            results["gcp_tts"] = {"success": r.status_code == 200, "message": f"HTTP {r.status_code}"}
        else:
            results["gcp_tts"] = {"success": False, "message": "no key"}
    except Exception as e:
        results["gcp_tts"] = {"success": False, "message": str(e)}

    return results


@app.post("/api/v1/pipeline")
async def run_pipeline(payload: Dict[str, Any]):
    topic: str = payload.get("topic")
    if not topic:
        raise HTTPException(status_code=400, detail="'topic' is required")
    urls = payload.get("urls") or []
    quality = payload.get("quality") or "1080p"
    editing_backend = payload.get("editing_backend") or settings.PIPELINE_COMPONENTS.get("editing_backend", "moviepy")
    private_upload = payload.get("private_upload", True)
    upload = payload.get("upload", False)  # New: control actual upload

    # Update editing backend temporarily for this run
    old_backend = settings.PIPELINE_COMPONENTS['editing_backend']
    settings.PIPELINE_COMPONENTS['editing_backend'] = editing_backend

    execution_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    PROGRESS[execution_id] = {"stage": "initializing", "progress": 0.0, "message": "starting"}

    def progress_cb(stage: str, progress: float, message: str):
        PROGRESS[execution_id] = {"stage": stage, "progress": progress, "message": message}

    try:
        pipeline = build_default_pipeline()
        result = await pipeline.run(
            topic=topic,
            urls=urls,
            quality=quality,
            private_upload=private_upload,
            upload=upload,  # Pass upload flag
            stage_modes=settings.PIPELINE_STAGE_MODES,
            user_preferences={},
            progress_callback=progress_cb,
        )
        RUNS[execution_id] = {
            "id": execution_id,
            "status": "succeeded" if result.get("success") else "failed",
            "topic": topic,
            "started_at": None,
            "finished_at": datetime.now().isoformat(),
            "youtube_url": result.get("youtube_url"),
            "upload_requested": upload,
        }
        ARTIFACTS[execution_id] = _to_dict(result.get("artifacts"))
        
        # Persist to disk
        _save_runs()
        _save_artifact(execution_id, ARTIFACTS[execution_id])
        
        # Restore backend
        settings.PIPELINE_COMPONENTS['editing_backend'] = old_backend
        
        # Conform to spec: return immediate result
        out = {
            "success": bool(result.get("success")),
            "youtube_url": result.get("youtube_url"),
            "artifacts": ARTIFACTS[execution_id],
        }
        return JSONResponse(content=out)
    except Exception as e:
        settings.PIPELINE_COMPONENTS['editing_backend'] = old_backend
        RUNS[execution_id] = {
            "id": execution_id,
            "status": "failed",
            "topic": topic,
            "started_at": None,
            "finished_at": datetime.now().isoformat(),
            "error": str(e),
            "upload_requested": upload,
        }
        _save_runs()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/pipeline/csv")
async def run_pipeline_csv(payload: Dict[str, Any]):
    """CSVタイムラインモードでパイプラインを実行するエンドポイント

    Request body:
        {
          "csv_path": "...",          # A列=話者, B列=テキスト のCSVパス
          "audio_dir": "...",         # 行ごとの音声ファイル(WAV)ディレクトリ
          "topic": "任意のトピック名", # 省略時はCSVファイル名を使用
          "quality": "1080p",         # 任意。既定は 1080p
          "editing_backend": "moviepy"|"ymm4", # 省略可
          "private_upload": true,      # 任意
          "upload": false              # 実際にアップロードするかどうか
        }
    """

    csv_path = payload.get("csv_path")
    audio_dir = payload.get("audio_dir")
    if not csv_path or not audio_dir:
        raise HTTPException(status_code=400, detail="'csv_path' and 'audio_dir' are required")

    topic = payload.get("topic")
    quality = payload.get("quality") or "1080p"
    editing_backend = payload.get("editing_backend") or settings.PIPELINE_COMPONENTS.get("editing_backend", "moviepy")
    private_upload = payload.get("private_upload", True)
    upload = payload.get("upload", False)

    # 一時的に編集バックエンドを上書き
    old_backend = settings.PIPELINE_COMPONENTS["editing_backend"]
    settings.PIPELINE_COMPONENTS["editing_backend"] = editing_backend

    execution_id = datetime.now().strftime("run_csv_%Y%m%d_%H%M%S")
    PROGRESS[execution_id] = {"stage": "initializing", "progress": 0.0, "message": "starting csv timeline"}

    def progress_cb(stage: str, progress: float, message: str):
        PROGRESS[execution_id] = {"stage": stage, "progress": progress, "message": message}

    from pathlib import Path as _Path

    try:
        pipeline = build_default_pipeline()
        result = await pipeline.run_csv_timeline(
            csv_path=_Path(csv_path),
            audio_dir=_Path(audio_dir),
            topic=topic,
            quality=quality,
            private_upload=private_upload,
            upload=upload,
            stage_modes=settings.PIPELINE_STAGE_MODES,
            user_preferences={},
            progress_callback=progress_cb,
        )

        RUNS[execution_id] = {
            "id": execution_id,
            "status": "succeeded" if result.get("success") else "failed",
            "topic": result.get("artifacts").transcript.title if result.get("artifacts") else topic,
            "started_at": None,
            "finished_at": datetime.now().isoformat(),
            "youtube_url": result.get("youtube_url"),
            "upload_requested": upload,
            "mode": "csv_timeline",
            "csv_path": csv_path,
            "audio_dir": audio_dir,
        }

        ARTIFACTS[execution_id] = _to_dict(result.get("artifacts"))

        _save_runs()
        _save_artifact(execution_id, ARTIFACTS[execution_id])

        settings.PIPELINE_COMPONENTS["editing_backend"] = old_backend

        out = {
            "success": bool(result.get("success")),
            "youtube_url": result.get("youtube_url"),
            "artifacts": ARTIFACTS[execution_id],
        }
        return JSONResponse(content=out)

    except Exception as e:
        settings.PIPELINE_COMPONENTS["editing_backend"] = old_backend
        RUNS[execution_id] = {
            "id": execution_id,
            "status": "failed",
            "topic": topic,
            "started_at": None,
            "finished_at": datetime.now().isoformat(),
            "error": str(e),
            "upload_requested": upload,
            "mode": "csv_timeline",
            "csv_path": csv_path,
            "audio_dir": audio_dir,
        }
        _save_runs()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/pipeline/{execution_id}/progress")
async def get_progress(execution_id: str = FPath(...)):
    if execution_id not in PROGRESS:
        raise HTTPException(status_code=404, detail="execution_id not found")
    return PROGRESS[execution_id]


@app.get("/api/v1/runs")
async def list_runs(limit: Optional[int] = Query(None), status: Optional[str] = Query(None)):
    items = list(RUNS.values())
    if status:
        items = [r for r in items if r.get("status") == status]
    items = sorted(items, key=lambda r: r.get("finished_at") or "")
    if limit:
        items = items[-limit:]
    return items


@app.get("/api/v1/runs/{execution_id}")
async def get_run(execution_id: str = FPath(...)):
    if execution_id not in RUNS:
        raise HTTPException(status_code=404, detail="not found")
    return RUNS[execution_id]


@app.get("/api/v1/runs/{execution_id}/artifacts")
async def get_run_artifacts(execution_id: str = FPath(...)):
    if execution_id not in ARTIFACTS:
        raise HTTPException(status_code=404, detail="not found")
    return ARTIFACTS[execution_id]
