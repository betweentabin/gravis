# /trigger-review - 手動でレビュー生成

週次・月次レビューを手動でトリガーします。

## 使い方

```
/trigger-review [weekly|monthly]
```

## Cloud Scheduler ジョブを手動実行

### 週次レビュー

```bash
gcloud scheduler jobs run weekly-review --location=asia-northeast1
```

### 月次レビュー

```bash
gcloud scheduler jobs run monthly-review --location=asia-northeast1
```

## Cloud Functions を直接呼び出し

### 週次レビュー

```bash
SCHEDULER_URL=$(gcloud functions describe scheduled-tasks --region=asia-northeast1 --gen2 --format='value(serviceConfig.uri)')

curl -X POST "$SCHEDULER_URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"task_type": "weekly_review"}'
```

### 月次レビュー

```bash
curl -X POST "$SCHEDULER_URL" \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"task_type": "monthly_review"}'
```

## スケジュール設定

| ジョブ | スケジュール | 説明 |
|-------|------------|------|
| weekly-review | `0 21 * * 0` | 毎週日曜 21:00 JST |
| monthly-review | `0 9 1 * *` | 毎月1日 9:00 JST |

## スケジュール変更

```bash
gcloud scheduler jobs update http weekly-review \
  --location=asia-northeast1 \
  --schedule="0 20 * * 0"  # 20:00に変更
```

## ログ確認

```bash
gcloud functions logs read scheduled-tasks \
  --region=asia-northeast1 \
  --gen2 \
  --limit=20
```
