# /add-command - 新しいLINEコマンドを追加

LINE Bot に新しいコマンドを追加します。

## 使い方

```
/add-command [コマンド名] [説明]
```

## 実装手順

### 1. コマンドハンドラーを追加

`functions/webhook/main.py` の `handle_command` 関数内に新しいハンドラーを追加:

```python
async def handle_command(text: str, user_id: str, message_id: str) -> str:
    handlers = {
        # ... 既存のハンドラー
        '/newcommand': lambda: new_command_handler(content, user_id),
    }
```

### 2. ハンドラー関数を実装

```python
async def new_command_handler(content: str, user_id: str) -> str:
    """新しいコマンドの処理"""
    if not content:
        return "使い方: /newcommand [引数]"

    # 処理ロジック

    return "結果メッセージ"
```

### 3. ヘルプに追加

`show_help()` 関数のヘルプテキストに新しいコマンドを追加。

### 4. 再デプロイ

```bash
/deploy
```

## 既存コマンドの参考実装

- シンプルな処理: `show_stats()`, `show_help()`
- GitHub 連携: `search_entries()`, `complete_task()`
- Claude 連携: `save_as_type()`, `process_message()`
