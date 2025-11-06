"""
Project initializers for setup
"""
import os
import shutil
from pathlib import Path


def create_directories(project_root: Path):
    """必要ディレクトリ作成"""
    print("\n📁 ディレクトリ構造作成")
    print("-" * 30)

    directories = [
        "data/input",
        "data/output",
        "data/temp",
        "data/audio",
        "data/slides",
        "data/videos",
        "data/transcripts",
        "data/thumbnails",
        "logs",
        "credentials",
        "scripts/output"
    ]

    for dir_path in directories:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ {dir_path}")

    # .gitkeep ファイル作成（空ディレクトリをGitで管理）
    for dir_path in directories:
        gitkeep_path = project_root / dir_path / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.touch()


def setup_environment_file(env_example: Path, env_file: Path):
    """環境変数ファイル作成"""
    print("\n🔧 環境変数ファイル設定")
    print("-" * 30)

    if env_file.exists():
        print("ℹ️ .env ファイルが既に存在します")
        return

    if not env_example.exists():
        print("⚠️ .env.example ファイルが見つからないため、デフォルトの .env ファイルを作成します")
        # デフォルトの環境変数ファイル作成
        default_env_content = """# NLMandSlideVideoGenerator Environment Variables

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# YouTube API
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret

# Other settings
LOG_LEVEL=INFO
DEBUG=false
"""
        env_file.write_text(default_env_content)
        print("✅ デフォルトの .env ファイルを作成しました")
    else:
        # .env.example をコピー
        shutil.copy2(env_example, env_file)
        print("✅ .env.example をコピーして .env ファイルを作成しました")

    print("📝 .env ファイルを編集してAPIキーを設定してください")


def setup_git_repository(project_root: Path):
    """Gitリポジトリ初期化"""
    print("\n📚 Gitリポジトリ初期化")
    print("-" * 30)

    git_dir = project_root / ".git"

    if git_dir.exists():
        print("ℹ️ Gitリポジトリが既に初期化されています")
        return

    try:
        import subprocess
        # Git リポジトリ初期化
        subprocess.run(["git", "init"], cwd=project_root, check=True, capture_output=True)

        # 最初のコミット
        subprocess.run(["git", "add", "."], cwd=project_root, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=project_root, check=True, capture_output=True)

        print("✅ Gitリポジトリを初期化しました")

    except subprocess.CalledProcessError:
        print("⚠️ Gitリポジトリの初期化に失敗しました")
    except FileNotFoundError:
        print("⚠️ Git がインストールされていないため、リポジトリ初期化をスキップします")


def run_initial_tests(project_root: Path):
    """初期テスト実行"""
    print("\n🧪 初期テスト実行")
    print("-" * 30)

    test_files = [
        "test_basic.py",
        "test_connection.py"
    ]

    for test_file in test_files:
        test_path = project_root / test_file
        if test_path.exists():
            try:
                import subprocess
                result = subprocess.run([sys.executable, str(test_path)],
                                      cwd=project_root, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    print(f"✅ {test_file}: 成功")
                else:
                    print(f"❌ {test_file}: 失敗")
                    print(f"   エラー: {result.stderr[:200]}...")

            except subprocess.TimeoutExpired:
                print(f"⏱️ {test_file}: タイムアウト")
            except Exception as e:
                print(f"❌ {test_file}: 実行エラー - {e}")
        else:
            print(f"⚠️ {test_file}: ファイルが見つかりません")
