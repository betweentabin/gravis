# /indicators - マーケットクロス分析・インジケータースキル

FRED時系列データと記事データをクロス分析し、派生インジケーターを算出する。
Pythonで計算し、結果をマークダウンまたはJSONで返す。

## 使い方

```
/indicators                    # 全インジケーターの最新スナップショット
/indicators regime             # 現在のレジーム判定（リスクオン/オフ等）
/indicators divergence          # FRED vs 記事データの乖離分析
/indicators signal [long|short] # 売買シグナル一覧
/indicators history [indicator] # 特定インジケーターの時系列推移
/indicators custom "式"         # カスタム計算（例: "SPX/VIX"）
```

---

## データソース

すべて `.claude/data/market/` 配下のJSONを読み込む：

| ファイル | 用途 |
|---------|------|
| `timeseries.json` | FRED週次9指標（SPX,NDX,SMCAP,VIX,WTI,US10Y,US2Y,DXY_BROAD,GOLD） |
| `timeseries_articles.json` | kokko記事データ（ポジショニング,ガンマ,ブレッドス,CTA等） |
| `triggers.json` | CTA/ガンマトリガー水準 |
| `positions.json` | ポジショニング履歴 |
| `events.json` | イベントログ |

---

## 実行手順

1. **JSONファイルを読み込む**（Read tool）
2. **Pythonスクリプトを実行**（Bash tool）して派生指標を計算
3. **結果をマークダウンで出力**

### Pythonテンプレート

```python
import json, sys
from pathlib import Path

BASE = Path(".claude/data/market")

# --- データ読み込み ---
with open(BASE / "timeseries.json") as f:
    ts = json.load(f)
snapshots = ts["snapshots"]

with open(BASE / "timeseries_articles.json") as f:
    articles = json.load(f)

with open(BASE / "positions.json") as f:
    positions = json.load(f)

with open(BASE / "triggers.json") as f:
    triggers = json.load(f)

# --- ヘルパー ---
def get(snap, key, default=None):
    return snap.get(key, default)

def pct_change(curr, prev):
    if prev and prev != 0:
        return round((curr - prev) / prev * 100, 2)
    return None

def sma(values, n):
    if len(values) < n:
        return None
    return round(sum(values[-n:]) / n, 2)

def zscore(value, values):
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    std = (sum((v - mean)**2 for v in values) / len(values)) ** 0.5
    if std == 0:
        return 0
    return round((value - mean) / std, 2)

# ここに各インジケーターの計算を書く
# ...
```

---

## インジケーター定義

### カテゴリ1: イールドカーブ・金利

#### `YIELD_CURVE_2S10S` — 2s10sスプレッド
```python
spread = US10Y - US2Y  # bp単位にする場合は ×100
```
- **意味**: 正=ノーマル、負=逆イールド（リセッション先行指標）
- **閾値**: < 0 → リセッション警告、> 100bp → スティープ（景気拡大初期）

#### `REAL_RATE_PROXY` — 実質金利プロキシ
```python
# CPI未取得のためISM価格指数からの推定値（記事データ）を使う
# または US10Y - ブレークイーブン（未取得）として US10Y そのものを監視
```

---

### カテゴリ2: リスクオン/オフ

#### `GOLD_OIL_RATIO` — 金/原油比率
```python
ratio = GOLD / WTI
```
- **意味**: 高い=リスクオフ（安全資産選好）、低い=リスクオン
- **用途**: 地政学リスクの株式市場への波及度を測る

#### `GOLD_SPX_RATIO` — 金/株式比率
```python
ratio = GOLD / SPX
```
- **意味**: 上昇=株式からゴールドへのローテーション

#### `VIX_SPX_RATIO` — VIX/SPX比率（恐怖指数正規化）
```python
ratio = VIX / SPX * 1000
```
- **意味**: 高い=恐怖過多、低い=楽観過多
- **閾値**: > 5 → パニック圏、< 2.5 → 楽観過多

#### `SMCAP_NDX_RATIO` — 小型/大型株比率
```python
ratio = SMCAP / NDX * 100
```
- **意味**: 上昇=リスクオン拡大（小型株選好）、下降=大型株集中（防御的）

---

### カテゴリ3: モメンタム・トレンド

