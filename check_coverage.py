#!/usr/bin/env python3
"""Coverage check script"""

import subprocess
import sys
import os

def run_coverage():
    """Run pytest with coverage"""
    try:
        # カバレッジレポート生成
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            '--cov=src',
            '--cov-report=term-missing',
            'tests/'
        ], capture_output=True, text=True, cwd=os.getcwd())

        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
        print("Return code:", result.returncode)

    except Exception as e:
        print(f"Error running coverage: {e}")

if __name__ == "__main__":
    run_coverage()
