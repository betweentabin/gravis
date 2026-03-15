#!/bin/bash
# Secret Manager セットアップスクリプト

set -e

# 設定
PROJECT_ID="${GCP_PROJECT_ID:-}"

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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
    echo "Usage: GCP_PROJECT_ID=your-project ./setup_secrets.sh"
    exit 1
fi

# プロジェクト設定
echo_info "Setting project to $PROJECT_ID"
gcloud config set project "$PROJECT_ID"

# Secret Manager API有効化
echo_info "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# シークレット作成関数
create_secret() {
    local secret_name=$1
    local prompt_message=$2

    echo ""
    echo_info "Setting up $secret_name"

    # 既存チェック
    if gcloud secrets describe "$secret_name" &>/dev/null; then
        echo_warn "$secret_name already exists"
        read -p "Do you want to update it? (y/N): " update_choice
        if [ "$update_choice" != "y" ] && [ "$update_choice" != "Y" ]; then
            echo "Skipping $secret_name"
            return
        fi
    fi

    # 値を入力
    echo "$prompt_message"
    read -s -p "Enter value (hidden): " secret_value
    echo ""

    if [ -z "$secret_value" ]; then
        echo_warn "Empty value, skipping $secret_name"
        return
    fi

    # シークレット作成または更新
    if gcloud secrets describe "$secret_name" &>/dev/null; then
        echo -n "$secret_value" | gcloud secrets versions add "$secret_name" --data-file=-
    else
        echo -n "$secret_value" | gcloud secrets create "$secret_name" --data-file=-
    fi

    echo_info "$secret_name has been set"
}

echo ""
echo "=== Life Assistant Secret Manager Setup ==="
echo ""
echo "This script will help you set up the required secrets."
echo "Please have the following ready:"
echo "  1. LINE Channel Secret (from LINE Developers Console)"
echo "  2. LINE Channel Access Token (from LINE Developers Console)"
echo "  3. GitHub Personal Access Token (from GitHub Settings)"
echo "  4. Anthropic API Key (from Anthropic Console)"
echo ""

# LINE Channel Secret
create_secret "LINE_CHANNEL_SECRET" \
    "LINE Channel Secret: Found in LINE Developers Console > Your Channel > Basic settings"

# LINE Channel Access Token
create_secret "LINE_CHANNEL_ACCESS_TOKEN" \
    "LINE Channel Access Token: Found in LINE Developers Console > Your Channel > Messaging API > Issue"

# GitHub Token
create_secret "GITHUB_TOKEN" \
    "GitHub Personal Access Token: Create at GitHub > Settings > Developer settings > Personal access tokens (needs 'repo' scope)"

# Anthropic API Key
create_secret "ANTHROPIC_API_KEY" \
    "Anthropic API Key: Found in Anthropic Console > API Keys"

echo ""
echo_info "=== Secret Setup Complete ==="
echo ""
echo "All secrets have been configured in Secret Manager."
echo "You can now run the deploy script:"
echo "  GCP_PROJECT_ID=$PROJECT_ID GITHUB_REPO=username/life-log ./deploy.sh"
echo ""
