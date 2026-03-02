from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

playwright_sync = pytest.importorskip("playwright.sync_api")


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "src" / "web" / "web_app.py"
SAMPLE_PACKAGE = PROJECT_ROOT / "tests" / "fixtures" / "research" / "sample_package.json"
SAMPLE_SCRIPT = PROJECT_ROOT / "tests" / "fixtures" / "research" / "sample_script.csv"
EXPECTED_CSV = PROJECT_ROOT / "output_csv" / "final_script_rp_playwright_smoke.csv"


def _artifact_dir() -> Path:
    path = Path(os.environ.get("RESEARCH_UI_SMOKE_ARTIFACT_DIR", PROJECT_ROOT / "logs" / "research_ui_smoke"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_streamlit(port: int, timeout: float = 40.0) -> None:
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/?page=research"
    while time.time() < deadline:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(0.5)
    raise TimeoutError(f"Streamlit did not start within {timeout} seconds")


def _wait_for_export_ready(page, timeout: float = 60.0):
    deadline = time.time() + timeout
    export_button = page.get_by_role("button", name="🚀 最終CSVを出力")
    error_text = page.get_by_text("エラーが発生しました")

    while time.time() < deadline:
        if export_button.is_visible():
            return export_button
        if error_text.count() > 0 and error_text.first.is_visible():
            raise AssertionError("Research UI reported an application error")
        page.wait_for_timeout(500)

    raise TimeoutError("Research UI did not become ready for CSV export in time")


def _capture_failure_state(page, artifact_dir: Path) -> None:
    try:
        page.screenshot(path=str(artifact_dir / "research_ui_failure.png"), full_page=True)
        (artifact_dir / "research_ui_failure.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass


@pytest.mark.integration
def test_research_page_smoke_with_playwright():
    port = _find_free_port()
    artifact_dir = _artifact_dir()
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(PROJECT_ROOT), str(PROJECT_ROOT / "src")])
    env["RESEARCH_UI_SMOKE_ARTIFACT_DIR"] = str(artifact_dir)

    if EXPECTED_CSV.exists():
        EXPECTED_CSV.unlink()

    stdout_log = (artifact_dir / "streamlit_stdout.log").open("w", encoding="utf-8")
    stderr_log = (artifact_dir / "streamlit_stderr.log").open("w", encoding="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(APP_PATH),
            "--server.headless=true",
            "--server.port",
            str(port),
        ],
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=stdout_log,
        stderr=stderr_log,
    )

    try:
        _wait_for_streamlit(port)
        base_url = f"http://127.0.0.1:{port}/?page=research"

        with playwright_sync.sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            try:
                page.goto(base_url, wait_until="networkidle")
                page.get_by_role("heading", name="🔍 リサーチ・台本照合").wait_for(timeout=15000)

                file_inputs = page.locator('input[type="file"]')
                assert file_inputs.count() >= 2
                file_inputs.nth(0).set_input_files(str(SAMPLE_PACKAGE))
                file_inputs.nth(1).set_input_files(str(SAMPLE_SCRIPT))

                export_button = _wait_for_export_ready(page)
                export_button.click()
                page.get_by_text("CSVを出力しました").wait_for(timeout=15000)
            except Exception:
                _capture_failure_state(page, artifact_dir)
                raise
            finally:
                browser.close()

        assert EXPECTED_CSV.exists()
        content = EXPECTED_CSV.read_text(encoding="utf-8")
        assert "ナレーター,AI導入率は2026年に42%へ上昇した" in content
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        stdout_log.close()
        stderr_log.close()
