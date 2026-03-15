"""
設定管理モジュール
Secret ManagerとEnv Varsから設定を取得
"""
import os
from functools import lru_cache
from typing import Optional


class Config:
    """設定クラス"""

    def __init__(self):
        self._secrets_client = None
        self._project_id = os.environ.get('GCP_PROJECT_ID')
        self._use_secret_manager = os.environ.get('USE_SECRET_MANAGER', 'true').lower() == 'true'

    @property
    def secrets_client(self):
        """Secret Managerクライアントを遅延初期化"""
        if self._secrets_client is None and self._use_secret_manager:
            try:
                from google.cloud import secretmanager
                self._secrets_client = secretmanager.SecretManagerServiceClient()
            except Exception as e:
                print(f"Warning: Could not initialize Secret Manager client: {e}")
                self._use_secret_manager = False
        return self._secrets_client

    @lru_cache(maxsize=10)
    def _get_secret(self, secret_id: str) -> str:
        """Secret Managerからシークレットを取得（キャッシュ付き）"""
        # ローカル開発時は環境変数から取得
        env_value = os.environ.get(secret_id)
        if env_value:
            return env_value

        # Secret Managerが無効または利用不可の場合
        if not self._use_secret_manager or not self.secrets_client:
            raise ValueError(f"Secret {secret_id} not found in environment variables")

        # 本番環境ではSecret Managerから取得
        try:
            name = f"projects/{self._project_id}/secrets/{secret_id}/versions/latest"
            response = self.secrets_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            raise ValueError(f"Failed to get secret {secret_id}: {e}")

    @property
    def line_channel_secret(self) -> str:
        """LINEチャネルシークレット"""
        return self._get_secret('LINE_CHANNEL_SECRET')

    @property
    def line_channel_access_token(self) -> str:
        """LINEチャネルアクセストークン"""
        return self._get_secret('LINE_CHANNEL_ACCESS_TOKEN')

    @property
    def github_token(self) -> str:
        """GitHub Personal Access Token"""
        return self._get_secret('GITHUB_TOKEN')

    @property
    def github_repo(self) -> str:
        """GitHubリポジトリ（username/repo形式）"""
        return os.environ.get('GITHUB_REPO', 'username/life-log')

    @property
    def anthropic_api_key(self) -> str:
        """Anthropic APIキー"""
        return self._get_secret('ANTHROPIC_API_KEY')

    @property
    def claude_model(self) -> str:
        """使用するClaudeモデル"""
        return os.environ.get('CLAUDE_MODEL', 'claude-sonnet-4-20250514')

    @property
    def gcp_project_id(self) -> Optional[str]:
        """GCPプロジェクトID"""
        return self._project_id


# シングルトンインスタンス
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """設定のシングルトンインスタンスを取得"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
