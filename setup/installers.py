"""
Dependency installers for setup
"""
import sys
import subprocess
from pathlib import Path


def install_dependencies(requirements_file: Path):
    """依存関係インストール"""
    print("\n📦 依存関係インストール")
    print("-" * 30)

    if not requirements_file.exists():
        print("❌ requirements.txt が見つかりません")
        return False

    try:
        # pip アップグレード
        print("🔄 pip をアップグレード中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
                      check=True, capture_output=True)

        # 依存関係インストール
        print("📦 Python パッケージをインストール中...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                      check=True)

        print("✅ 依存関係インストール完了")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 依存関係インストール失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")
        return False


def install_system_dependencies():
    """システム依存関係インストール（オプション）"""
    print("\n🔧 システム依存関係確認")
    print("-" * 30)

    # Windows 用のシステム依存関係チェック
    system_deps = ["ffmpeg", "git"]
    missing_deps = []

    for dep in system_deps:
        if not shutil.which(dep):
            missing_deps.append(dep)

    if missing_deps:
        print(f"⚠️ 以下のシステム依存関係が見つかりません: {', '.join(missing_deps)}")
        print("手動でインストールしてください:")
        for dep in missing_deps:
            if dep == "ffmpeg":
                print("  - FFmpeg: https://ffmpeg.org/download.html")
            elif dep == "git":
                print("  - Git: https://git-scm.com/downloads")
    else:
        print("✅ システム依存関係が利用可能です")