#### `SPX_4W_MOMENTUM` — SPX 4週モメンタム
```python
mom = (SPX_now - SPX_4w_ago) / SPX_4w_ago * 100
```

#### `SPX_13W_MOMENTUM` — SPX 13週（四半期）モメンタム
```python
mom = (SPX_now - SPX_13w_ago) / SPX_13w_ago * 100
```

#### `SPX_SMA4` / `SPX_SMA13` — 移動平均
```python
sma4 = mean(SPX[-4:])
sma13 = mean(SPX[-13:])
trend = "bullish" if sma4 > sma13 else "bearish"
```

#### `DXY_SPX_DIVERGENCE` — ドル/株式ダイバージェンス
```python
# 通常: ドル高→株安。同方向なら異常
spx_4w_chg = pct_change(SPX, SPX_4w)
dxy_4w_chg = pct_change(DXY, DXY_4w)
divergence = spx_4w_chg + dxy_4w_chg  # 通常は相殺して≈0
# |divergence| > 5 → 異常
```

---

### カテゴリ4: ボラティリティ構造

#### `VIX_ZSCORE` — VIX Zスコア（52週基準）
```python
vix_values = [s["VIX"] for s in snapshots]
z = zscore(vix_values[-1], vix_values)
```
- **閾値**: > 2 → パニック、< -1 → 楽観極端（VIXショートスクイーズリスク）

#### `VIX_PERCENTILE` — VIX パーセンタイル（52週）
```python
current = vix_values[-1]
pct = sum(1 for v in vix_values if v <= current) / len(vix_values) * 100
```

#### `WTI_VOLATILITY` — 原油4週ボラティリティ
```python
import statistics
wti_returns = [pct_change(wti[i], wti[i-1]) for i in range(-4, 0)]
vol = statistics.stdev(wti_returns)
```

---

### カテゴリ5: 記事データクロス（timeseries_articles.json使用）

#### `FRED_VS_ARTICLE_SPX` — FRED/記事 SPX乖離率
```python
# 記事の同日付FREDデータとの差を計算
for article in articles["snapshots"]:
    fred_snap = find_nearest_fred(article["date"])
    gap_pct = (fred_snap["SPX"] - article["prices"]["SPX"]["value"]) / article["prices"]["SPX"]["value"] * 100
```
- **用途**: 記事が参照している「市場」と公式データの違いを定量化

#### `POSITIONING_VIX_COMPOSITE` — ポジショニング×VIX複合スコア
```python
# positions.json の positioning_history を使用
# 低ポジション + 高VIX = 買いシグナル
# 高ポジション + 低VIX = 売りシグナル
pos = positioning_percentile  # 0-100
vix_pct = vix_percentile      # 0-100
composite = pos - vix_pct     # 負=買い、正=売り
```

#### `CRASH_RISK_SCORE` — クラッシュリスクスコア
```python
# triggers.json + positions.json を総合
score = 0
if cta_triggered: score += 25
if vix_backwardation: score += 20
if gamma_negative: score += 20
if breadth < 20: score += 15
if discretionary_pct < 30: score += 10
if vol_control_pct < 40: score += 10
# score: 0-100, >60 = 高リスク
```

#### `MELT_UP_SCORE` — メルトアップリスクスコア
```python
score = 0
if discretionary_pct < 30: score += 25   # アンダーウェイト→巻き戻し
if mmf_tn > 7.5: score += 20             # 待機資金豊富
if buyback_pct_remaining > 70: score += 15
if vix_zscore < -1: score += 20          # 楽観極端
if spx_below_sma13: score += 20          # 売られ過ぎからの反発
```

---

## 出力フォーマット

### `/indicators` の出力例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MARKET INDICATORS [2026-03-13]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ イールドカーブ
  2s10s:        +56bp (スティープ)    4W前: +60bp
  US10Y:        4.19%                 52W Z: -0.3
  US2Y:         3.63%                 52W Z: -1.2

■ リスクオン/オフ
  Gold/Oil:     64.1 (高=リスクオフ)  4W前: 81.8 ← 原油急騰で低下
  Gold/SPX:     0.757                 4W前: 0.783
  VIX/SPX*1000: 3.84                  52W平均: 2.94
  SmCap/NDX:    13.2%                 4W前: 13.8%

