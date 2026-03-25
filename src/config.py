"""設定読み込みモジュール"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def load_config() -> dict:
    """環境変数を読み込み、バリデーションして設定辞書を返す。"""
    # プロジェクトルートの .env を読み込み
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    required_vars = [
        "ANTHROPIC_API_KEY",
        "INSTAGRAM_BUSINESS_ACCOUNT_ID",
        "META_ACCESS_TOKEN",
        "IMGBB_API_KEY",
    ]

    missing = [v for v in required_vars if not os.getenv(v)]
    if missing:
        print(f"エラー: 以下の環境変数が設定されていません: {', '.join(missing)}", file=sys.stderr)
        print("`.env` ファイルを作成し、必要な値を設定してください。", file=sys.stderr)
        print("テンプレート: .env.example", file=sys.stderr)
        sys.exit(1)

    watch_folder = Path(os.getenv("WATCH_FOLDER", "./photos/inbox"))
    posted_folder = Path(os.getenv("POSTED_FOLDER", "./photos/posted"))

    # 相対パスの場合はプロジェクトルート基準に解決
    if not watch_folder.is_absolute():
        watch_folder = project_root / watch_folder
    if not posted_folder.is_absolute():
        posted_folder = project_root / posted_folder

    # フォルダが存在しなければ作成
    watch_folder.mkdir(parents=True, exist_ok=True)
    posted_folder.mkdir(parents=True, exist_ok=True)

    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "instagram_account_id": os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID"),
        "meta_access_token": os.getenv("META_ACCESS_TOKEN"),
        "imgbb_api_key": os.getenv("IMGBB_API_KEY"),
        "watch_folder": watch_folder,
        "posted_folder": posted_folder,
    }
