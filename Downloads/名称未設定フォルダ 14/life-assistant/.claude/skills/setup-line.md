# /setup-line - LINE Developers 設定ガイド

LINE Messaging API の設定手順を案内します。

## 使い方

```
/setup-line
```

## Step 1: LINE Developers アカウント作成

1. https://developers.line.biz/ にアクセス
2. LINE アカウントでログイン
3. 開発者登録を完了

## Step 2: プロバイダー作成

1. コンソールで「プロバイダー」→「作成」
2. プロバイダー名: `Life Assistant`

## Step 3: Messaging API チャネル作成

1. 「チャネル作成」→「Messaging API」
2. 設定内容:
   - **チャネル名**: Life Assistant
   - **チャネル説明**: 知識管理システム

## Step 4: 認証情報を取得

### Channel Secret
1. Basic settings タブを開く
2. `Channel secret` をコピー

### Channel Access Token
1. Messaging API タブを開く
2. 「発行」ボタンをクリック
3. トークンをコピー

## Step 5: GCP Secret Manager に保存

```bash
echo -n "YOUR_CHANNEL_SECRET" | gcloud secrets create LINE_CHANNEL_SECRET --data-file=-
echo -n "YOUR_ACCESS_TOKEN" | gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=-
```

## Step 6: Webhook URL 設定（デプロイ後）

1. Messaging API タブ
2. Webhook URL に入力:
   ```
   https://asia-northeast1-PROJECT_ID.cloudfunctions.net/line-webhook
   ```
3. 「検証」で疎通確認
4. 以下を設定:
   - Webhook の利用: **ON**
   - 応答メッセージ: **OFF**
   - あいさつメッセージ: **OFF**

## QR コードで友だち追加

Messaging API タブの QR コードをスキャンして Bot を友だち追加。
