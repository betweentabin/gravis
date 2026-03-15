"""
メッセージ分類モジュール
Claude APIを使用してメッセージを自動分類
"""
from typing import Optional, Dict, Any

from .config import Config
from .claude_client import ClaudeClient


class MessageClassifier:
    """メッセージ分類器"""

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            from .config import get_config
            config = get_config()
        self.config = config
        self.claude_client = ClaudeClient(config)

    def classify(self, message: str) -> Dict[str, Any]:
        """
        メッセージを分類

        Returns:
            {
                "category": "diary|learning|idea|task",
                "confidence": 0.0-1.0,
                "tags": ["tag1", "tag2"],
                "summary": "要約",
                "extracted_data": {...}
            }
        """
        return self.claude_client.classify_message(message)

    def analyze(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        コンテンツを分析

        Args:
            content: 分析するコンテンツ
            content_type: diary, learning, idea, task のいずれか

        Returns:
            分析結果（カテゴリ固有のデータ）
        """
        return self.claude_client.analyze_content(content, content_type)

    def extract_title(self, content: str, content_type: str) -> str:
        """
        コンテンツからタイトルを抽出

        Args:
            content: コンテンツ
            content_type: カテゴリ

        Returns:
            タイトル文字列
        """
        # 最初の行または最初の20文字をタイトルとして使用
        lines = content.strip().split('\n')
        first_line = lines[0] if lines else content

        # 長すぎる場合は切り詰め
        if len(first_line) > 50:
            first_line = first_line[:47] + "..."

        return first_line

    def suggest_tags(self, content: str, existing_tags: list = None) -> list:
        """
        コンテンツに基づいてタグを提案

        Args:
            content: コンテンツ
            existing_tags: 既存のタグリスト（重複を避けるため）

        Returns:
            提案されたタグのリスト
        """
        if existing_tags is None:
            existing_tags = []

        # 分類結果からタグを取得
        result = self.classify(content)
        suggested = result.get("tags", [])

        # 既存タグと重複を除外
        return [tag for tag in suggested if tag not in existing_tags]
