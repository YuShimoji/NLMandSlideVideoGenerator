#!/usr/bin/env python3
"""
環境セットアップスクリプト
プロジェクトの初期設定と依存関係のインストールを自動化
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

class EnvironmentSetup:
    """環境セットアップクラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.requirements_file = self.project_root / "requirements.txt"
        self.env_example = self.project_root / ".env.example"
        self.env_file = self.project_root / ".env"
        
    def run_setup(self):
        """セットアップ実行"""
        print("🚀 NLMandSlideVideoGenerator 環境セットアップ開始")
        print("=" * 60)
        
        # 1. Python環境確認
        self.check_python_version()
        
        # 2. 必要ディレクトリ作成
        self.create_directories()
        
        # 3. 依存関係インストール
        self.install_dependencies()
        
        # 4. 環境変数ファイル作成
        self.setup_environment_file()
        
        # 5. Gitリポジトリ初期化
        self.setup_git_repository()
        
        # 6. 初期テスト実行
        self.run_initial_tests()
        
        print("\n🎉 セットアップ完了！")
        self.show_next_steps()
    
    def check_python_version(self):
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
    
    def create_directories(self):
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
            "logs",
            "credentials"
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ {dir_path}")
        
        # .gitkeep ファイル作成（空ディレクトリをGitで管理）
        for dir_path in directories:
            gitkeep_path = self.project_root / dir_path / ".gitkeep"
            if not gitkeep_path.exists():
                gitkeep_path.touch()
    
    def install_dependencies(self):
        """依存関係インストール"""
        print("\n📦 依存関係インストール")
        print("-" * 30)
        
        if not self.requirements_file.exists():
            print("❌ requirements.txt が見つかりません")
            return
        
        try:
            # pip アップグレード
            print("🔄 pip をアップグレード中...")
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # 依存関係インストール
            print("📥 パッケージインストール中...")
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)
            ], check=True, capture_output=True, text=True)
            
            print("✅ 依存関係のインストール完了")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ 依存関係インストール失敗: {e}")
            print(f"エラー出力: {e.stderr}")
            
            # 個別インストール試行
            print("🔄 個別パッケージインストールを試行...")
            self.install_packages_individually()
    
    def install_packages_individually(self):
        """個別パッケージインストール"""
        essential_packages = [
            "requests>=2.31.0",
            "google-generativeai>=0.3.0",
            "google-api-python-client>=2.108.0",
            "google-auth-oauthlib>=1.1.0",
            "pillow>=10.0.0",
            "moviepy>=1.0.3",
            "pytest>=7.4.0",
            "python-dotenv>=1.0.0"
        ]
        
        for package in essential_packages:
            try:
                print(f"📦 {package} をインストール中...")
                subprocess.run([sys.executable, "-m", "pip", "install", package], 
                             check=True, capture_output=True)
                print(f"✅ {package}")
            except subprocess.CalledProcessError:
                print(f"⚠️ {package} のインストールに失敗")
    
    def setup_environment_file(self):
        """環境変数ファイルセットアップ"""
        print("\n🔧 環境変数ファイル設定")
        print("-" * 30)
        
        if not self.env_file.exists() and self.env_example.exists():
            # .env.example を .env にコピー
            shutil.copy2(self.env_example, self.env_file)
            print("✅ .env ファイルを作成しました")
            print("💡 .env ファイルを編集してAPI認証情報を設定してください")
        elif self.env_file.exists():
            print("✅ .env ファイルは既に存在します")
        else:
            print("⚠️ .env.example ファイルが見つかりません")
    
    def setup_git_repository(self):
        """Gitリポジトリ初期化"""
        print("\n📝 Git リポジトリ設定")
        print("-" * 30)
        
        try:
            # Git初期化確認
            result = subprocess.run(["git", "status"], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                # Gitリポジトリ初期化
                subprocess.run(["git", "init"], check=True, capture_output=True)
                print("✅ Git リポジトリを初期化しました")
                
                # .gitignore 作成
                self.create_gitignore()
                
                # 初回コミット
                subprocess.run(["git", "add", "."], check=True, capture_output=True)
                subprocess.run(["git", "commit", "-m", "Initial commit: Project setup"], 
                             check=True, capture_output=True)
                print("✅ 初回コミットを作成しました")
            else:
                print("✅ Git リポジトリは既に初期化されています")
                
        except subprocess.CalledProcessError:
            print("⚠️ Git が利用できません（オプション）")
        except FileNotFoundError:
            print("⚠️ Git がインストールされていません（オプション）")
    
    def create_gitignore(self):
        """gitignore ファイル作成"""
        gitignore_content = """# 環境変数
.env
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 仮想環境
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# ログファイル
logs/
*.log

# 一時ファイル
data/temp/
data/output/
*.tmp

# 認証情報
credentials/
*.json
*.p12

# 動画・音声ファイル
*.mp4
*.mp3
*.wav
*.avi
*.mov

# 画像ファイル（大容量）
*.png
*.jpg
*.jpeg
*.gif
*.bmp
*.tiff

# テストカバレッジ
.coverage
htmlcov/

# pytest
.pytest_cache/
"""
        
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(gitignore_content, encoding='utf-8')
            print("✅ .gitignore ファイルを作成しました")
    
    def run_initial_tests(self):
        """初期テスト実行"""
        print("\n🧪 初期テスト実行")
        print("-" * 30)
        
        try:
            # 基本インポートテスト
            test_script = self.project_root / "debug_test.py"
            if test_script.exists():
                result = subprocess.run([sys.executable, str(test_script)], 
                                      capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    print("✅ 基本インポートテスト成功")
                else:
                    print(f"⚠️ 基本テストで警告: {result.stderr}")
            else:
                print("⚠️ テストスクリプトが見つかりません")
                
        except subprocess.TimeoutExpired:
            print("⚠️ テスト実行がタイムアウトしました")
        except Exception as e:
            print(f"⚠️ テスト実行エラー: {e}")
    
    def show_next_steps(self):
        """次のステップ表示"""
        print("\n📋 次のステップ")
        print("=" * 60)
        
        print("1. 🔑 API認証設定")
        print("   - .env ファイルを編集してAPI認証情報を設定")
        print("   - Google AI Studio でGemini APIキーを取得")
        print("   - YouTube API、Google Slides API の OAuth設定")
        print("   - 音声生成API（ElevenLabs、OpenAI等）の設定")
        
        print("\n2. 🧪 API統合テスト実行")
        print("   python test_api_integration.py")
        
        print("\n3. 🎬 デモ実行")
        print("   python test_execution_demo.py")
        
        print("\n4. 📚 ドキュメント確認")
        print("   - docs/api_setup_guide.md")
        print("   - docs/system_specification.md")
        
        print("\n5. 🚀 本格運用開始")
        print("   python main.py --help")
        
        print(f"\n💡 詳細な設定方法は docs/api_setup_guide.md を参照してください")

def main():
    """メイン実行"""
    setup = EnvironmentSetup()
    setup.run_setup()

if __name__ == "__main__":
    main()
