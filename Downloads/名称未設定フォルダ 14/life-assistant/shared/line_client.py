"""
LINE Messaging API クライアント
"""
import httpx
from typing import Optional, List, Dict, Any

from .config import Config


class LineClient:
    """LINE Messaging API クライアント"""

    BASE_URL = "https://api.line.me/v2/bot"

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            from .config import get_config
            config = get_config()
        self.config = config
        self._headers = {
            "Authorization": f"Bearer {config.line_channel_access_token}",
            "Content-Type": "application/json"
        }

    async def reply_text(self, reply_token: str, text: str) -> Dict[str, Any]:
        """テキストメッセージを返信"""
        return await self.reply_messages(reply_token, [{"type": "text", "text": text}])

    async def reply_messages(
        self,
        reply_token: str,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """複数メッセージを返信"""
        url = f"{self.BASE_URL}/message/reply"

        # LINEメッセージは最大5件まで
        messages = messages[:5]

        # テキストメッセージは最大5000文字
        for msg in messages:
            if msg.get("type") == "text" and len(msg.get("text", "")) > 5000:
                msg["text"] = msg["text"][:4997] + "..."

        payload = {
            "replyToken": reply_token,
            "messages": messages
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self._headers, json=payload)

            if response.status_code != 200:
                print(f"LINE reply error: {response.status_code} - {response.text}")

            return {"status_code": response.status_code}

    async def push_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """プッシュメッセージを送信"""
        return await self.push_messages(user_id, [{"type": "text", "text": text}])

    async def push_messages(
        self,
        user_id: str,
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """複数プッシュメッセージを送信"""
        url = f"{self.BASE_URL}/message/push"

        # LINEメッセージは最大5件まで
        messages = messages[:5]

        # テキストメッセージは最大5000文字
        for msg in messages:
            if msg.get("type") == "text" and len(msg.get("text", "")) > 5000:
                msg["text"] = msg["text"][:4997] + "..."

        payload = {
            "to": user_id,
            "messages": messages
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self._headers, json=payload)

            if response.status_code != 200:
                print(f"LINE push error: {response.status_code} - {response.text}")

            return {"status_code": response.status_code}

    async def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザープロフィールを取得"""
        url = f"{self.BASE_URL}/profile/{user_id}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers)

            if response.status_code == 200:
                return response.json()
            return None

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """LINE署名を検証"""
        import hashlib
        import hmac
        import base64

        hash_value = hmac.new(
            self.config.line_channel_secret.encode('utf-8'),
            body,
            hashlib.sha256
        ).digest()
        expected_signature = base64.b64encode(hash_value).decode('utf-8')
        return hmac.compare_digest(signature, expected_signature)
