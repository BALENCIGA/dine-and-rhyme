"""Instagram Graph API 投稿モジュール"""

import base64
import time
from pathlib import Path

import requests

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"

# メディアコンテナのステータス確認間隔・最大回数
POLL_INTERVAL = 5  # seconds
MAX_POLL_ATTEMPTS = 24  # 最大2分待機


class InstagramPostError(Exception):
    """Instagram投稿エラー"""


class TokenExpiredError(InstagramPostError):
    """アクセストークン期限切れエラー"""


def upload_image_to_imgbb(filepath: Path, api_key: str) -> str:
    """画像をimgbbにアップロードし、公開URLを返す。"""
    image_data = filepath.read_bytes()
    b64_data = base64.standard_b64encode(image_data).decode("utf-8")

    response = requests.post(
        IMGBB_UPLOAD_URL,
        data={
            "key": api_key,
            "image": b64_data,
        },
        timeout=60,
    )

    if response.status_code != 200:
        raise InstagramPostError(f"imgbb アップロード失敗: {response.status_code} {response.text}")

    data = response.json()
    if not data.get("success"):
        raise InstagramPostError(f"imgbb アップロード失敗: {data}")

    return data["data"]["url"]


def create_media_container(
    image_url: str,
    caption: str,
    account_id: str,
    access_token: str,
) -> str:
    """Instagram Graph API でメディアコンテナを作成し、コンテナIDを返す。"""
    url = f"{GRAPH_API_BASE}/{account_id}/media"
    params = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }

    response = requests.post(url, data=params, timeout=30)
    data = response.json()

    _check_for_errors(data)

    container_id = data.get("id")
    if not container_id:
        raise InstagramPostError(f"メディアコンテナIDが取得できません: {data}")

    return container_id


def wait_for_container_ready(container_id: str, access_token: str) -> None:
    """メディアコンテナのステータスが FINISHED になるまでポーリング。"""
    url = f"{GRAPH_API_BASE}/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": access_token,
    }

    for attempt in range(MAX_POLL_ATTEMPTS):
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        _check_for_errors(data)

        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise InstagramPostError(f"メディアコンテナ処理エラー: {data}")

        time.sleep(POLL_INTERVAL)

    raise InstagramPostError(
        f"メディアコンテナの処理がタイムアウトしました（{MAX_POLL_ATTEMPTS * POLL_INTERVAL}秒）"
    )


def publish_media(container_id: str, account_id: str, access_token: str) -> str:
    """メディアコンテナを公開し、投稿IDを返す。"""
    url = f"{GRAPH_API_BASE}/{account_id}/media_publish"
    params = {
        "creation_id": container_id,
        "access_token": access_token,
    }

    response = requests.post(url, data=params, timeout=30)
    data = response.json()

    _check_for_errors(data)

    post_id = data.get("id")
    if not post_id:
        raise InstagramPostError(f"投稿IDが取得できません: {data}")

    return post_id


def post_to_instagram(
    filepath: Path,
    caption: str,
    config: dict,
) -> str:
    """写真をInstagramに投稿する全フロー。

    1. imgbb にアップロード
    2. メディアコンテナ作成
    3. ステータス確認（ポーリング）
    4. 公開

    Returns:
        投稿ID
    """
    print("  画像をアップロード中...")
    image_url = upload_image_to_imgbb(filepath, config["imgbb_api_key"])
    print(f"  アップロード完了: {image_url}")

    print("  メディアコンテナを作成中...")
    container_id = create_media_container(
        image_url=image_url,
        caption=caption,
        account_id=config["instagram_account_id"],
        access_token=config["meta_access_token"],
    )
    print(f"  コンテナID: {container_id}")

    print("  メディア処理を待機中...")
    wait_for_container_ready(container_id, config["meta_access_token"])

    print("  投稿を公開中...")
    post_id = publish_media(
        container_id=container_id,
        account_id=config["instagram_account_id"],
        access_token=config["meta_access_token"],
    )

    return post_id


def _check_for_errors(data: dict) -> None:
    """API レスポンスのエラーを確認する。"""
    error = data.get("error")
    if not error:
        return

    error_code = error.get("code", 0)
    error_message = error.get("message", "不明なエラー")

    # トークン期限切れ (code 190)
    if error_code == 190:
        raise TokenExpiredError(
            f"アクセストークンが期限切れです。\n"
            f"エラー: {error_message}\n\n"
            f"トークンを更新してください:\n"
            f"1. https://developers.facebook.com/tools/explorer/ にアクセス\n"
            f"2. 新しいアクセストークンを生成\n"
            f"3. 長期トークンに変換\n"
            f"4. .env の META_ACCESS_TOKEN を更新"
        )

    # レート制限 (code 4, 32, etc.)
    if error_code in (4, 32, 17):
        raise InstagramPostError(
            f"APIレート制限に達しました。しばらく待ってから再試行してください。\n"
            f"エラー: {error_message}"
        )

    raise InstagramPostError(f"Instagram API エラー (code={error_code}): {error_message}")
