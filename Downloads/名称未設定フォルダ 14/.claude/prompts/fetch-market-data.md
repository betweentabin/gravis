# 市場データ取得プロンプト

## 概要
Chrome DevTools MCP または Playwright MCPを使用して、過去1年分の実際の市場データを取得し、`.claude/data/market/`のJSONファイルを更新する。

---

## 実行指示

### タスク
以下のデータソースから2025年3月〜2026年3月の市場データを取得して、`.claude/data/market/timeseries.json`の推定値を実データで置き換えてください。

### 取得対象データ

| 項目 | ティッカー | データソース候補 | 粒度 |
|------|-----------|-----------------|------|
| S&P 500 | SPX / ^GSPC | Yahoo Finance, TradingView | 日次OHLC |
| NASDAQ 100 | NDX / ^NDX | Yahoo Finance, TradingView | 日次OHLC |
| Russell 2000 | RUT / ^RUT | Yahoo Finance | 日次OHLC |
| VIX | ^VIX | Yahoo Finance, CBOE | 日次終値 |
| WTI原油 | CL=F | Yahoo Finance | 日次OHLC |
| 金 | GC=F | Yahoo Finance | 日次OHLC |
| ドル指数 | DX-Y.NYB | Yahoo Finance | 日次終値 |
| 米10年債利回り | ^TNX | Yahoo Finance | 日次終値 |
| 米2年債利回り | ^IRX or 2Y | Yahoo Finance | 日次終値 |

### 推奨データソース

1. **Yahoo Finance** (優先)
   - URL: `https://finance.yahoo.com/quote/^GSPC/history`
   - 1年の履歴データがテーブル形式で取得可能
   - 日付範囲指定可能

2. **TradingView** (代替)
   - チャートからデータ抽出

3. **Investing.com** (代替)
   - 履歴データテーブル

### 取得手順

1. Chrome DevTools MCPでブラウザを起動
2. Yahoo Finance の各ティッカーの履歴ページにアクセス
3. 期間を「1年」に設定
4. テーブルデータをスクレイピング
5. JSONフォーマットに変換
6. `timeseries.json`を更新

### 出力フォーマット

```json
{
  "date": "2025-03-15",
  "source": "yahoo_finance",
  "prices": {
    "SPX": {"open": 5380, "high": 5420, "low": 5365, "close": 5400, "volume": 3500000000},
    "NDX": {"open": 22700, "high": 22850, "low": 22650, "close": 22800},
    "VIX": {"value": 14.2},
    "WTI": {"value": 78.5},
    "US10Y": {"value": 3.85}
  }
}
```

### 補足：既存の実データ

以下の日付は記事から取得済みの実データなので、上書き不要：
- 2026-03-14 (websearch)
- 2026-03-07 (kokko_article_5)
- 2026-02-28 (kokko_article_4)
- 2026-02-15 (kokko_article_2)
- 2026-02-08 (kokko_article_3)

### 更新対象ファイル

- `.claude/data/market/timeseries.json` - メイン時系列データ
- `.claude/data/market/triggers.json` - trigger_history セクション（CTAトリガー推移）

---

## 確認事項

データ取得完了後、以下を確認：
1. 全52週分のデータが揃っているか
2. 欠損値がないか
3. 異常値（前日比±20%超など）がないか
4. sourceフィールドが「yahoo_finance」等に更新されているか
