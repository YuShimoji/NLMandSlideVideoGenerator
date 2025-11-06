"""
Environment checkers for setup
"""
import sys
import subprocess
import shutil


def check_python_version():
    """Python バージョン確認"""
    print("\n🐍 Python環境確認")
    print("-" * 30)

    version = sys.version_info
    print(f"Python バージョン: {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8以上が必要です")
        sys.exit(1)
    else:
        print("✅ Python バージョン要件を満たしています")


def check_git_availability():
    """Git の利用可能性確認"""
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git が利用可能です")
            return True
        else:
            print("⚠️ Git が利用できません")
            return False
    except FileNotFoundError:
        print("⚠️ Git がインストールされていません")
        return False


def check_pip_availability():
    """pip の利用可能性確認"""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ pip が利用可能です")
            return True
        else:
            print("⚠️ pip が利用できません")
            return False
    except Exception:
        print("⚠️ pip が利用できません")
        return False
