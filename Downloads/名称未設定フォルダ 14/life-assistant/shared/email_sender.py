"""
ファイル共有モジュール
Cloud Storageを使用してファイルを保存し、ダウンロードリンクを生成
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from google.cloud import storage

from .config import Config


class FileSharer:
    """Cloud Storageを使用したファイル共有"""

    JST = timezone(timedelta(hours=9))

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            from .config import get_config
            config = get_config()
        self.config = config
        self._storage_client = None
        self._bucket_name = f"{config.gcp_project_id}-slides"

    @property
    def storage_client(self):
        """Storageクライアントを遅延初期化"""
        if self._storage_client is None:
            self._storage_client = storage.Client()
        return self._storage_client

    def _ensure_bucket_exists(self):
        """バケットが存在しない場合は作成"""
        try:
            bucket = self.storage_client.bucket(self._bucket_name)
            if not bucket.exists():
                bucket = self.storage_client.create_bucket(
                    self._bucket_name,
                    location="asia-northeast1"
                )
                # ライフサイクルルール設定（30日後に自動削除）
                bucket.add_lifecycle_delete_rule(age=30)
                bucket.patch()
            return bucket
        except Exception as e:
            print(f"Bucket error: {e}")
            raise

    async def upload_and_get_link(
        self,
        data: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        expiration_hours: int = 24
    ) -> Dict[str, Any]:
        """
        ファイルをアップロードして署名付きURLを取得

        Args:
            data: ファイルデータ
            filename: ファイル名
            content_type: MIMEタイプ
            expiration_hours: URLの有効期限（時間）

        Returns:
            {
                "success": bool,
                "url": "署名付きURL",
                "filename": "ファイル名",
                "expires_at": "有効期限"
            }
        """
        try:
            bucket = self._ensure_bucket_exists()

            # ユニークなファイル名を生成
            unique_id = str(uuid.uuid4())[:8]
            timestamp = datetime.now(self.JST).strftime("%Y%m%d_%H%M%S")
            blob_name = f"slides/{timestamp}_{unique_id}_{filename}"

            blob = bucket.blob(blob_name)
            blob.upload_from_string(data, content_type=content_type)

            # 署名付きURL生成
            expiration = timedelta(hours=expiration_hours)
            url = blob.generate_signed_url(
                expiration=expiration,
                method="GET",
                response_disposition=f'attachment; filename="{filename}"'
            )

            expires_at = datetime.now(self.JST) + expiration

            return {
                "success": True,
                "url": url,
                "filename": filename,
                "expires_at": expires_at.isoformat()
            }

        except Exception as e:
            print(f"Upload error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def upload_slides(
        self,
        pptx_data: bytes,
        meeting_title: str
    ) -> Dict[str, Any]:
        """
        会議スライドをアップロード

        Args:
            pptx_data: PPTXファイルのバイトデータ
            meeting_title: 会議タイトル

        Returns:
            アップロード結果
        """
        # ファイル名をサニタイズ
        safe_title = "".join(c for c in meeting_title if c.isalnum() or c in "._- ").strip()
        if not safe_title:
            safe_title = "meeting"

        filename = f"{safe_title}_議事録.pptx"

        return await self.upload_and_get_link(
            data=pptx_data,
            filename=filename,
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            expiration_hours=72  # 3日間有効
        )
