"""
経済指標データ管理モジュール
経済指標の抽出、保存、検索を行う
"""
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import json


class EconomicDataManager:
    """経済指標データマネージャー"""

    JST = timezone(timedelta(hours=9))

    # 主要経済指標のマッピング
    INDICATORS = {
        # 雇用
        'NFP': {'name': 'Nonfarm Payrolls', 'unit': 'K', 'category': 'Employment'},
        'Unemployment': {'name': 'Unemployment Rate', 'unit': '%', 'category': 'Employment'},
        'JOLTS': {'name': 'Job Openings', 'unit': 'M', 'category': 'Employment'},
        'AHE': {'name': 'Average Hourly Earnings', 'unit': '%YoY', 'category': 'Employment'},
        'Claims': {'name': 'Initial Jobless Claims', 'unit': 'K', 'category': 'Employment'},

        # インフレ
        'CPI': {'name': 'Consumer Price Index', 'unit': '%MoM', 'category': 'Inflation'},
        'Core CPI': {'name': 'Core CPI', 'unit': '%MoM', 'category': 'Inflation'},
        'PPI': {'name': 'Producer Price Index', 'unit': '%MoM', 'category': 'Inflation'},
        'Core PPI': {'name': 'Core PPI', 'unit': '%MoM', 'category': 'Inflation'},
        'PCE': {'name': 'PCE Price Index', 'unit': '%MoM', 'category': 'Inflation'},
        'Core PCE': {'name': 'Core PCE', 'unit': '%MoM', 'category': 'Inflation'},
        'Supercore': {'name': 'Supercore Services', 'unit': '%MoM', 'category': 'Inflation'},

        # 経済活動
        'GDP': {'name': 'GDP Growth', 'unit': '%QoQ', 'category': 'Growth'},
        'Retail Sales': {'name': 'Retail Sales', 'unit': '%MoM', 'category': 'Growth'},
        'ISM Mfg': {'name': 'ISM Manufacturing PMI', 'unit': 'index', 'category': 'Growth'},
        'ISM Services': {'name': 'ISM Services PMI', 'unit': 'index', 'category': 'Growth'},
        'Industrial Production': {'name': 'Industrial Production', 'unit': '%MoM', 'category': 'Growth'},

        # 住宅
        'Housing Starts': {'name': 'Housing Starts', 'unit': 'K', 'category': 'Housing'},
        'Existing Home Sales': {'name': 'Existing Home Sales', 'unit': 'M', 'category': 'Housing'},
        'Home Prices': {'name': 'Home Price Index', 'unit': '%YoY', 'category': 'Housing'},

        # 金融市場
        'VIX': {'name': 'VIX Volatility Index', 'unit': 'pts', 'category': 'Market'},
        '10Y': {'name': '10-Year Treasury Yield', 'unit': '%', 'category': 'Market'},
        '2Y': {'name': '2-Year Treasury Yield', 'unit': '%', 'category': 'Market'},
        'DXY': {'name': 'Dollar Index', 'unit': 'pts', 'category': 'Market'},
    }

    @staticmethod
    def extract_indicator_data(text: str) -> Optional[Dict[str, Any]]:
        """
        テキストから経済指標データを抽出

        例: "PPI 0.8%でコンセンサス0.3%上振れ"
        → {'indicator': 'PPI', 'actual': 0.8, 'consensus': 0.3, ...}
        """
        text_upper = text.upper()

        # 指標名を検出
        indicator_found = None
        for key in EconomicDataManager.INDICATORS.keys():
            if key.upper() in text_upper:
                indicator_found = key
                break

        if not indicator_found:
            return None

        # 数値を抽出（簡易版 - 実際はもっと複雑なパターンマッチングが必要）
        import re

        # パターン: "0.8%", "130K", "3.95%"など
        numbers = re.findall(r'[-+]?\d*\.?\d+%?[KMB]?', text)

        result = {
            'indicator': indicator_found,
            'indicator_name': EconomicDataManager.INDICATORS[indicator_found]['name'],
            'category': EconomicDataManager.INDICATORS[indicator_found]['category'],
            'raw_text': text,
            'detected_values': numbers,
            'timestamp': datetime.now(EconomicDataManager.JST).isoformat()
        }

        # キーワードベースで値を分類
        text_lower = text.lower()
        if 'コンセンサス' in text_lower or '予想' in text_lower or 'consensus' in text_lower:
            result['has_consensus'] = True
        if '前回' in text_lower or '前月' in text_lower or 'previous' in text_lower:
            result['has_previous'] = True

        return result

    @staticmethod
    def format_indicator_summary(data: Dict[str, Any]) -> str:
        """指標データをサマリー形式で出力"""
        indicator = data.get('indicator', 'Unknown')
        name = data.get('indicator_name', indicator)
        values = data.get('detected_values', [])

        summary = f"📊 {name} ({indicator})\n"
        if values:
            summary += f"検出値: {', '.join(values)}\n"
        summary += f"カテゴリ: {data.get('category', 'N/A')}\n"
        summary += f"記録時刻: {data.get('timestamp', 'N/A')}\n"

        return summary

    @staticmethod
    def get_historical_data(
        indicators_data: List[Dict[str, Any]],
        indicator_name: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """特定の指標の過去データを取得"""
        filtered = [
            d for d in indicators_data
            if d.get('indicator') == indicator_name
        ]
        # 新しい順にソート
        filtered.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return filtered[:limit]

    @staticmethod
    def generate_discussion_prompt(
        indicator_data: Dict[str, Any],
        user_interpretation: str,
        historical_data: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """考察を深めるための対話プロンプトを生成"""
        indicator = indicator_data.get('indicator', 'Unknown')
        name = indicator_data.get('indicator_name', indicator)
        category = indicator_data.get('category', 'N/A')

        prompt = f"""ユーザーが経済指標について考察を述べています。
指標の理解を深めるために、以下の観点で質問や追加視点を提供してください。

## 指標情報
- 指標: {name} ({indicator})
- カテゴリ: {category}
- 入力データ: {indicator_data.get('raw_text', 'N/A')}

## ユーザーの解釈
{user_interpretation}

## 議論を深めるポイント
1. **メカニズム理解**: なぜその数値になったのか？構造的要因は？
2. **波及効果**: 他の指標やマーケットへの影響は？
3. **トレンド**: 過去の推移と比較してどうか？
4. **政策インプリケーション**: FRBの判断にどう影響するか？
5. **矛盾点の指摘**: 他のデータと矛盾していないか？

## 対話スタイル
- ユーザーの解釈を尊重しつつ、見落としている視点を提示
- 質問形式で思考を促す
- データや理論に基づく客観的な議論
- 簡潔に（3-5文程度）

以下、考察の深掘りを開始してください。"""

        return prompt
