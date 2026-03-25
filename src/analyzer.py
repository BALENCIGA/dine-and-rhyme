"""Claude API で食事写真を解析しキャプションを生成するモジュール"""

import base64
import io
import time
from pathlib import Path

import anthropic
from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic"}

CAPTION_PROMPT = """\
あなたは食事の写真からInstagramの投稿文を作成するアシスタントです。

以下のルールに従って投稿文を作成してください：
- 文体: カジュアルで友達に話しかけるような口調（「〜だよ」「〜めっちゃ」「〜最高！」など）
- 本文: 日本語で3〜5行程度。料理の見た目、味の想像、シチュエーションなどを含む
- 絵文字: 適度に使用（多すぎない）
- ハッシュタグ: 日本語5〜8個 + 英語3〜5個（本文の後に改行2つ空けて配置）
- ハッシュタグの例: #ランチ #東京グルメ #foodstagram #japanesefood

写真の内容を分析して投稿文を作成してください。
投稿文のみを出力してください。余計な説明や前置きは不要です。"""

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def is_supported_image(filepath: Path) -> bool:
    """対応する画像ファイルかどうか判定する。"""
    return filepath.suffix.lower() in SUPPORTED_EXTENSIONS


def _load_image_as_base64(filepath: Path) -> tuple[str, str]:
    """画像を読み込み、base64エンコードとメディアタイプを返す。

    HEIC画像はJPEGに変換する。
    """
    suffix = filepath.suffix.lower()

    if suffix == ".heic":
        # HEIC → JPEG変換
        img = Image.open(filepath)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=90)
        image_data = buffer.getvalue()
        media_type = "image/jpeg"
    else:
        image_data = filepath.read_bytes()
        media_type_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        media_type = media_type_map.get(suffix, "image/jpeg")

    return base64.standard_b64encode(image_data).decode("utf-8"), media_type


def generate_caption(filepath: Path, api_key: str) -> str:
    """食事写真を解析してInstagram用キャプションを生成する。

    リトライ付き（最大3回）。
    """
    image_b64, media_type = _load_image_as_base64(filepath)
    client = anthropic.Anthropic(api_key=api_key)

    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_b64,
                                },
                            },
                            {
                                "type": "text",
                                "text": CAPTION_PROMPT,
                            },
                        ],
                    }
                ],
            )
            return response.content[0].text

        except anthropic.APIError as e:
            if attempt < MAX_RETRIES - 1:
                print(f"  Claude API エラー（リトライ {attempt + 1}/{MAX_RETRIES}）: {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                raise RuntimeError(f"Claude API エラー（{MAX_RETRIES}回リトライ後）: {e}") from e
