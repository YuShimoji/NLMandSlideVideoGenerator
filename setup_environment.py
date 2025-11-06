#!/usr/bin/env python3
"""
環境セットアップスクリプト
プロジェクトの初期設定と依存関係のインストールを自動化
"""
import sys
from pathlib import Path

# setup モジュールをパスに追加
setup_dir = Path(__file__).parent / "setup"
sys.path.insert(0, str(setup_dir))

from setup.checkers import check_python_version, check_git_availability, check_pip_availability
from setup.installers import install_dependencies, install_system_dependencies
from setup.initializers import (
    create_directories,
    setup_environment_file,
    setup_git_repository,
    run_initial_tests,
)


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
        check_python_version()

        # 2. システム依存関係確認
        check_git_availability()
        check_pip_availability()
        install_system_dependencies()

        # 3. 必要ディレクトリ作成
        create_directories(self.project_root)

        # 4. 依存関係インストール
        install_dependencies(self.requirements_file)

        # 5. 環境変数ファイル作成
        setup_environment_file(self.env_example, self.env_file)

        # 6. Gitリポジトリ初期化
        setup_git_repository(self.project_root)

        # 7. 初期テスト実行
        run_initial_tests(self.project_root)

        print("\n🎉 セットアップ完了！")
        self.show_next_steps()

    def show_next_steps(self):
        """次のステップを表示"""
        print("\n📋 次のステップ:")
        print("  1. .env ファイルを編集してAPIキーを設定")
        print("  2. python test_basic.py を実行して基本機能をテスト")
        print("  3. python run_web_app.py を実行してWeb UIを起動")
        print("  4. ドキュメント (README.md) を参照して詳細な使用方法を確認")
        print("\n💡 サポート: issues を作成するか、ドキュメントを確認してください")


def main():
    """メイン実行関数"""
    setup = EnvironmentSetup()
    try:
        setup.run_setup()
    except KeyboardInterrupt:
        print("\n\n⚠️ セットアップが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ セットアップ中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
