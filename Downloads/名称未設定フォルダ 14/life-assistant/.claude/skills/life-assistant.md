# Life Assistant Skills

LINE + Git + Claude を連携した知識管理システムのスキル集です。

## プロジェクト概要

- **入力**: LINE Messaging API
- **処理**: GCP Cloud Functions (Python 3.11)
- **保存**: GitHub Private Repository (`life-log`)
- **分析**: Anthropic Claude API

## ディレクトリ構造

```
life-assistant/
├── shared/           # 共有モジュール
├── functions/
│   ├── webhook/      # LINE Webhook ハンドラー
│   └── scheduler/    # 定期タスク（レビュー生成）
├── scripts/          # デプロイスクリプト
└── docs/             # ドキュメント
```

## 主要ファイル

| ファイル | 役割 |
|---------|------|
| `shared/config.py` | 設定・Secret Manager 連携 |
| `shared/line_client.py` | LINE API クライアント |
| `shared/github_client.py` | GitHub API クライアント |
| `shared/claude_client.py` | Claude API クライアント |
| `shared/classifier.py` | メッセージ分類ロジック |
| `shared/formatter.py` | Markdown フォーマッター |
| `functions/webhook/main.py` | LINE Webhook 処理 |
| `functions/scheduler/main.py` | 週次/月次レビュー生成 |

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `/diary [内容]` | 日記として保存 |
| `/learn [内容]` | 学習メモとして保存 |
| `/idea [内容]` | アイデアとして保存 |
| `/task [内容]` | タスク追加 |
| `/done [名前]` | タスク完了 |
| `/review week/month` | レビュー表示 |
| `/search [キーワード]` | 検索 |
| `/stats` | 統計表示 |

## デプロイ

```bash
cd scripts
GCP_PROJECT_ID=your-project GITHUB_REPO=username/life-log ./deploy.sh
```
