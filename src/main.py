"""エントリーポイント: フォルダ監視モード or 単発投稿モード"""

import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.watcher import start_watching, process_single_file


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Instagram 食事写真 自動投稿ツール",
    )
    subparsers = parser.add_subparsers(dest="command", help="実行モード")

    # watch サブコマンド
    subparsers.add_parser("watch", help="フォルダ監視モード（常駐）")

    # post サブコマンド
    post_parser = subparsers.add_parser("post", help="単発投稿モード")
    post_parser.add_argument("file", type=str, help="投稿する画像ファイルのパス")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config()

    if args.command == "watch":
        start_watching(config)

    elif args.command == "post":
        filepath = Path(args.file).resolve()
        if not filepath.exists():
            print(f"エラー: ファイルが見つかりません: {filepath}", file=sys.stderr)
            sys.exit(1)

        success = process_single_file(filepath, config)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
