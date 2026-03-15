# /setup-github - GitHub リポジトリ設定ガイド

知識を保存する GitHub リポジトリの設定手順です。

## 使い方

```
/setup-github
```

## Step 1: Private リポジトリ作成

1. GitHub で新規リポジトリ作成
2. 設定:
   - **Repository name**: `life-log`
   - **Visibility**: Private
   - **Add a README file**: チェック

## Step 2: 初期ディレクトリ構造作成

```bash
git clone https://github.com/YOUR_USERNAME/life-log.git
cd life-log

# ディレクトリ作成
mkdir -p diary/2025/02
mkdir -p learning/2025/02
mkdir -p ideas/2025/02
mkdir -p tasks/{active,completed,archive}
mkdir -p reviews/{weekly,monthly}/2025
mkdir -p .metadata

# メタデータファイル作成
cat > .metadata/index.json << 'EOF'
{"version": "1.0.0", "entries": [], "total_entries": 0, "last_updated": null}
EOF

cat > .metadata/user_config.json << 'EOF'
{"version": "1.0.0", "line_user_id": "", "timezone": "Asia/Tokyo"}
EOF

# コミット
git add .
git commit -m "Initial repository structure"
git push
```

## Step 3: Personal Access Token 作成

1. GitHub Settings → Developer settings
2. Personal access tokens → Tokens (classic)
3. "Generate new token (classic)"
4. 設定:
   - **Note**: Life Assistant
   - **Expiration**: 適切な期間
   - **Scopes**: `repo` にチェック
5. トークンをコピー

## Step 4: GCP Secret Manager に保存

```bash
echo -n "YOUR_GITHUB_TOKEN" | gcloud secrets create GITHUB_TOKEN --data-file=-
```

## リポジトリ構造

```
life-log/
├── diary/           # 日記 (日付別)
├── learning/        # 学習メモ
├── ideas/           # アイデア
├── tasks/
│   ├── active/      # 進行中タスク
│   ├── completed/   # 完了タスク
│   └── archive/     # アーカイブ
├── reviews/
│   ├── weekly/      # 週次レビュー
│   └── monthly/     # 月次レビュー
└── .metadata/       # システムメタデータ
```
