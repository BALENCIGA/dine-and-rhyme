"""analyzer.py のテスト"""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.analyzer import (
    generate_caption,
    is_supported_image,
    _load_image_as_base64,
)


class TestIsSupportedImage:
    def test_jpg(self):
        assert is_supported_image(Path("photo.jpg")) is True

    def test_jpeg(self):
        assert is_supported_image(Path("photo.jpeg")) is True

    def test_png(self):
        assert is_supported_image(Path("photo.png")) is True

    def test_webp(self):
        assert is_supported_image(Path("photo.webp")) is True

    def test_heic(self):
        assert is_supported_image(Path("photo.heic")) is True

    def test_uppercase(self):
        assert is_supported_image(Path("photo.JPG")) is True

    def test_unsupported_txt(self):
        assert is_supported_image(Path("notes.txt")) is False

    def test_unsupported_gif(self):
        assert is_supported_image(Path("animation.gif")) is False

    def test_no_extension(self):
        assert is_supported_image(Path("noext")) is False


class TestLoadImageAsBase64:
    def test_jpg_file(self, tmp_path):
        # 最小限のJPEGファイルを作成
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="red")
        filepath = tmp_path / "test.jpg"
        img.save(filepath, format="JPEG")

        b64_data, media_type = _load_image_as_base64(filepath)

        assert media_type == "image/jpeg"
        assert len(b64_data) > 0
        # デコードできることを確認
        decoded = base64.standard_b64decode(b64_data)
        assert len(decoded) > 0

    def test_png_file(self, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="blue")
        filepath = tmp_path / "test.png"
        img.save(filepath, format="PNG")

        b64_data, media_type = _load_image_as_base64(filepath)

        assert media_type == "image/png"
        assert len(b64_data) > 0


class TestGenerateCaption:
    @patch("src.analyzer.anthropic.Anthropic")
    def test_success(self, mock_anthropic_cls, tmp_path):
        from PIL import Image

        img = Image.new("RGB", (10, 10), color="red")
        filepath = tmp_path / "test.jpg"
        img.save(filepath, format="JPEG")

        # モックのレスポンスを設定
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="美味しそうなランチ！\n\n#ランチ #foodstagram")]
        mock_client.messages.create.return_value = mock_response

        caption = generate_caption(filepath, "test-api-key")

        assert caption == "美味しそうなランチ！\n\n#ランチ #foodstagram"
        mock_client.messages.create.assert_called_once()

    @patch("src.analyzer.anthropic.Anthropic")
    def test_retry_on_api_error(self, mock_anthropic_cls, tmp_path):
        from PIL import Image
        import anthropic as anthropic_module

        img = Image.new("RGB", (10, 10), color="red")
        filepath = tmp_path / "test.jpg"
        img.save(filepath, format="JPEG")

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # 1回目はエラー、2回目は成功
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="キャプション")]

        mock_client.messages.create.side_effect = [
            anthropic_module.APIError(
                message="Server error",
                request=MagicMock(),
                body=None,
            ),
            mock_response,
        ]

        with patch("src.analyzer.time.sleep"):
            caption = generate_caption(filepath, "test-api-key")

        assert caption == "キャプション"
        assert mock_client.messages.create.call_count == 2

    @patch("src.analyzer.anthropic.Anthropic")
    def test_max_retries_exceeded(self, mock_anthropic_cls, tmp_path):
        from PIL import Image
        import anthropic as anthropic_module

        img = Image.new("RGB", (10, 10), color="red")
        filepath = tmp_path / "test.jpg"
        img.save(filepath, format="JPEG")

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_client.messages.create.side_effect = anthropic_module.APIError(
            message="Server error",
            request=MagicMock(),
            body=None,
        )

        with patch("src.analyzer.time.sleep"):
            with pytest.raises(RuntimeError, match="3回リトライ後"):
                generate_caption(filepath, "test-api-key")

        assert mock_client.messages.create.call_count == 3
