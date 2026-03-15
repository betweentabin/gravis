# Life Assistant セットアップガイド

LINE + Git + Claude を連携した知識管理システムのセットアップ手順です。

## 目次

1. [前提条件](#前提条件)
2. [LINE Developers 設定](#line-developers-設定)
3. [GitHub 設定](#github-設定)
4. [GCP 設定](#gcp-設定)
5. [デプロイ](#デプロイ)
6. [動作確認](#動作確認)
7. [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- Google Cloud Platform アカウント
- GitHub アカウント
- LINE アカウント
- Anthropic API キー
- `gcloud` CLI がインストール済み

---

## LINE Developers 設定

### Step 1: LINE Developers アカウント作成

1. [LINE Developers](https://developers.line.biz/) にアクセス
2. LINE アカウントでログイン
3. 開発者登録を完了

### Step 2: プロバイダー作成

1. コンソールで「プロバイダー」→「作成」
2. プロバイダー名を入力（例: "Life Assistant"）

### Step 3: Messaging API チャネル作成

1. プロバイダー内で「チャネル作成」→「Messaging API」を選択
2. 以下を設定：
   - **チャネル名**: Life Assistant
   - **チャネル説明**: 知識管理システム
   - **大業種/小業種**: 適切なものを選択
   - **メールアドレス**: 連絡先

### Step 4: 必要な情報を取得

**Basic settings タブ:**
- `Channel secret` をコピー → 後で `LINE_CHANNEL_SECRET` として使用

**Messaging API タブ:**
- `Channel access token` を発行してコピー → 後で `LINE_CHANNEL_ACCESS_TOKEN` として使用

> ⚠️ Webhook URL は GCP デプロイ後に設定します

---

## GitHub 設定

### Step 1: Private Repository 作成

1. GitHub で新規リポジトリ作成
   - **Repository name**: `life-log`
   - **Visibility**: Private
   - **Add a README file**: チェック

### Step 2: 初期ディレクトリ構造作成

ローカルでクローンして構造を作成：

```bash
git clone https://github.com/YOUR_USERNAME/life-log.git
cd life-log

# ディレクトリ構造作成
mkdir -p diary/2025/02
mkdir -p learning/2025/02
mkdir -p ideas/2025/02
mkdir -p tasks/{active,completed,archive}
mkdir -p reviews/{weekly,monthly}/2025
mkdir -p .metadata

# 初期ファイル作成
cat > .metadata/index.json << 'EOF'
{
  "version": "1.0.0",
  "entries": [],
  "total_entries": 0,
  "last_updated": null
}
EOF

cat > .metadata/tags.json << 'EOF'
{
  "version": "1.0.0",
  "tags": {}
}
EOF

cat > .metadata/user_config.json << 'EOF'
{
  "version": "1.0.0",
  "line_user_id": "",
  "timezone": "Asia/Tokyo",
  "notifications": {
    "weekly_review": true,
    "monthly_review": true
  }
}
EOF

# コミット
git add .
git commit -m "Initial repository structure"
git push
```

### Step 3: Personal Access Token 作成

1. GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. "Generate new token (classic)" をクリック
3. 設定:
   - **Note**: Life Assistant
   - **Expiration**: 適切な期間
   - **Scopes**: `repo` にチェック（Full control of private repositories）
4. Generate token をクリックしてコピー → 後で `GITHUB_TOKEN` として使用

---

## GCP 設定

### Step 1: プロジェクト作成

```bash
# プロジェクト作成
gcloud projects create life-assistant-xxxxx --name="Life Assistant"

# プロジェクト選択
gcloud config set project life-assistant-xxxxx

# 課金アカウントをリンク（必要に応じて）
gcloud billing accounts list
gcloud billing projects link life-assistant-xxxxx --billing-account=BILLING_ACCOUNT_ID
```

### Step 2: API 有効化

```bash
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    run.googleapis.com
```

### Step 3: Secret Manager 設定

セットアップスクリプトを使用：

```bash
cd life-assistant/scripts
GCP_PROJECT_ID=life-assistant-xxxxx ./setup_secrets.sh
```

または手動で設定：

```bash
# LINE Channel Secret
echo -n "YOUR_LINE_CHANNEL_SECRET" | \
  gcloud secrets create LINE_CHANNEL_SECRET --data-file=-

# LINE Channel Access Token
echo -n "YOUR_LINE_CHANNEL_ACCESS_TOKEN" | \
  gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=-

# GitHub Token
echo -n "YOUR_GITHUB_TOKEN" | \
  gcloud secrets create GITHUB_TOKEN --data-file=-

# Anthropic API Key
echo -n "YOUR_ANTHROPIC_API_KEY" | \
  gcloud secrets create ANTHROPIC_API_KEY --data-file=-
```

---

## デプロイ

### 自動デプロイ（推奨）

```bash
cd life-assistant/scripts
GCP_PROJECT_ID=life-assistant-xxxxx \
GITHUB_REPO=YOUR_USERNAME/life-log \
./deploy.sh
```

### 手動デプロイ

```bash
# Webhook Function
cd functions/webhook
gcloud functions deploy line-webhook \
  --gen2 \
  --runtime=python311 \
  --region=asia-northeast1 \
  --source=. \
  --entry-point=webhook \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=YOUR_PROJECT,GITHUB_REPO=YOUR_USERNAME/life-log" \
  --set-secrets="LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest"
```

---

## LINE Webhook URL 設定

デプロイ完了後、出力された Webhook URL を LINE Developers Console に設定：

1. LINE Developers Console → チャネル → Messaging API
2. **Webhook URL** に URL を設定
   ```
   https://asia-northeast1-YOUR_PROJECT.cloudfunctions.net/line-webhook
   ```
3. 「検証」ボタンで疎通確認
4. **Webhook の利用**: ON
5. **応答メッセージ**: OFF
6. **あいさつメッセージ**: OFF

---

## 動作確認

1. LINE で Bot を友だち追加（QR コードは Messaging API タブにあります）
2. ウェルカムメッセージが届くことを確認
3. テストメッセージを送信：
   ```
   今日はPythonの非同期処理について学んだ
   ```
4. 分類・保存完了のメッセージが返ってくることを確認
5. GitHub リポジトリにファイルが作成されていることを確認

### コマンドテスト

```
/help
/stats
/diary 今日は良い一日だった
/learn Reactのhooksについて学んだ
/task 明日までに資料作成
/search Python
```

---

## トラブルシューティング

### Webhook が応答しない

1. Cloud Functions のログを確認：
   ```bash
   gcloud functions logs read line-webhook --region=asia-northeast1 --gen2
   ```

2. LINE 署名検証エラーの場合：
   - `LINE_CHANNEL_SECRET` が正しく設定されているか確認

### GitHub にファイルが作成されない

1. `GITHUB_TOKEN` のスコープを確認（`repo` が必要）
2. リポジトリ名が正しいか確認（`username/repo` 形式）

### Claude API エラー

1. `ANTHROPIC_API_KEY` が有効か確認
2. API の利用制限に達していないか確認

### Cloud Scheduler が動かない

1. サービスアカウントの権限を確認：
   ```bash
   gcloud functions add-invoker-policy-binding scheduled-tasks \
     --region=asia-northeast1 \
     --gen2 \
     --member="serviceAccount:scheduler-invoker@YOUR_PROJECT.iam.gserviceaccount.com"
   ```

---

## 推定コスト（月額）

| サービス | 推定コスト |
|---------|----------|
| GCP Cloud Functions | ~$0 (無料枠内) |
| GCP Secret Manager | ~$0 (無料枠内) |
| GCP Cloud Scheduler | ~$0 (3ジョブ無料) |
| Claude API | ~$5-15 (使用量による) |
| GitHub Private Repo | $0 (無料) |
| LINE Messaging API | $0 (無料枠) |

**合計: 約$5-15/月** (主に Claude API 使用料)

---

## 次のステップ

- カスタマイズ: `shared/formatter.py` でMarkdownフォーマットを変更
- 通知時間変更: Cloud Scheduler の cron 設定を変更
- 新機能追加: `functions/webhook/main.py` にコマンドを追加
