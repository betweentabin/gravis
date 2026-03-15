# /deploy - Life Assistant デプロイ

GCP Cloud Functions へのデプロイを実行します。

## 使い方

```
/deploy
```

## 実行内容

1. 共有モジュールを functions ディレクトリにコピー
2. Webhook Function をデプロイ
3. Scheduler Function をデプロイ
4. Cloud Scheduler ジョブを設定
5. クリーンアップ

## 前提条件

- GCP プロジェクトが作成済み
- Secret Manager にシークレットが設定済み
- `gcloud` CLI が認証済み

## 環境変数

| 変数 | 説明 |
|-----|------|
| `GCP_PROJECT_ID` | GCP プロジェクト ID |
| `GITHUB_REPO` | GitHub リポジトリ (username/repo) |
| `GCP_REGION` | リージョン (デフォルト: asia-northeast1) |

## 手順

```bash
cd life-assistant/scripts
GCP_PROJECT_ID=your-project GITHUB_REPO=username/life-log ./deploy.sh
```

## 出力

デプロイ成功時、Webhook URL が表示されます。この URL を LINE Developers Console に設定してください。
