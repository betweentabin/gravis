#!/bin/bash
# Life Assistant デプロイスクリプト

set -e

# 設定
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-asia-northeast1}"
GITHUB_REPO="${GITHUB_REPO:-}"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 引数チェック
if [ -z "$PROJECT_ID" ]; then
    echo_error "GCP_PROJECT_ID environment variable is not set"
    echo "Usage: GCP_PROJECT_ID=your-project GITHUB_REPO=username/repo ./deploy.sh"
    exit 1
fi

if [ -z "$GITHUB_REPO" ]; then
    echo_error "GITHUB_REPO environment variable is not set"
    echo "Usage: GCP_PROJECT_ID=your-project GITHUB_REPO=username/repo ./deploy.sh"
    exit 1
fi

# プロジェクト設定
echo_info "Setting project to $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# API有効化
echo_info "Enabling required APIs..."
gcloud services enable \
    cloudfunctions.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    cloudscheduler.googleapis.com \
    run.googleapis.com

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 共有モジュールをコピー
echo_info "Copying shared modules..."
cp -r "$PROJECT_ROOT/shared" "$PROJECT_ROOT/functions/webhook/"
cp -r "$PROJECT_ROOT/shared" "$PROJECT_ROOT/functions/scheduler/"

# Webhook Function デプロイ
echo_info "Deploying webhook function..."
cd "$PROJECT_ROOT/functions/webhook"
gcloud functions deploy line-webhook \
    --gen2 \
    --runtime=python311 \
    --region="$REGION" \
    --source=. \
    --entry-point=webhook \
    --trigger-http \
    --allow-unauthenticated \
    --memory=512MB \
    --timeout=60s \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GITHUB_REPO=$GITHUB_REPO" \
    --set-secrets="LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest"

# Webhook URLを取得
WEBHOOK_URL=$(gcloud functions describe line-webhook --region="$REGION" --gen2 --format='value(serviceConfig.uri)')
echo_info "Webhook URL: $WEBHOOK_URL"

# Scheduler Function デプロイ
echo_info "Deploying scheduler function..."
cd "$PROJECT_ROOT/functions/scheduler"
gcloud functions deploy scheduled-tasks \
    --gen2 \
    --runtime=python311 \
    --region="$REGION" \
    --source=. \
    --entry-point=scheduled_task \
    --trigger-http \
    --no-allow-unauthenticated \
    --memory=1024MB \
    --timeout=300s \
    --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GITHUB_REPO=$GITHUB_REPO" \
    --set-secrets="LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,GITHUB_TOKEN=GITHUB_TOKEN:latest,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest"

# Scheduler URLを取得
SCHEDULER_URL=$(gcloud functions describe scheduled-tasks --region="$REGION" --gen2 --format='value(serviceConfig.uri)')

# 共有モジュールを削除（クリーンアップ）
echo_info "Cleaning up..."
rm -rf "$PROJECT_ROOT/functions/webhook/shared"
rm -rf "$PROJECT_ROOT/functions/scheduler/shared"

# サービスアカウント作成（存在しない場合）
echo_info "Setting up Cloud Scheduler service account..."
SA_NAME="scheduler-invoker"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Cloud Scheduler Invoker"
fi

# 権限付与
gcloud functions add-invoker-policy-binding scheduled-tasks \
    --region="$REGION" \
    --gen2 \
    --member="serviceAccount:$SA_EMAIL"

# Cloud Scheduler ジョブ作成
echo_info "Creating Cloud Scheduler jobs..."

# 週次レビュー（毎週日曜日 21:00 JST）
if gcloud scheduler jobs describe weekly-review --location="$REGION" &>/dev/null; then
    echo_warn "weekly-review job already exists, updating..."
    gcloud scheduler jobs update http weekly-review \
        --location="$REGION" \
        --schedule="0 21 * * 0" \
        --time-zone="Asia/Tokyo" \
        --uri="$SCHEDULER_URL" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body='{"task_type": "weekly_review"}' \
        --oidc-service-account-email="$SA_EMAIL"
else
    gcloud scheduler jobs create http weekly-review \
        --location="$REGION" \
        --schedule="0 21 * * 0" \
        --time-zone="Asia/Tokyo" \
        --uri="$SCHEDULER_URL" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body='{"task_type": "weekly_review"}' \
        --oidc-service-account-email="$SA_EMAIL"
fi

# 月次レビュー（毎月1日 9:00 JST）
if gcloud scheduler jobs describe monthly-review --location="$REGION" &>/dev/null; then
    echo_warn "monthly-review job already exists, updating..."
    gcloud scheduler jobs update http monthly-review \
        --location="$REGION" \
        --schedule="0 9 1 * *" \
        --time-zone="Asia/Tokyo" \
        --uri="$SCHEDULER_URL" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body='{"task_type": "monthly_review"}' \
        --oidc-service-account-email="$SA_EMAIL"
else
    gcloud scheduler jobs create http monthly-review \
        --location="$REGION" \
        --schedule="0 9 1 * *" \
        --time-zone="Asia/Tokyo" \
        --uri="$SCHEDULER_URL" \
        --http-method=POST \
        --headers="Content-Type=application/json" \
        --message-body='{"task_type": "monthly_review"}' \
        --oidc-service-account-email="$SA_EMAIL"
fi

echo ""
echo_info "=== Deployment Complete ==="
echo ""
echo "Webhook URL (set this in LINE Developers Console):"
echo "  $WEBHOOK_URL"
echo ""
echo "Next steps:"
echo "1. Go to LINE Developers Console"
echo "2. Set the Webhook URL to: $WEBHOOK_URL"
echo "3. Enable 'Use webhook'"
echo "4. Disable 'Auto-reply messages'"
echo ""
