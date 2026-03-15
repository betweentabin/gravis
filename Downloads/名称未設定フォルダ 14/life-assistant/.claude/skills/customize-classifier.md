# /customize-classifier - 分類ロジックのカスタマイズ

Claude による自動分類のプロンプトをカスタマイズします。

## 使い方

```
/customize-classifier
```

## 分類ロジックの場所

`shared/claude_client.py` の `classify_message` メソッド

## 現在のカテゴリ

| カテゴリ | 説明 |
|---------|------|
| `diary` | 日記、日々の出来事、感情、振り返り |
| `learning` | 学習メモ、技術的内容、読書メモ |
| `idea` | アイデア、企画、改善提案 |
| `task` | TODO、やるべきこと、リマインダー |

## カスタマイズ例

### 新しいカテゴリを追加

1. `shared/claude_client.py` のプロンプトを編集:

```python
## カテゴリ
1. diary (日記): ...
2. learning (学習メモ): ...
3. idea (アイデア): ...
4. task (タスク): ...
5. health (健康): 運動、食事、睡眠、体調記録  # 追加
```

2. `shared/formatter.py` にフォーマットを追加:

```python
def _get_type_specific_metadata(self, entry_type, metadata):
    type_metadata = {
        # ...
        "health": {
            "category": extracted.get("category", "general"),
            "metrics": extracted.get("metrics", {})
        }
    }
```

3. `shared/formatter.py` の `generate_file_path` を更新:

```python
elif entry_type == "health":
    return f"health/{year}/{month}/{date_str}.md"
```

### 分類の精度向上

プロンプトに具体例を追加:

```python
## 分類の例
- "今日は疲れた" → diary
- "Reactのhooksを学んだ" → learning
- "新しいアプリのアイデア" → idea
- "明日までにレポート提出" → task
```

### タグ抽出の改善

```python
## タグ付けルール
- 技術用語は英語のまま (React, Python, AWS)
- 固有名詞は適切に抽出
- 最大5つまで
```
