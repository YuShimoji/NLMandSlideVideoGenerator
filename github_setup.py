#!/usr/bin/env python3
"""
GitHub リポジトリ初期化スクリプト
"""
import subprocess
import sys
from pathlib import Path

class GitHubSetup:
    """GitHub リポジトリセットアップクラス"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.project_name = "NLMandSlideVideoGenerator"
        
    def run_setup(self):
        """GitHub セットアップ実行"""
        print("📝 GitHub リポジトリ初期化開始")
        print("=" * 50)
        
        # 1. Git初期化確認
        self.check_git_status()
        
        # 2. 初回コミット作成
        self.create_initial_commit()
        
        # 3. GitHub リポジトリ作成指示
        self.show_github_instructions()
        
        print("\n✅ GitHub セットアップ準備完了！")
    
    def check_git_status(self):
        """Git状態確認"""
        print("\n🔍 Git 状態確認")
        print("-" * 30)
        
        try:
            result = subprocess.run(["git", "status"], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Git リポジトリは初期化済み")
                
                # 変更ファイル確認
                status_output = result.stdout
                if "nothing to commit" not in status_output:
                    print("📝 コミット待ちの変更があります")
                else:
                    print("📝 すべての変更はコミット済み")
            else:
                print("⚠️ Git リポジトリが初期化されていません")
                self.initialize_git()
                
        except FileNotFoundError:
            print("❌ Git がインストールされていません")
            print("💡 https://git-scm.com/ からGitをインストールしてください")
            sys.exit(1)
    
    def initialize_git(self):
        """Git初期化"""
        print("🔄 Git リポジトリを初期化中...")
        
        try:
            subprocess.run(["git", "init"], check=True, capture_output=True)
            print("✅ Git リポジトリを初期化しました")
            
            # デフォルトブランチをmainに設定
            subprocess.run(["git", "branch", "-M", "main"], 
                         check=True, capture_output=True)
            print("✅ デフォルトブランチを main に設定しました")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git初期化失敗: {e}")
    
    def create_initial_commit(self):
        """初回コミット作成"""
        print("\n📦 初回コミット作成")
        print("-" * 30)
        
        try:
            # ステージング
            subprocess.run(["git", "add", "."], check=True, capture_output=True)
            print("✅ ファイルをステージングしました")
            
            # コミット
            commit_message = "feat: Initial commit - YouTube video automation system\n\n" \
                           "- Gemini API integration for script generation\n" \
                           "- Multi-provider TTS integration\n" \
                           "- YouTube API v3 support\n" \
                           "- Google Slides API integration\n" \
                           "- Comprehensive testing framework\n" \
                           "- Automated environment setup"
            
            subprocess.run(["git", "commit", "-m", commit_message], 
                         check=True, capture_output=True)
            print("✅ 初回コミットを作成しました")
            
        except subprocess.CalledProcessError as e:
            print(f"⚠️ コミット作成で問題が発生: {e}")
            print("💡 既にコミット済みの可能性があります")
    
    def show_github_instructions(self):
        """GitHub リポジトリ作成手順表示"""
        print("\n🚀 GitHub リポジトリ作成手順")
        print("=" * 50)
        
        print("1. 📱 GitHub にアクセス")
        print("   https://github.com/new")
        
        print(f"\n2. 📝 リポジトリ情報入力")
        print(f"   Repository name: {self.project_name}")
        print("   Description: YouTube解説動画の自動生成システム")
        print("   Visibility: Public または Private")
        print("   ⚠️ README, .gitignore, license は追加しない（既存）")
        
        print("\n3. 🔗 リモートリポジトリ追加")
        print("   作成後、以下のコマンドを実行:")
        print(f"   git remote add origin https://github.com/USERNAME/{self.project_name}.git")
        print("   git push -u origin main")
        
        print("\n4. 🎯 推奨設定")
        print("   - Issues を有効化")
        print("   - Discussions を有効化")
        print("   - Actions を有効化（CI/CD用）")
        print("   - Branch protection rules 設定")
        
        print("\n💡 GitHub CLI を使用する場合:")
        print(f"   gh repo create {self.project_name} --public --source=. --push")
        print("   または")
        print(f"   gh repo create {self.project_name} --private --source=. --push")

def main():
    """メイン実行"""
    setup = GitHubSetup()
    setup.run_setup()

if __name__ == "__main__":
    main()
