"""ターミナル上の確認/編集フローモジュール"""

import os
import subprocess
import tempfile


def confirm_caption(caption: str, filename: str) -> tuple[str, bool]:
    """キャプションをユーザーに確認し、承認/編集/再生成/スキップを選択させる。

    Returns:
        (caption, should_post): 最終キャプションと投稿するかどうか。
        should_post が False で caption が "regenerate" の場合は再生成を要求。
    """
    while True:
        print("\n" + "=" * 60)
        print(f"📷 ファイル: {filename}")
        print("=" * 60)
        print("\n--- 生成されたキャプション ---\n")
        print(caption)
        print("\n--- ここまで ---\n")

        print("[1] このまま投稿する")
        print("[2] キャプションを再生成")
        print("[3] 手動で編集する")
        print("[4] スキップ（投稿しない）")
        print()

        choice = input("選択してください (1-4): ").strip()

        if choice == "1":
            if _final_confirm():
                return caption, True
            # 確認でキャンセルされたらメニューに戻る

        elif choice == "2":
            return "regenerate", False

        elif choice == "3":
            edited = _edit_in_editor(caption)
            if edited is not None:
                caption = edited
                # 編集後、再度メニューを表示して確認
            else:
                print("  編集がキャンセルされました。")

        elif choice == "4":
            print("  スキップしました。")
            return caption, False

        else:
            print("  無効な選択です。1〜4 の数字を入力してください。")


def _final_confirm() -> bool:
    """最終確認プロンプト。"""
    answer = input("本当に投稿しますか？ (y/n): ").strip().lower()
    return answer in ("y", "yes")


def _edit_in_editor(text: str) -> str | None:
    """テキストエディタでキャプションを編集する。

    $EDITOR、vim、nano の順で試行する。
    """
    editor = os.environ.get("EDITOR", "")
    if not editor:
        # vim が利用可能か確認
        for candidate in ("vim", "nano", "vi"):
            try:
                subprocess.run(
                    ["which", candidate],
                    capture_output=True,
                    check=True,
                )
                editor = candidate
                break
            except subprocess.CalledProcessError:
                continue

    if not editor:
        print("  エディタが見つかりません。$EDITOR を設定してください。")
        # フォールバック: インラインで入力
        print("  直接入力してください（空行2つで終了）:")
        return _inline_edit()

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".txt",
        prefix="instagram_caption_",
        delete=False,
    ) as f:
        f.write(text)
        tmpfile = f.name

    try:
        subprocess.run([editor, tmpfile], check=True)
        with open(tmpfile) as f:
            edited = f.read().strip()
        if edited:
            return edited
        return None
    except subprocess.CalledProcessError:
        print("  エディタの実行に失敗しました。")
        return None
    finally:
        os.unlink(tmpfile)


def _inline_edit() -> str | None:
    """フォールバック: ターミナルで直接キャプションを入力する。"""
    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append(line)
        else:
            empty_count = 0
            lines.append(line)

    result = "\n".join(lines).strip()
    return result if result else None