■ モメンタム
  SPX 4W:       -3.6%    13W:  -3.1%
  NDX 4W:       -0.4%    13W:  -4.4%
  SMA4 vs SMA13: bearish (SMA4 < SMA13)

■ ボラティリティ
  VIX:          25.49    Z: +1.4     Pctl: 85%
  WTI 4W Vol:   18.2% (異常)

■ 複合スコア
  Crash Risk:   70/100 [HIGH]
    CTA triggered(+25), VIX backwardation(+20),
    Gamma negative(+20), Breadth low(+15)
  Melt-Up Risk: 55/100 [MODERATE]
    Underweight discretionary(+25), MMF record(+20),
    Below SMA13(+20)

■ FRED vs 記事乖離
  SPX: FRED 6632 vs kokko 5621 → +18.0% 乖離
  NDX: FRED 24761 vs kokko 24380 → +1.6% 一致

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `/indicators regime` の出力例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REGIME ANALYSIS [2026-03-13]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

■ 現在のレジーム: RISK-OFF (地政学ドリブン)

  判定根拠:
  [x] VIX > 25 (25.49)
  [x] VIX backwardation
  [x] CTA sell triggered
  [x] Discretionary < 30pctl (22)
  [ ] Yield curve inverted (NO - still positive)

■ レジーム遷移履歴（直近5回）
  2026-03-01~: RISK-OFF (Iran crisis)     VIX avg: 25
  2026-01-27~: ADJUSTMENT (DeepSeek)       VIX avg: 18
  2025-12-01~: RISK-ON (Year-end rally)    VIX avg: 15
  2025-11-01~: ELECTION VOL                VIX avg: 22
  2025-09-18~: RATE-CUT RALLY              VIX avg: 17

■ レジーム転換シグナル
  Risk-On移行条件:
  [ ] VIX < 20 → 現在 25.49
  [ ] VIX contango回帰
  [ ] CTA trigger解除 (SPX > 5725)
  [ ] Breadth > 50%
  達成: 0/4 → 転換まだ遠い
```

### `/indicators history yield_curve` の出力例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 YIELD CURVE 2s10s HISTORY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Date        US10Y  US2Y   Spread  Direction
2025-03-07  4.25   3.97   +28bp   ─
2025-04-04  4.13   3.81   +32bp   ▲ steepening
2025-05-23  4.51   3.99   +52bp   ▲ steepening
2025-07-18  4.46   3.90   +56bp   ▲ peak spread
2025-09-19  4.08   3.54   +54bp   ─
2025-10-24  4.00   3.46   +54bp   ─
2025-12-26  4.16   3.46   +70bp   ▲ steepening
2026-01-23  4.27   3.60   +67bp   ▼ flattening
2026-02-27  4.02   3.42   +60bp   ▼ flattening
2026-03-13  4.19   3.63   +56bp   ▼ flattening

トレンド: 年間でスティープニング (+28bp → +56bp)
         直近はフラットニング傾向
```

---

## `/indicators custom` の使い方

自由に式を指定して計算：

```
/indicators custom "GOLD / WTI"           # 金原油比率
/indicators custom "US10Y - US2Y"         # イールドカーブ
/indicators custom "SPX / SMCAP"          # 大型/小型比率
/indicators custom "VIX * WTI / 100"      # 恐怖×原油（ストレス指標）
/indicators custom "zscore(VIX, 13)"      # VIX 13週Zスコア
/indicators custom "sma(SPX, 4) - sma(SPX, 13)"  # ゴールデン/デッドクロス
/indicators custom "momentum(NDX, 4)"     # NDX 4週モメンタム
```

実行時はPythonでパースして計算する。

---

## 関連スキル

- `/chart` - リアルタイムダッシュボード（WebSearch併用）
- `/market-analysis` - 記事分析・蓄積
- `/indicators` - 本スキル（クロス分析・派生指標）

## 注意事項

- FREDデータと記事データのSPX乖離（約15%）があるため、クロス分析時は注意
- DSPX/COR1Mはプロプライエタリのため時系列計算不可（記事スナップショットのみ）
- 週次データのため日中・日次シグナルには不向き
