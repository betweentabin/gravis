"""
GitHub API クライアント
GitHubリポジトリへのファイル操作を行う
"""
import base64
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import httpx

from .config import Config


class GitHubClient:
    """GitHub API クライアント"""

    BASE_URL = "https://api.github.com"
    JST = timezone(timedelta(hours=9))

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            from .config import get_config
            config = get_config()
        self.config = config
        self.repo = config.github_repo
        self._headers = {
            "Authorization": f"Bearer {config.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }

    async def create_or_update_file(
        self,
        path: str,
        content: str,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """ファイルを作成または更新"""
        if message is None:
            message = f"Add/Update {path}"

        url = f"{self.BASE_URL}/repos/{self.repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            # 既存ファイルのSHAを取得（更新の場合に必要）
            sha = await self._get_file_sha(path)

            data = {
                "message": message,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": "main"
            }

            if sha:
                data["sha"] = sha

            response = await client.put(url, headers=self._headers, json=data, timeout=30.0)
            response.raise_for_status()

            return response.json()

    async def _get_file_sha(self, path: str) -> Optional[str]:
        """ファイルのSHAを取得"""
        url = f"{self.BASE_URL}/repos/{self.repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers, timeout=30.0)

            if response.status_code == 200:
                return response.json().get("sha")
            return None

    async def get_file_content(self, path: str) -> Optional[str]:
        """ファイルの内容を取得"""
        url = f"{self.BASE_URL}/repos/{self.repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers, timeout=30.0)

            if response.status_code == 200:
                content = response.json().get("content", "")
                return base64.b64decode(content).decode()
            return None

    async def list_files(self, path: str) -> List[Dict[str, Any]]:
        """ディレクトリ内のファイル一覧を取得"""
        url = f"{self.BASE_URL}/repos/{self.repo}/contents/{path}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self._headers, timeout=30.0)

            if response.status_code == 200:
                result = response.json()
                # 単一ファイルの場合はリストに変換
                if isinstance(result, dict):
                    return [result]
                return result
            return []

    async def delete_file(self, path: str, message: Optional[str] = None) -> bool:
        """ファイルを削除"""
        if message is None:
            message = f"Delete {path}"

        url = f"{self.BASE_URL}/repos/{self.repo}/contents/{path}"
        sha = await self._get_file_sha(path)

        if not sha:
            return False

        async with httpx.AsyncClient() as client:
            response = await client.request(
                "DELETE",
                url,
                headers=self._headers,
                json={
                    "message": message,
                    "sha": sha,
                    "branch": "main"
                },
                timeout=30.0
            )
            return response.status_code == 200

    async def get_index(self) -> Dict[str, Any]:
        """インデックスを取得"""
        content = await self.get_file_content(".metadata/index.json")
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return {"version": "1.0.0", "entries": [], "total_entries": 0, "last_updated": None}

    async def update_index(self, entry: Dict[str, Any]) -> None:
        """インデックスに新しいエントリを追加"""
        index = await self.get_index()

        # 新しいエントリを追加
        index["entries"].append(entry)
        index["total_entries"] = len(index["entries"])
        index["last_updated"] = datetime.now(self.JST).isoformat()

        # インデックスを保存
        await self.create_or_update_file(
            ".metadata/index.json",
            json.dumps(index, ensure_ascii=False, indent=2),
            f"Update index: add {entry.get('id', 'entry')}"
        )

    async def complete_task(self, task_name: str) -> bool:
        """タスクを完了にする"""
        # アクティブタスクから検索
        files = await self.list_files("tasks/active")

        for file_info in files:
            if not isinstance(file_info, dict):
                continue
            if file_info.get("type") != "file":
                continue
            if task_name.lower() not in file_info.get("name", "").lower():
                continue

            # ファイル内容を取得
            content = await self.get_file_content(file_info["path"])
            if not content:
                continue

            # ステータスを更新
            content = content.replace("status: in_progress", "status: completed")
            content = content.replace("status: pending", "status: completed")

            # 完了日時を追加
            now = datetime.now(self.JST).isoformat()
            content = content.replace("completed_at: null", f"completed_at: {now}")

            # 完了フォルダのパスを生成
            year = datetime.now(self.JST).strftime("%Y")
            month = datetime.now(self.JST).strftime("%m")
            filename = file_info["name"]
            new_path = f"tasks/completed/{year}/{month}/{filename}"

            # 完了フォルダに保存
            await self.create_or_update_file(
                new_path,
                content,
                f"Complete task: {task_name}"
            )

            # 古いファイルを削除
            await self.delete_file(file_info["path"], f"Move completed task: {task_name}")

            return True

        return False

    async def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        index = await self.get_index()
        entries = index.get("entries", [])

        now = datetime.now(self.JST)
        week_ago = now - timedelta(days=7)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        stats = {
            "total": len(entries),
            "diary": 0,
            "learning": 0,
            "ideas": 0,
            "tasks": 0,
            "tasks_completed": 0,
            "this_week": 0,
            "this_month": 0,
            "top_tags": []
        }

        tag_counts: Dict[str, int] = {}

        for entry in entries:
            entry_type = entry.get("type")
            if entry_type == "diary":
                stats["diary"] += 1
            elif entry_type == "learning":
                stats["learning"] += 1
            elif entry_type == "idea":
                stats["ideas"] += 1
            elif entry_type == "task":
                stats["tasks"] += 1
                if entry.get("status") == "completed":
                    stats["tasks_completed"] += 1

            # 期間別カウント
            created_at_str = entry.get("created_at", "")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str)
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=self.JST)
                    if created_at >= week_ago:
                        stats["this_week"] += 1
                    if created_at >= month_start:
                        stats["this_month"] += 1
                except (ValueError, TypeError):
                    pass

            # タグカウント
            for tag in entry.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # トップタグ（使用回数順）
        stats["top_tags"] = sorted(tag_counts.keys(), key=lambda t: tag_counts[t], reverse=True)

        return stats

    async def search_entries(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """エントリを検索"""
        index = await self.get_index()
        results = []
        query_lower = query.lower()

        for entry in index.get("entries", []):
            # ID、タグ、タイプで検索
            searchable = f"{entry.get('id', '')} {' '.join(entry.get('tags', []))} {entry.get('type', '')}".lower()
            if query_lower in searchable:
                results.append({
                    "type": entry.get("type"),
                    "title": entry.get("id"),
                    "date": entry.get("date"),
                    "path": entry.get("path"),
                    "tags": entry.get("tags", [])
                })

        return results[:limit]

    async def get_entries_for_period(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """指定期間のエントリを取得"""
        index = await self.get_index()
        entries = []

        for entry in index.get("entries", []):
            created_at_str = entry.get("created_at", "")
            if not created_at_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=self.JST)

                if start_date <= created_at <= end_date:
                    entries.append(entry)
            except (ValueError, TypeError):
                continue

        return entries

    async def get_latest_weekly_review(self) -> Optional[str]:
        """最新の週次レビューを取得"""
        now = datetime.now(self.JST)
        year = now.year
        week = now.isocalendar()[1]

        # 今週のレビューを試す
        path = f"reviews/weekly/{year}/{year}-W{week:02d}.md"
        content = await self.get_file_content(path)
        if content:
            return content

        # 先週のレビューを試す
        week -= 1
        if week < 1:
            year -= 1
            week = 52
        path = f"reviews/weekly/{year}/{year}-W{week:02d}.md"
        return await self.get_file_content(path)

    async def get_latest_monthly_review(self) -> Optional[str]:
        """最新の月次レビューを取得"""
        now = datetime.now(self.JST)
        year = now.year
        month = now.month

        # 今月のレビューを試す
        path = f"reviews/monthly/{year}/{year}-{month:02d}.md"
        content = await self.get_file_content(path)
        if content:
            return content

        # 先月のレビューを試す
        month -= 1
        if month < 1:
            year -= 1
            month = 12
        path = f"reviews/monthly/{year}/{year}-{month:02d}.md"
        return await self.get_file_content(path)

    async def get_user_config(self) -> Dict[str, Any]:
        """ユーザー設定を取得"""
        content = await self.get_file_content(".metadata/user_config.json")
        if content:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass
        return {
            "version": "1.0.0",
            "line_user_id": "",
            "timezone": "Asia/Tokyo",
            "notifications": {
                "weekly_review": True,
                "monthly_review": True
            }
        }

    async def update_user_config(self, updates: Dict[str, Any]) -> None:
        """ユーザー設定を更新"""
        config = await self.get_user_config()
        config.update(updates)
        config["last_updated"] = datetime.now(self.JST).isoformat()

        await self.create_or_update_file(
            ".metadata/user_config.json",
            json.dumps(config, ensure_ascii=False, indent=2),
            "Update user config"
        )

    async def get_recent_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """最近のエントリを取得"""
        index = await self.get_index()
        entries = index.get("entries", [])

        # 作成日時でソート（新しい順）
        sorted_entries = sorted(
            entries,
            key=lambda e: e.get("created_at", ""),
            reverse=True
        )

        return sorted_entries[:limit]

    async def save_economic_indicator(self, indicator_data: Dict[str, Any]) -> None:
        """経済指標データを保存"""
        # 既存データを取得
        indicators = await self.get_economic_indicators()

        # 新しいデータを追加
        indicator_entry = {
            **indicator_data,
            "saved_at": datetime.now(self.JST).isoformat()
        }
        indicators.append(indicator_entry)

        # 保存（最新100件のみ保持）
        indicators = indicators[-100:]

        await self.create_or_update_file(
            ".metadata/economic_indicators.json",
            json.dumps({"indicators": indicators, "last_updated": datetime.now(self.JST).isoformat()}, ensure_ascii=False, indent=2),
            f"Add economic indicator: {indicator_data.get('indicator', 'unknown')}"
        )

    async def get_economic_indicators(self) -> List[Dict[str, Any]]:
        """経済指標データを取得"""
        content = await self.get_file_content(".metadata/economic_indicators.json")
        if content:
            try:
                data = json.loads(content)
                return data.get("indicators", [])
            except json.JSONDecodeError:
                pass
        return []

    async def get_indicator_history(self, indicator_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """特定の指標の履歴を取得"""
        all_indicators = await self.get_economic_indicators()
        filtered = [
            ind for ind in all_indicators
            if ind.get('indicator', '').upper() == indicator_name.upper()
        ]
        # 新しい順にソート
        filtered.sort(key=lambda x: x.get('saved_at', ''), reverse=True)
        return filtered[:limit]
