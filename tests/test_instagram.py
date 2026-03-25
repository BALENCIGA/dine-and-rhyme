"""instagram.py のテスト"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.instagram import (
    upload_image_to_imgbb,
    create_media_container,
    wait_for_container_ready,
    publish_media,
    post_to_instagram,
    InstagramPostError,
    TokenExpiredError,
)


class TestUploadImageToImgbb:
    @patch("src.instagram.requests.post")
    def test_success(self, mock_post, tmp_path):
        filepath = tmp_path / "test.jpg"
        filepath.write_bytes(b"\xff\xd8\xff\xe0fake_jpeg_data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {"url": "https://i.ibb.co/abc123/test.jpg"},
        }
        mock_post.return_value = mock_response

        url = upload_image_to_imgbb(filepath, "test-key")
        assert url == "https://i.ibb.co/abc123/test.jpg"

    @patch("src.instagram.requests.post")
    def test_failure(self, mock_post, tmp_path):
        filepath = tmp_path / "test.jpg"
        filepath.write_bytes(b"fake_data")

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with pytest.raises(InstagramPostError, match="imgbb アップロード失敗"):
            upload_image_to_imgbb(filepath, "test-key")


class TestCreateMediaContainer:
    @patch("src.instagram.requests.post")
    def test_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "17889615691921648"}
        mock_post.return_value = mock_response

        container_id = create_media_container(
            image_url="https://example.com/img.jpg",
            caption="テスト投稿",
            account_id="123456",
            access_token="token",
        )
        assert container_id == "17889615691921648"

    @patch("src.instagram.requests.post")
    def test_token_expired(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {
                "code": 190,
                "message": "Error validating access token",
            }
        }
        mock_post.return_value = mock_response

        with pytest.raises(TokenExpiredError, match="アクセストークンが期限切れ"):
            create_media_container(
                image_url="https://example.com/img.jpg",
                caption="テスト",
                account_id="123456",
                access_token="expired_token",
            )

    @patch("src.instagram.requests.post")
    def test_rate_limit(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "error": {
                "code": 4,
                "message": "Application request limit reached",
            }
        }
        mock_post.return_value = mock_response

        with pytest.raises(InstagramPostError, match="レート制限"):
            create_media_container(
                image_url="https://example.com/img.jpg",
                caption="テスト",
                account_id="123456",
                access_token="token",
            )


class TestWaitForContainerReady:
    @patch("src.instagram.requests.get")
    def test_immediate_ready(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status_code": "FINISHED"}
        mock_get.return_value = mock_response

        # エラーが発生しなければ成功
        wait_for_container_ready("container_123", "token")

    @patch("src.instagram.requests.get")
    @patch("src.instagram.time.sleep")
    def test_delayed_ready(self, mock_sleep, mock_get):
        mock_in_progress = MagicMock()
        mock_in_progress.json.return_value = {"status_code": "IN_PROGRESS"}

        mock_finished = MagicMock()
        mock_finished.json.return_value = {"status_code": "FINISHED"}

        mock_get.side_effect = [mock_in_progress, mock_in_progress, mock_finished]

        wait_for_container_ready("container_123", "token")
        assert mock_get.call_count == 3

    @patch("src.instagram.requests.get")
    def test_error_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status_code": "ERROR"}
        mock_get.return_value = mock_response

        with pytest.raises(InstagramPostError, match="メディアコンテナ処理エラー"):
            wait_for_container_ready("container_123", "token")


class TestPublishMedia:
    @patch("src.instagram.requests.post")
    def test_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "17889615691921999"}
        mock_post.return_value = mock_response

        post_id = publish_media("container_123", "account_456", "token")
        assert post_id == "17889615691921999"


class TestPostToInstagram:
    @patch("src.instagram.publish_media")
    @patch("src.instagram.wait_for_container_ready")
    @patch("src.instagram.create_media_container")
    @patch("src.instagram.upload_image_to_imgbb")
    def test_full_flow(self, mock_upload, mock_create, mock_wait, mock_publish, tmp_path):
        filepath = tmp_path / "test.jpg"
        filepath.write_bytes(b"fake_data")

        mock_upload.return_value = "https://i.ibb.co/abc/test.jpg"
        mock_create.return_value = "container_123"
        mock_publish.return_value = "post_999"

        config = {
            "imgbb_api_key": "imgbb_key",
            "instagram_account_id": "account_456",
            "meta_access_token": "token",
        }

        post_id = post_to_instagram(filepath, "テストキャプション", config)

        assert post_id == "post_999"
        mock_upload.assert_called_once_with(filepath, "imgbb_key")
        mock_create.assert_called_once_with(
            image_url="https://i.ibb.co/abc/test.jpg",
            caption="テストキャプション",
            account_id="account_456",
            access_token="token",
        )
        mock_wait.assert_called_once_with("container_123", "token")
        mock_publish.assert_called_once_with(
            container_id="container_123",
            account_id="account_456",
            access_token="token",
        )
