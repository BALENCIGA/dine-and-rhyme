"""フォルダ監視モジュール"""

import shutil
import queue
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from src.analyzer import generate_caption, is_supported_image
from src.confirm import confirm_caption
from src.instagram import post_to_instagram, InstagramPostError, TokenExpiredError


class PhotoHandler(FileSystemEventHandler):
    """新しい画像ファイルをキューに追加するハンドラ。"""

    def __init__(self, file_queue: queue.Queue):
        super().__init__()
        self._queue = file_queue

    def on_created(self, event: FileCreatedEvent) -> None:
        if event.is_directory:
            return
        filepath = Path(event.src_path)
        if is_supported_image(filepath):
            print(f"\n新しい写真を検知: {filepath.name}")
            self._queue.put(filepath)


def process_single_file(filepath: Path, config: dict) -> bool:
    """1枚の写真に対して解析→確認→投稿のパイプラインを実行する。

    Returns:
        True: 投稿成功, False: スキップまたはエラー
    """
    if not filepath.exists():
        print(f"  ファイルが見つかりません: {filepath}")
        return False

    if not is_supported_image(filepath):
        print(f"  非対応のファイル形式です: {filepath.name}")
        return False

    print(f"\n写真を解析中: {filepath.name}")

    while True:
        # キャプション生成
        try:
            caption = generate_caption(filepath, config["anthropic_api_key"])
        except RuntimeError as e:
            print(f"  キャプション生成エラー: {e}")
            return False

        # ユーザー確認
        caption, should_post = confirm_caption(caption, filepath.name)

        if caption == "regenerate" and not should_post:
            print("  キャプションを再生成します...")
            continue

        if not should_post:
            return False

        break

    # Instagram投稿
    try:
        post_id = post_to_instagram(filepath, caption, config)
        print(f"\n  投稿完了！ (ID: {post_id})")

        # 投稿済みフォルダに移動
        dest = config["posted_folder"] / filepath.name
        # 同名ファイルが存在する場合はリネーム
        if dest.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            counter = 1
            while dest.exists():
                dest = config["posted_folder"] / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.move(str(filepath), str(dest))
        print(f"  写真を移動しました: {dest.name}")
        return True

    except TokenExpiredError as e:
        print(f"\n  {e}")
        return False
    except InstagramPostError as e:
        print(f"\n  投稿エラー: {e}")
        print("  写真はinboxに残ります。")
        return False


def start_watching(config: dict) -> None:
    """フォルダ監視を開始する（ブロッキング）。"""
    watch_folder = config["watch_folder"]
    file_queue: queue.Queue[Path] = queue.Queue()

    # 既存ファイルをチェック
    existing = sorted(
        [f for f in watch_folder.iterdir() if is_supported_image(f)],
        key=lambda f: f.stat().st_mtime,
    )
    if existing:
        print(f"\ninboxに {len(existing)} 枚の写真があります。")
        for f in existing:
            file_queue.put(f)

    # ファイル監視を開始
    handler = PhotoHandler(file_queue)
    observer = Observer()
    observer.schedule(handler, str(watch_folder), recursive=False)
    observer.start()

    print(f"\n監視中: {watch_folder}")
    print("写真をフォルダに追加すると自動的に処理されます。")
    print("終了するには Ctrl+C を押してください。\n")

    try:
        while True:
            try:
                filepath = file_queue.get(timeout=1)
                process_single_file(filepath, config)
            except queue.Empty:
                continue
    except KeyboardInterrupt:
        print("\n\n監視を停止します...")
        observer.stop()

    observer.join()
    print("終了しました。")
