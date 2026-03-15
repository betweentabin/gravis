# /analyze-logs - Cloud Functions ログ分析

GCP Cloud Functions のログを取得・分析します。

## 使い方

```
/analyze-logs [webhook|scheduler] [--errors] [--limit N]
```

## ログ取得コマンド

### Webhook ログ

```bash
# 最新ログ
gcloud functions logs read line-webhook \
  --region=asia-northeast1 \
  --gen2 \
  --limit=50

# エラーのみ
gcloud functions logs read line-webhook \
  --region=asia-northeast1 \
  --gen2 \
  --limit=50 \
  --min-log-level=ERROR
```

### Scheduler ログ

```bash
gcloud functions logs read scheduled-tasks \
  --region=asia-northeast1 \
  --gen2 \
  --limit=50
```

## よくあるエラー

### 1. LINE 署名検証エラー
```
Invalid signature
```
→ `LINE_CHANNEL_SECRET` が正しいか確認

### 2. GitHub API エラー
```
404 Not Found
```
→ `GITHUB_REPO` の形式 (`username/repo`) と権限を確認

### 3. Claude API エラー
```
AuthenticationError
```
→ `ANTHROPIC_API_KEY` が有効か確認

### 4. タイムアウト
```
Function execution took X ms, finished with status: 'timeout'
```
→ Cloud Functions のタイムアウト設定を増やす

## デバッグのヒント

1. **リアルタイムログ監視**:
   ```bash
   gcloud functions logs read line-webhook --region=asia-northeast1 --gen2 --limit=10 --freshness=1m
   ```

2. **特定期間のログ**:
   ```bash
   gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=line-webhook" --limit=100
   ```
