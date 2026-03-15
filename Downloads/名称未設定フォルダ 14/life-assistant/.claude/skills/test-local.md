# /test-local - ローカルテスト実行

Cloud Functions をローカルでテストします。

## 使い方

```
/test-local [webhook|scheduler]
```

## Webhook のローカルテスト

### 1. 環境変数を設定

```bash
export LINE_CHANNEL_SECRET="your-channel-secret"
export LINE_CHANNEL_ACCESS_TOKEN="your-access-token"
export GITHUB_TOKEN="your-github-token"
export ANTHROPIC_API_KEY="your-api-key"
export GITHUB_REPO="username/life-log"
export USE_SECRET_MANAGER="false"
```

### 2. ローカルサーバー起動

```bash
cd functions/webhook
pip install -r requirements.txt
functions-framework --target=webhook --port=8080 --debug
```

### 3. テストリクエスト送信

```bash
# ヘルプコマンドのテスト（署名なしは本番では拒否される）
curl -X POST http://localhost:8080 \
  -H "Content-Type: application/json" \
  -d '{"events": [{"type": "message", "message": {"type": "text", "text": "/help"}, "replyToken": "test", "source": {"userId": "test"}}]}'
```

## Scheduler のローカルテスト

```bash
cd functions/scheduler
pip install -r requirements.txt
functions-framework --target=scheduled_task --port=8081 --debug
```

```bash
# 週次レビューテスト
curl -X POST http://localhost:8081 \
  -H "Content-Type: application/json" \
  -d '{"task_type": "weekly_review"}'
```

## 注意事項

- ローカルテストでは LINE 署名検証をスキップする必要があります
- 本番環境の Secret Manager は使用されません（環境変数を使用）
