# /generate-slide - 議事録からスライド自動生成

議事録テキストからINTLOOPテンプレート準拠のPowerPointスライドを生成します。

## 使い方

```
/generate-slide
```

## LINE Bot コマンド

```
/slide [議事録内容]
```

例：
```
/slide
プロジェクトA キックオフ会議
日時: 2025年2月13日

■ 参加者
- 田中（PM）、佐藤、鈴木

■ 議題
1. プロジェクト概要説明
2. スケジュール確認
3. 役割分担

■ 決定事項
- 開発言語はPythonを採用
- 週次定例は毎週火曜14:00

■ TODO
- 佐藤: 環境構築（2/20まで）
- 鈴木: 要件定義書レビュー（2/18まで）
```

## 処理フロー

1. **テキスト解析**: Claude APIで議事録を構造化JSONに変換
2. **スライド生成**: python-pptxでINTLOOPテンプレートを使用してPPTX作成
3. **アップロード**: Cloud Storageに保存し署名付きURLを生成
4. **返信**: ダウンロードリンクをLINEで送信

## 構造化JSON形式

```json
{
  "title": "会議タイトル",
  "subtitle": "サブタイトル",
  "date": "YYYY年M月D日",
  "sections": [
    {
      "heading": "セクション見出し",
      "type": "セクション種別",
      "key_points": ["要点1", "要点2"],
      "action_items": [
        {"assignee": "担当者", "action": "内容", "deadline": "期限"}
      ]
    }
  ]
}
```

## セクション種別（type）

| type | 説明 | バッジカラー |
|------|------|-------------|
| `overview` | プロジェクト概要、背景、目的 | #0086C5 (青) |
| `team_structure` | 体制、メンバー、役割分担 | #0086C5 (青) |
| `technology` | 技術方針、システム構成 | #003965 (紺) |
| `schedule` | スケジュール、マイルストーン | #ED514E (赤) |
| `risk` | リスク、課題、懸念事項 | #ED514E (赤) |
| `action_items` | アクションアイテム、TODO | #ED514E (赤) |
| `budget` | 予算、コスト | #003965 (紺) |
| `discussion` | 議論、検討事項 | #595959 (グレー) |
| `general` | その他 | #595959 (グレー) |

## デザインルール

### フォント
| 用途 | フォント | サイズ |
|------|---------|--------|
| タイトル | BIZ UDPゴシック | 36pt |
| サブ見出し | BIZ UDPゴシック | 18pt |
| 本文リード | BIZ UDPゴシック | 16pt |
| 本文 | BIZ UDPゴシック | 14pt |

### カラーパレット
| HEX | 用途 |
|-----|------|
| #003965 | ロゴ基調、タイトル、見出し |
| #0086C5 | 強調、ベタ塗り |
| #000000 | 基本テキスト |
| #595959 | 注釈、グレー |
| #ED514E | ポイント、強調 |

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `shared/slide_generator.py` | スライド生成ロジック |
| `shared/email_sender.py` | Cloud Storage アップロード (FileSharer) |
| `shared/templates/INTLOOP_スライドテンプレート_コピー.pptx` | テンプレートファイル |
| `functions/webhook/main.py` | `/slide` コマンドハンドラー |

## テンプレートレイアウト（25種）

- タイトルスライド_クライアント向け（表紙）
- 目次スライド
- サブタイトルページ（セクション区切り）
- 基本スライド（メインコンテンツ）
- 基本：3BOX① / ② / ③
- 基本：4BOX
- 基本：説明表① / ②
- 基本：フロー図
- 基本：表テーブル挿入スライド
- ロゴページ（締め）

## トラブルシューティング

### スライドが生成されない
1. Cloud Storageバケットの権限確認
   ```bash
   gcloud storage buckets describe gs://life-assistant-line-slides
   ```

2. ログ確認
   ```bash
   gcloud functions logs read life-assistant-webhook \
     --region=asia-northeast1 --gen2 --limit=20
   ```

### テンプレートが見つからない
テンプレートファイルがデプロイに含まれているか確認:
```bash
ls -la /tmp/webhook-deploy/shared/templates/
```

### ダウンロードリンクが無効
署名付きURLの有効期限は72時間です。期限切れの場合は再度 `/slide` コマンドを実行してください。
