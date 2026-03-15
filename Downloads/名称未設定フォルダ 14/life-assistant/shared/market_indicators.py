"""
Market Indicators Engine
FRED時系列 + 記事データからクロス分析インジケーターを算出する

Usage:
    # モジュールとして
    from shared.market_indicators import MarketIndicators
    mi = MarketIndicators(data_dir=".claude/data/market")
    result = mi.snapshot()

    # CLIとして
    python -m shared.market_indicators snapshot
    python -m shared.market_indicators regime
    python -m shared.market_indicators signal long
    python -m shared.market_indicators history yield_curve
    python -m shared.market_indicators custom "GOLD / WTI"
"""
import json
import statistics
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


class MarketIndicators:
    """マーケットクロス分析エンジン"""

    def __init__(self, data_dir: str = ".claude/data/market"):
        self.data_dir = Path(data_dir)
        self._load_data()

    # ──────────────────────────────────────────────
    # Data Loading
    # ──────────────────────────────────────────────
    def _load_data(self):
        self.ts = self._read("timeseries.json")
        self.articles = self._read("timeseries_articles.json")
        self.positions = self._read("positions.json")
        self.triggers = self._read("triggers.json")
        self.events = self._read("events.json")

        # oldest-first series
        self.snaps = list(reversed(self.ts.get("snapshots", [])))
        self.dates = [s["date"] for s in self.snaps]

    def _read(self, name: str) -> dict:
        p = self.data_dir / name
        if p.exists():
            with open(p) as f:
                return json.load(f)
        return {}

    # ──────────────────────────────────────────────
    # Series Helpers
    # ──────────────────────────────────────────────
    def _series(self, key: str) -> list:
        """指定キーの時系列を oldest-first で返す"""
        return [s.get(key) for s in self.snaps]

    def _valid(self, vals: list) -> list:
        return [v for v in vals if v is not None]

    @staticmethod
    def pct(a, b):
        if b and b != 0:
            return round((a - b) / b * 100, 2)
        return None

    @staticmethod
    def sma(vals: list, n: int):
        valid = [v for v in vals[-n:] if v is not None]
        return round(sum(valid) / len(valid), 2) if len(valid) == n else None

    @staticmethod
    def zscore(val, vals: list):
        clean = [v for v in vals if v is not None]
        if len(clean) < 2 or val is None:
            return None
        m = sum(clean) / len(clean)
        std = (sum((v - m) ** 2 for v in clean) / len(clean)) ** 0.5
        return round((val - m) / std, 2) if std else 0

    @staticmethod
    def percentile(val, vals: list):
        clean = [v for v in vals if v is not None]
        if not clean or val is None:
            return None
        return round(sum(1 for v in clean if v <= val) / len(clean) * 100, 1)

    def _latest(self, n: int = 0) -> dict:
        """最新から n 番目のスナップショットを返す (0=最新)"""
        idx = len(self.snaps) - 1 - n
        return self.snaps[idx] if 0 <= idx < len(self.snaps) else {}

    # ──────────────────────────────────────────────
    # Individual Indicators
    # ──────────────────────────────────────────────

    # --- Yield Curve ---
    def yield_curve_2s10s(self) -> dict:
        us10 = self._series("US10Y")
        us2 = self._series("US2Y")
        spreads = [
            round((t - w) * 100) if t is not None and w is not None else None
            for t, w in zip(us10, us2)
        ]
        curr = spreads[-1]
        w4 = spreads[-5] if len(spreads) >= 5 else None
        w13 = spreads[-14] if len(spreads) >= 14 else None
        return {
            "name": "YIELD_CURVE_2S10S",
            "value": curr,
            "unit": "bp",
            "w4_ago": w4,
            "w13_ago": w13,
            "direction": "steepening" if w4 and curr and curr > w4 else "flattening",
            "signal": "normal" if curr and curr > 0 else "inverted",
            "history": spreads,
        }

    # --- Risk On/Off ---
    def gold_oil_ratio(self) -> dict:
        gold = self._series("GOLD")
        wti = self._series("WTI")
        ratios = [
            round(g / w, 1) if g and w else None for g, w in zip(gold, wti)
        ]
        curr = ratios[-1]
        avg = round(
            sum(v for v in ratios if v) / len([v for v in ratios if v]), 1
        )
        return {
            "name": "GOLD_OIL_RATIO",
            "value": curr,
            "w4_ago": ratios[-5] if len(ratios) >= 5 else None,
            "avg_52w": avg,
            "interpretation": "risk_off" if curr and curr > avg else "risk_on",
            "history": ratios,
        }

    def gold_spx_ratio(self) -> dict:
        gold = self._series("GOLD")
        spx = self._series("SPX")
        ratios = [
            round(g / s, 3) if g and s else None for g, s in zip(gold, spx)
        ]
        return {
            "name": "GOLD_SPX_RATIO",
            "value": ratios[-1],
            "w4_ago": ratios[-5] if len(ratios) >= 5 else None,
            "interpretation": "gold_outperform"
            if ratios[-1] and ratios[-5] and ratios[-1] > ratios[-5]
            else "equity_outperform",
            "history": ratios,
        }

    def vix_spx_ratio(self) -> dict:
        vix = self._series("VIX")
        spx = self._series("SPX")
        ratios = [
            round(v / s * 1000, 2) if v and s else None
            for v, s in zip(vix, spx)
        ]
        valid = self._valid(ratios)
        avg = round(sum(valid) / len(valid), 2) if valid else None
        curr = ratios[-1]
        return {
            "name": "VIX_SPX_RATIO",
            "value": curr,
            "avg_52w": avg,
            "signal": "panic"
            if curr and curr > 5
            else "fear"
            if curr and curr > 3.5
            else "complacent"
            if curr and curr < 2.5
            else "normal",
            "history": ratios,
        }

    def smcap_ndx_ratio(self) -> dict:
        smcap = self._series("SMCAP")
        ndx = self._series("NDX")
        ratios = [
            round(s / n * 100, 2) if s and n else None
            for s, n in zip(smcap, ndx)
        ]
        return {
            "name": "SMCAP_NDX_RATIO",
            "value": ratios[-1],
            "w4_ago": ratios[-5] if len(ratios) >= 5 else None,
            "interpretation": "risk_on_broadening"
            if ratios[-1] and ratios[-5] and ratios[-1] > ratios[-5]
            else "large_cap_defensive",
            "history": ratios,
        }

    # --- Momentum ---
    def momentum(self, key: str = "SPX", weeks: int = 4) -> dict:
        vals = self._series(key)
        curr = vals[-1]
        prev = vals[-(weeks + 1)] if len(vals) > weeks else None
        mom = self.pct(curr, prev) if curr and prev else None
        return {
            "name": f"{key}_{weeks}W_MOMENTUM",
            "value": mom,
            "unit": "%",
            "current_price": curr,
            "base_price": prev,
        }

    def trend(self, key: str = "SPX") -> dict:
        vals = self._series(key)
        sma4 = self.sma(vals, 4)
        sma13 = self.sma(vals, 13)
        bullish = sma4 and sma13 and sma4 > sma13
        return {
            "name": f"{key}_TREND",
            "sma4": sma4,
            "sma13": sma13,
            "signal": "bullish" if bullish else "bearish",
            "gap_pct": self.pct(sma4, sma13) if sma4 and sma13 else None,
        }

    # --- Volatility ---
    def vix_stats(self) -> dict:
        vix = self._valid(self._series("VIX"))
        curr = vix[-1] if vix else None
        return {
            "name": "VIX_STATS",
            "value": curr,
            "zscore_52w": self.zscore(curr, vix),
            "percentile_52w": self.percentile(curr, vix),
            "sma4": self.sma(vix, 4),
            "signal": "extreme_fear"
            if curr and curr > 35
            else "high_vol"
            if curr and curr > 25
            else "elevated"
            if curr and curr > 20
            else "low_vol"
            if curr and curr < 15
            else "normal",
        }

    def wti_volatility(self, weeks: int = 4) -> dict:
        wti = self._valid(self._series("WTI"))
        if len(wti) < weeks + 1:
            return {"name": "WTI_VOL", "value": None}
        rets = [self.pct(wti[i], wti[i - 1]) for i in range(-weeks, 0)]
        vol = round(statistics.stdev(rets), 1) if len(rets) >= 2 else None
        return {
            "name": "WTI_VOLATILITY",
            "value": vol,
            "unit": "% (weekly stdev)",
            "signal": "extreme" if vol and vol > 15 else "high" if vol and vol > 8 else "normal",
        }

    # --- Dollar ---
    def dxy_trend(self) -> dict:
        dxy = self._series("DXY_BROAD")
        valid = self._valid(dxy)
        if not valid:
            return {"name": "DXY_TREND", "value": None}
        curr = valid[-1]
        return {
            "name": "DXY_TREND",
            "value": curr,
            "zscore_52w": self.zscore(curr, valid),
            "w4_momentum": self.pct(curr, valid[-5]) if len(valid) >= 5 else None,
            "w13_momentum": self.pct(curr, valid[-14]) if len(valid) >= 14 else None,
            "signal": "strong_dollar" if self.zscore(curr, valid) and self.zscore(curr, valid) > 1 else
                      "weak_dollar" if self.zscore(curr, valid) and self.zscore(curr, valid) < -1 else "neutral",
        }

    # ──────────────────────────────────────────────
    # Composite Scores
    # ──────────────────────────────────────────────
    def crash_risk_score(self) -> dict:
        score = 0
        components = []

        # CTA triggered
        cta = self.triggers.get("cta_triggers", {}).get("SPX", {})
        if cta.get("status") == "triggered":
            score += 25
            components.append(("CTA_triggered", 25))

        # VIX backwardation
        vix_struct = self.triggers.get("vix_structure", {})
        if vix_struct.get("curve") == "backwardation":
            score += 20
            components.append(("VIX_backwardation", 20))

        # Gamma negative
        gamma = self.triggers.get("gamma_levels", {}).get("SPX", {})
        if gamma.get("gamma_status") == "negative":
            score += 20
            components.append(("Gamma_negative", 20))

        # Breadth
        breadth = self.triggers.get("breadth_alerts", {}).get("spx_above_20ema", {})
        bval = breadth.get("current_pct", 50)
        if bval < 15:
            score += 15
            components.append((f"Breadth_extreme({bval}%)", 15))
        elif bval < 30:
            score += 10
            components.append((f"Breadth_low({bval}%)", 10))

        # Discretionary
        disc = (self.positions.get("current_positioning", {})
                .get("discretionary", {}).get("aggregate", {}).get("percentile", 50))
        if disc < 30:
            score += 10
            components.append((f"Discretionary_underweight({disc}pctl)", 10))

        # Vol Control
        vc = (self.positions.get("current_positioning", {})
              .get("systematic", {}).get("vol_control", {}).get("percentile", 50))
        if vc < 40:
            score += 10
            components.append((f"VolControl_low({vc}pctl)", 10))

        return {
            "name": "CRASH_RISK",
            "score": score,
            "max": 100,
            "rating": self._rating(score),
            "components": components,
        }

    def melt_up_score(self) -> dict:
        score = 0
        components = []

        # Discretionary underweight
        disc = (self.positions.get("current_positioning", {})
                .get("discretionary", {}).get("aggregate", {}).get("percentile", 50))
        if disc < 30:
            score += 25
            components.append((f"Discretionary_underweight({disc}pctl)", 25))

        # MMF record high
        mmf = (self.positions.get("current_positioning", {})
               .get("flows", {}).get("mmf", {}).get("total_tn", 0))
        if mmf > 7.5:
            score += 20
            components.append((f"MMF_record(${mmf}T)", 20))

        # VIX extreme low (complacency → reversal fuel)
        vix_z = self.vix_stats().get("zscore_52w")
        if vix_z is not None and vix_z < -1:
            score += 20
            components.append((f"VIX_low(Z={vix_z})", 20))

        # Below SMA13 (potential snapback)
        t = self.trend("SPX")
        if t["signal"] == "bearish":
            score += 20
            components.append(("SPX_below_SMA13", 20))

        # Buyback remaining
        bb = (self.positions.get("current_positioning", {})
              .get("buyback", {}).get("discretionary_pct", 100))
        if bb < 50:
            score += 15
            components.append((f"Buyback_{100-bb}%_remaining", 15))

        return {
            "name": "MELT_UP_RISK",
            "score": score,
            "max": 100,
            "rating": self._rating(score),
            "components": components,
        }

    @staticmethod
    def _rating(score: int) -> str:
        if score >= 70:
            return "HIGH"
        if score >= 50:
            return "MODERATE"
        if score >= 30:
            return "LOW"
        return "MINIMAL"

    # ──────────────────────────────────────────────
    # FRED vs Article Divergence
    # ──────────────────────────────────────────────
    def divergence(self) -> list:
        results = []
        for art in self.articles.get("snapshots", []):
            art_date = art["date"]
            prices = art.get("prices", {})
            spx_data = prices.get("SPX", {})
            art_val = spx_data.get("value") if isinstance(spx_data, dict) else spx_data
            if not art_val:
                continue

            # Nearest FRED snap
            nearest = min(
                self.ts.get("snapshots", []),
                key=lambda s: abs(
                    int(s["date"].replace("-", "")) - int(art_date.replace("-", ""))
                ),
            )
            fred_val = nearest.get("SPX")
            if not fred_val:
                continue

            gap = round((fred_val - art_val) / art_val * 100, 1)
            results.append({
                "date": art_date,
                "source": art.get("source", ""),
                "article_spx": art_val,
                "fred_spx": round(fred_val, 2),
                "gap_pct": gap,
            })
        return results

    # ──────────────────────────────────────────────
    # Regime Detection
    # ──────────────────────────────────────────────
    def regime(self) -> dict:
        vix_val = self.vix_stats()
        cta = self.triggers.get("cta_triggers", {}).get("SPX", {})
        vix_curve = self.triggers.get("vix_structure", {}).get("curve")
        disc = (self.positions.get("current_positioning", {})
                .get("discretionary", {}).get("aggregate", {}).get("percentile", 50))
        yc = self.yield_curve_2s10s()

        conditions = {
            "VIX > 25": vix_val["value"] is not None and vix_val["value"] > 25,
            "VIX backwardation": vix_curve == "backwardation",
            "CTA sell triggered": cta.get("status") == "triggered",
            "Discretionary < 30pctl": disc < 30,
            "Yield curve inverted": yc["value"] is not None and yc["value"] < 0,
        }

        risk_off_count = sum(1 for v in conditions.values() if v)

        if risk_off_count >= 3:
            regime = "RISK_OFF"
        elif risk_off_count >= 2:
            regime = "CAUTIOUS"
        elif disc > 60 and vix_val["value"] and vix_val["value"] < 18:
            regime = "RISK_ON"
        else:
            regime = "NEUTRAL"

        # Recovery conditions
        recovery = {
            "VIX < 20": vix_val["value"] is not None and vix_val["value"] < 20,
            "VIX contango": vix_curve == "contango",
            "CTA trigger clear": cta.get("status") != "triggered",
            "Breadth > 50%": (self.triggers.get("breadth_alerts", {})
                              .get("spx_above_20ema", {}).get("current_pct", 0) > 50),
        }
        recovery_met = sum(1 for v in recovery.values() if v)

        # Regime history from positions.json
        regime_hist = self.positions.get("regime_classification", [])

        return {
            "current": regime,
            "conditions": conditions,
            "risk_off_score": f"{risk_off_count}/5",
            "recovery_conditions": recovery,
            "recovery_progress": f"{recovery_met}/4",
            "regime_history": regime_hist[-5:] if regime_hist else [],
        }

    # ──────────────────────────────────────────────
    # Signal Generation
    # ──────────────────────────────────────────────
    def signals(self, direction: str = "all") -> list:
        """売買シグナルを生成"""
        sigs = []

        # --- Long signals ---
        vix = self.vix_stats()
        crash = self.crash_risk_score()
        melt = self.melt_up_score()
        yc = self.yield_curve_2s10s()

        if vix["percentile_52w"] and vix["percentile_52w"] > 90:
            sigs.append({
                "direction": "long",
                "signal": "VIX_EXTREME",
                "strength": "strong",
                "reason": f"VIX {vix['value']} at {vix['percentile_52w']}th percentile — contrarian buy",
            })

        if melt["score"] >= 60:
            sigs.append({
                "direction": "long",
                "signal": "MELT_UP_CONDITIONS",
                "strength": "moderate",
                "reason": f"Melt-up score {melt['score']}/100 — snapback potential",
            })

        mom_ndx = self.momentum("NDX", 13)
        if mom_ndx["value"] and mom_ndx["value"] < -10:
            sigs.append({
                "direction": "long",
                "signal": "NDX_OVERSOLD_13W",
                "strength": "moderate",
                "reason": f"NDX 13W momentum {mom_ndx['value']}% — oversold",
            })

        # Gold strength
        gold_mom = self.momentum("GOLD", 13)
        if gold_mom["value"] and gold_mom["value"] > 20:
            sigs.append({
                "direction": "long",
                "signal": "GOLD_BREAKOUT",
                "strength": "strong",
                "reason": f"Gold 13W momentum +{gold_mom['value']}% — safe haven demand",
            })

        # --- Short / Hedge signals ---
        if crash["score"] >= 70:
            sigs.append({
                "direction": "short",
                "signal": "CRASH_RISK_HIGH",
                "strength": "strong",
                "reason": f"Crash risk {crash['score']}/100 — hedging warranted",
            })

        wti_vol = self.wti_volatility()
        if wti_vol["signal"] in ("extreme", "high"):
            sigs.append({
                "direction": "short",
                "signal": "OIL_VOL_SPIKE",
                "strength": "moderate",
                "reason": f"WTI vol {wti_vol['value']}% — supply disruption risk",
            })

        t = self.trend("SPX")
        if t["signal"] == "bearish" and t["gap_pct"] and t["gap_pct"] < -1:
            sigs.append({
                "direction": "short",
                "signal": "SPX_DEATH_CROSS",
                "strength": "moderate",
                "reason": f"SMA4 ({t['sma4']}) < SMA13 ({t['sma13']}) gap {t['gap_pct']}%",
            })

        dxy = self.dxy_trend()
        if dxy.get("signal") == "weak_dollar":
            sigs.append({
                "direction": "long",
                "signal": "WEAK_DOLLAR",
                "strength": "moderate",
                "reason": f"DXY broad Z={dxy.get('zscore_52w')} — non-US assets benefit",
            })

        # Filter
        if direction == "all":
            return sigs
        return [s for s in sigs if s["direction"] == direction]

    # ──────────────────────────────────────────────
    # History
    # ──────────────────────────────────────────────
    def history(self, indicator: str, interval: int = 4) -> list:
        """指定インジケーターの履歴をサンプリングして返す"""
        calculators = {
            "yield_curve": lambda s: round((s.get("US10Y", 0) - s.get("US2Y", 0)) * 100)
                if s.get("US10Y") and s.get("US2Y") else None,
            "gold_oil": lambda s: round(s["GOLD"] / s["WTI"], 1)
                if s.get("GOLD") and s.get("WTI") else None,
            "vix_spx": lambda s: round(s["VIX"] / s["SPX"] * 1000, 2)
                if s.get("VIX") and s.get("SPX") else None,
            "smcap_ndx": lambda s: round(s["SMCAP"] / s["NDX"] * 100, 2)
                if s.get("SMCAP") and s.get("NDX") else None,
        }

        # Simple series
        simple_keys = {"spx": "SPX", "ndx": "NDX", "vix": "VIX", "wti": "WTI",
                       "gold": "GOLD", "us10y": "US10Y", "us2y": "US2Y",
                       "dxy": "DXY_BROAD", "smcap": "SMCAP"}

        indicator_lower = indicator.lower()

        if indicator_lower in simple_keys:
            key = simple_keys[indicator_lower]
            calc = lambda s, k=key: s.get(k)
        elif indicator_lower in calculators:
            calc = calculators[indicator_lower]
        else:
            return []

        results = []
        for i in range(0, len(self.snaps), interval):
            s = self.snaps[i]
            val = calc(s)
            if val is not None:
                results.append({"date": s["date"], "value": val})

        return results

    # ──────────────────────────────────────────────
    # Custom Expression
    # ──────────────────────────────────────────────
    def custom(self, expr: str) -> list:
        """カスタム式を全スナップショットに適用"""
        # 安全な変数マッピング
        allowed = {"SPX", "NDX", "SMCAP", "VIX", "WTI", "US10Y", "US2Y",
                   "DXY_BROAD", "GOLD"}
        results = []
        for s in self.snaps:
            local_vars = {k: s.get(k) for k in allowed}
            if any(v is None for v in local_vars.values() if v is not None):
                pass  # some None is ok
            try:
                val = eval(expr, {"__builtins__": {}}, local_vars)
                if val is not None:
                    results.append({"date": s["date"], "value": round(val, 4)})
            except Exception:
                continue
        return results

    # ──────────────────────────────────────────────
    # Full Snapshot (all indicators)
    # ──────────────────────────────────────────────
    def snapshot(self) -> dict:
        """全インジケーターの最新値を一括取得"""
        latest = self._latest()
        return {
            "date": latest.get("date"),
            "prices": {
                "SPX": latest.get("SPX"),
                "NDX": latest.get("NDX"),
                "SMCAP": latest.get("SMCAP"),
                "VIX": latest.get("VIX"),
                "WTI": latest.get("WTI"),
                "GOLD": latest.get("GOLD"),
                "US10Y": latest.get("US10Y"),
                "US2Y": latest.get("US2Y"),
                "DXY_BROAD": latest.get("DXY_BROAD"),
            },
            "yield_curve": self.yield_curve_2s10s(),
            "risk_indicators": {
                "gold_oil_ratio": self.gold_oil_ratio(),
                "gold_spx_ratio": self.gold_spx_ratio(),
                "vix_spx_ratio": self.vix_spx_ratio(),
                "smcap_ndx_ratio": self.smcap_ndx_ratio(),
            },
            "momentum": {
                "spx_4w": self.momentum("SPX", 4),
                "spx_13w": self.momentum("SPX", 13),
                "ndx_4w": self.momentum("NDX", 4),
                "ndx_13w": self.momentum("NDX", 13),
                "gold_13w": self.momentum("GOLD", 13),
            },
            "trend": {
                "spx": self.trend("SPX"),
                "ndx": self.trend("NDX"),
            },
            "volatility": {
                "vix": self.vix_stats(),
                "wti_vol": self.wti_volatility(),
            },
            "dollar": self.dxy_trend(),
            "composite": {
                "crash_risk": self.crash_risk_score(),
                "melt_up_risk": self.melt_up_score(),
            },
            "regime": self.regime(),
            "signals": self.signals(),
            "divergence": self.divergence(),
        }

    # ──────────────────────────────────────────────
    # Markdown Formatters
    # ──────────────────────────────────────────────
    def format_snapshot(self) -> str:
        s = self.snapshot()
        d = s["date"]
        p = s["prices"]
        yc = s["yield_curve"]
        risk = s["risk_indicators"]
        mom = s["momentum"]
        tr = s["trend"]
        vol = s["volatility"]
        dxy = s["dollar"]
        comp = s["composite"]
        reg = s["regime"]

        lines = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f" MARKET INDICATORS [{d}]",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "■ イールドカーブ",
            f"  2s10s: +{yc['value']}bp ({yc['direction']})    4W前: {yc['w4_ago']}bp",
            f"  US10Y: {p['US10Y']}%  Z: {vol['vix'].get('zscore_52w','-')}",
            f"  US2Y:  {p['US2Y']}%",
            "",
            "■ リスクオン/オフ",
            f"  Gold/Oil:     {risk['gold_oil_ratio']['value']}  ({risk['gold_oil_ratio']['interpretation']})  4W前: {risk['gold_oil_ratio']['w4_ago']}",
            f"  Gold/SPX:     {risk['gold_spx_ratio']['value']}  ({risk['gold_spx_ratio']['interpretation']})",
            f"  VIX/SPX*1000: {risk['vix_spx_ratio']['value']}  ({risk['vix_spx_ratio']['signal']})  avg: {risk['vix_spx_ratio']['avg_52w']}",
            f"  SmCap/NDX:    {risk['smcap_ndx_ratio']['value']}%  ({risk['smcap_ndx_ratio']['interpretation']})",
            "",
            "■ モメンタム",
            f"  SPX  4W: {_fmt_pct(mom['spx_4w']['value'])}    13W: {_fmt_pct(mom['spx_13w']['value'])}",
            f"  NDX  4W: {_fmt_pct(mom['ndx_4w']['value'])}    13W: {_fmt_pct(mom['ndx_13w']['value'])}",
            f"  GOLD 13W: {_fmt_pct(mom['gold_13w']['value'])}",
            f"  SPX Trend: {tr['spx']['signal']} (SMA4={tr['spx']['sma4']} vs SMA13={tr['spx']['sma13']})",
            "",
            "■ ボラティリティ",
            f"  VIX: {vol['vix']['value']}  Z: {vol['vix']['zscore_52w']}  Pctl: {vol['vix']['percentile_52w']}%  [{vol['vix']['signal']}]",
            f"  WTI Vol: {vol['wti_vol']['value']}%  [{vol['wti_vol']['signal']}]",
            "",
            "■ ドル",
            f"  DXY Broad: {dxy.get('value','-')}  Z: {dxy.get('zscore_52w','-')}  [{dxy.get('signal','-')}]",
            "",
            "■ 複合スコア",
            f"  Crash Risk:   {comp['crash_risk']['score']}/100 [{comp['crash_risk']['rating']}]",
            f"    {', '.join(c[0] for c in comp['crash_risk']['components'])}",
            f"  Melt-Up Risk: {comp['melt_up_risk']['score']}/100 [{comp['melt_up_risk']['rating']}]",
            f"    {', '.join(c[0] for c in comp['melt_up_risk']['components'])}",
            "",
            f"■ レジーム: {reg['current']} ({reg['risk_off_score']} risk-off conditions)",
            f"  回復進捗: {reg['recovery_progress']}",
            "",
        ]

        # Signals
        sigs = s["signals"]
        if sigs:
            lines.append("■ シグナル")
            for sig in sigs:
                arrow = "▲" if sig["direction"] == "long" else "▼"
                lines.append(f"  {arrow} [{sig['strength']}] {sig['signal']}: {sig['reason']}")
            lines.append("")

        # Divergence
        divs = s["divergence"]
        if divs:
            lines.append("■ FRED vs 記事乖離")
            for dv in divs:
                lines.append(f"  {dv['date']}: FRED {dv['fred_spx']:.0f} vs 記事 {dv['article_spx']:.0f} → {dv['gap_pct']:+.1f}%")
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def format_regime(self) -> str:
        r = self.regime()
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f" REGIME: {r['current']}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            "■ 判定条件",
        ]
        for cond, met in r["conditions"].items():
            mark = "[x]" if met else "[ ]"
            lines.append(f"  {mark} {cond}")

        lines.extend(["", "■ 回復条件"])
        for cond, met in r["recovery_conditions"].items():
            mark = "[x]" if met else "[ ]"
            lines.append(f"  {mark} {cond}")
        lines.append(f"  進捗: {r['recovery_progress']}")

        if r["regime_history"]:
            lines.extend(["", "■ レジーム履歴"])
            for rh in reversed(r["regime_history"]):
                lines.append(f"  {rh.get('period','')}: {rh.get('regime','')}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def format_signals(self, direction: str = "all") -> str:
        sigs = self.signals(direction)
        if not sigs:
            return "シグナルなし"
        lines = ["━━━ SIGNALS ━━━", ""]
        for sig in sigs:
            arrow = "▲ LONG" if sig["direction"] == "long" else "▼ SHORT"
            lines.append(f"{arrow} [{sig['strength']}] {sig['signal']}")
            lines.append(f"  {sig['reason']}")
            lines.append("")
        return "\n".join(lines)

    def format_history(self, indicator: str) -> str:
        hist = self.history(indicator, interval=4)
        if not hist:
            return f"'{indicator}' のデータなし"
        lines = [f"━━━ {indicator.upper()} HISTORY ━━━", ""]
        for h in hist:
            lines.append(f"  {h['date']}:  {h['value']}")
        return "\n".join(lines)

    def to_json(self) -> str:
        """全スナップショットをJSON文字列で返す"""
        return json.dumps(self.snapshot(), ensure_ascii=False, indent=2)


def _fmt_pct(val):
    if val is None:
        return "-"
    sign = "+" if val > 0 else ""
    return f"{sign}{val}%"


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    # data_dirを自動検出
    candidates = [
        Path(".claude/data/market"),
        Path("../../.claude/data/market"),
        Path(__file__).parent.parent.parent / ".claude" / "data" / "market",
    ]
    data_dir = None
    for c in candidates:
        if c.exists():
            data_dir = str(c)
            break

    if not data_dir:
        print("Error: .claude/data/market/ not found")
        sys.exit(1)

    mi = MarketIndicators(data_dir=data_dir)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "snapshot":
        print(mi.format_snapshot())
    elif cmd == "json":
        print(mi.to_json())
    elif cmd == "regime":
        print(mi.format_regime())
    elif cmd == "signal":
        print(mi.format_signals(arg or "all"))
    elif cmd == "history":
        print(mi.format_history(arg or "yield_curve"))
    elif cmd == "custom":
        if arg:
            results = mi.custom(arg)
            for r in results[-10:]:
                print(f"  {r['date']}: {r['value']}")
        else:
            print("Usage: python market_indicators.py custom 'GOLD / WTI'")
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: snapshot, json, regime, signal [long|short], history [indicator], custom 'expr'")
