"""
Test execution logic for web application
"""
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Callable, Optional


async def run_api_tests_async(
    progress_callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    API統合テストを非同期で実行

    Args:
        progress_callback: プログレスコールバック

    Returns:
        テスト結果
    """
    try:
        if progress_callback:
            progress_callback("API統合テストを開始します...")

        # Run the test script
        project_root = Path(__file__).parent.parent.parent
        test_script = project_root / "test_api_integration.py"

        if not test_script.exists():
            raise FileNotFoundError(f"テストスクリプトが見つかりません: {test_script}")

        # Run subprocess
        cmd = [sys.executable, str(test_script)]

        if progress_callback:
            progress_callback("テスト実行中...")

        # For now, run synchronously since the test script is not async
        # In a real implementation, you might want to run this in a thread pool
        import asyncio
        loop = asyncio.get_event_loop()

        def run_test():
            result = subprocess.run(
                cmd,
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            return result

        # Run in thread pool to avoid blocking
        result = await loop.run_in_executor(None, run_test)

        if result.returncode == 0:
            if progress_callback:
                progress_callback("テスト完了")

            # Parse output for results
            # This is a simplified parsing - you might want more sophisticated parsing
            test_results = parse_test_output(result.stdout)
            return {
                "success": True,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "parsed_results": test_results
            }
        else:
            if progress_callback:
                progress_callback("テスト失敗")

            return {
                "success": False,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.stderr
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "テスト実行がタイムアウトしました"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"テスト実行中にエラーが発生しました: {str(e)}"
        }


def parse_test_output(output: str) -> Dict[str, Any]:
    """
    テスト出力を解析して結果を抽出

    Args:
        output: テスト実行出力

    Returns:
        解析結果
    """
    # This is a simplified parser - you might want to implement more sophisticated parsing
    # based on the actual output format of your test script

    results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
        "test_details": []
    }

    lines = output.split('\n')
    for line in lines:
        line = line.strip()
        if '✅' in line and ':' in line:
            results["passed_tests"] += 1
            results["test_details"].append({"name": line.split(':')[0].replace('✅', '').strip(), "status": "passed"})
        elif '❌' in line and ':' in line:
            results["failed_tests"] += 1
            results["test_details"].append({"name": line.split(':')[0].replace('❌', '').strip(), "status": "failed"})
        elif '⏭️' in line and ':' in line:
            results["skipped_tests"] += 1
            results["test_details"].append({"name": line.split(':')[0].replace('⏭️', '').strip(), "status": "skipped"})

    results["total_tests"] = results["passed_tests"] + results["failed_tests"] + results["skipped_tests"]

    return results
