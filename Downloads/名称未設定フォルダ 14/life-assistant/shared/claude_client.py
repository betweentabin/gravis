"""
Claude API クライアント
メッセージ分類、分析、レビュー生成を行う
"""
import json
from typing import Optional, List, Dict, Any
import anthropic

from .config import Config


class ClaudeClient:
    """Claude API クライアント"""

    def __init__(self, config: Optional[Config] = None):
        if config is None:
            from .config import get_config
            config = get_config()
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.model = config.claude_model

    def _parse_json_response(self, content: str) -> Dict[str, Any]:
        """レスポンスからJSONを抽出してパース"""
        try:
            # コードブロックを除去
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]

            return json.loads(content.strip())
        except json.JSONDecodeError:
            return {}

    def classify_message(self, message: str) -> Dict[str, Any]:
        """メッセージを分類"""
        prompt = f"""あなたは知識管理システムの分類AIです。
ユーザーのメッセージを以下の4つのカテゴリに分類してください。

## カテゴリ
1. diary (日記): 日々の出来事、感情、振り返り、個人的な体験
2. learning (学習メモ): 学んだこと、技術的な内容、読書メモ、新しい知識
3. idea (アイデア): 新しいアイデア、企画、改善提案、ひらめき
4. task (タスク): やるべきこと、TODO、リマインダー、予定

## 出力形式 (JSON)
{{
  "category": "diary|learning|idea|task",
  "confidence": 0.0-1.0,
  "tags": ["タグ1", "タグ2", "タグ3"],
  "summary": "1行の簡潔な要約（20文字以内）",
  "extracted_data": {{}}
}}

## カテゴリ固有のextracted_data
- diary: {{"mood": "positive|neutral|negative"}}
- learning: {{"topic": "トピック名", "difficulty": "beginner|intermediate|advanced"}}
- idea: {{"priority": "low|medium|high", "status": "draft"}}
- task: {{"priority": "low|medium|high", "due_date": "YYYY-MM-DD or null"}}

## ユーザーメッセージ
{message}

JSONのみを出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        result = self._parse_json_response(content)

        # デフォルト値を設定
        if not result or "category" not in result:
            return {
                "category": "diary",
                "confidence": 0.5,
                "tags": [],
                "summary": message[:20] if len(message) > 20 else message,
                "extracted_data": {"mood": "neutral"}
            }

        return result

    def analyze_content(self, content: str, content_type: str) -> Dict[str, Any]:
        """コンテンツを分析"""
        prompts = {
            "diary": """日記の内容を分析し、以下をJSON形式で出力してください：
- mood: 感情トーン (positive/neutral/negative)
- key_topics: 主要なトピック（リスト、最大3つ）
- tags: 適切なタグ（リスト、最大5つ）
- insights: 気づきや重要なポイント（1文）""",

            "learning": """学習メモを分析し、以下をJSON形式で出力してください：
- topic: 学習トピック
- difficulty: 難易度 (beginner/intermediate/advanced)
- key_concepts: キーコンセプト（リスト、最大5つ）
- tags: 適切なタグ（リスト、最大5つ）
- next_steps: 次のステップ提案（リスト、最大3つ）""",

            "idea": """アイデアを分析し、以下をJSON形式で出力してください：
- category: アイデアのカテゴリ
- priority: 優先度 (low/medium/high)
- tags: 適切なタグ（リスト、最大5つ）
- action_items: 次のアクション候補（リスト、最大3つ）
- potential: このアイデアの可能性についての短評（1文）""",

            "task": """タスクを分析し、以下をJSON形式で出力してください：
- priority: 緊急度 (low/medium/high)
- estimated_time: 推定所要時間（例: "30分", "2時間"）
- tags: 適切なタグ（リスト、最大5つ）
- subtasks: サブタスクへの分解案（リスト、最大5つ）
- due_date: 期限の示唆（あれば、YYYY-MM-DD形式、なければnull）"""
        }

        analysis_prompt = prompts.get(content_type, prompts["diary"])

        prompt = f"""{analysis_prompt}

## 内容
{content}

JSONのみを出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        content_text = response.content[0].text
        result = self._parse_json_response(content_text)

        if not result:
            return {"tags": [], "error": "parse_failed"}

        return result

    def generate_weekly_review(
        self,
        entries: List[Dict[str, Any]],
        week_info: Dict[str, Any]
    ) -> str:
        """週次レビューを生成"""
        entries_json = json.dumps(entries, ensure_ascii=False, indent=2)

        prompt = f"""以下の1週間のデータから週次レビューを生成してください。

## 週の情報
- 年: {week_info['year']}
- 週番号: {week_info['week']}
- 期間: {week_info['start_date']} ～ {week_info['end_date']}

## 今週のエントリ
{entries_json}

## 出力形式（Markdown）
以下の構成で週次レビューを生成してください：

1. **サマリー**: 今週を2-3文で総括
2. **統計**: カテゴリ別の件数をテーブルで表示
3. **ハイライト**:
   - 学習: 今週学んだ主要なこと
   - 達成: 完了したタスクや成果
   - アイデア: 生まれたアイデア
4. **気づき・振り返り**: 傾向や改善点
5. **来週のフォーカス**: 優先すべきこと3つ

YAMLフロントマターは不要です。Markdownの本文のみ出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def generate_monthly_review(
        self,
        entries: List[Dict[str, Any]],
        weekly_reviews: List[Dict[str, Any]],
        month_info: Dict[str, Any]
    ) -> str:
        """月次レビューを生成"""
        # エントリのサマリーを作成（大量の場合は概要のみ）
        entry_summary = {
            "total": len(entries),
            "by_type": {},
            "top_tags": {},
            "sample_entries": entries[:20]  # サンプルとして最初の20件
        }

        for entry in entries:
            entry_type = entry.get("type", "unknown")
            entry_summary["by_type"][entry_type] = entry_summary["by_type"].get(entry_type, 0) + 1
            for tag in entry.get("tags", []):
                entry_summary["top_tags"][tag] = entry_summary["top_tags"].get(tag, 0) + 1

        # トップタグを上位10件に絞る
        sorted_tags = sorted(entry_summary["top_tags"].items(), key=lambda x: x[1], reverse=True)[:10]
        entry_summary["top_tags"] = dict(sorted_tags)

        prompt = f"""以下の1ヶ月のデータから月次レビューを生成してください。

## 月の情報
- 年: {month_info['year']}
- 月: {month_info['month']}

## 週次レビューサマリー
{json.dumps(weekly_reviews, ensure_ascii=False, indent=2)}

## 今月のエントリ概要
{json.dumps(entry_summary, ensure_ascii=False, indent=2)}

## 出力形式（Markdown）
以下の構成で月次レビューを生成してください：

1. **月間サマリー**: 今月の総括（3-4文）
2. **月間統計**:
   - カテゴリ別件数
   - 週ごとの推移（もしデータがあれば）
   - よく使われたタグTop5
3. **成長と学び**:
   - 今月習得したスキル/知識
   - 印象に残った学習
4. **プロジェクト進捗**:
   - 完了したこと
   - 進行中のこと
5. **アイデアの棚卸し**:
   - 実行に移したアイデア
   - 保留中の有望なアイデア
6. **来月の目標**:
   - フォーカスエリア
   - 具体的なアクション3つ

YAMLフロントマターは不要です。Markdownの本文のみ出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def chat(
        self,
        message: str,
        context: Dict[str, Any] = None,
        recent_entries: List[Dict[str, Any]] = None
    ) -> str:
        """
        会話型応答を生成

        Args:
            message: ユーザーのメッセージ
            context: コンテキスト情報（ユーザー設定など）
            recent_entries: 最近の記録エントリ

        Returns:
            AIの応答テキスト
        """
        # コンテキスト情報を構築
        context_info = ""
        if recent_entries:
            entries_summary = []
            for entry in recent_entries[:10]:  # 最新10件まで
                entry_type = entry.get('type', 'unknown')
                date = entry.get('date', '不明')
                tags = ', '.join(entry.get('tags', [])[:3])
                summary = entry.get('summary', entry.get('title', ''))[:50]
                entries_summary.append(f"- [{entry_type}] {date}: {summary} (タグ: {tags})")

            context_info = f"""

## ユーザーの最近の記録（参考情報）
{chr(10).join(entries_summary)}
"""

        system_prompt = f"""あなたは「Life Assistant」という名前のパーソナルアシスタントAIです。
ユーザーの生活の質を向上させるために、以下の役割を果たします：

## あなたの役割
1. **会話相手**: 自然で親しみやすい会話をします
2. **記憶の活用**: ユーザーの過去の記録を参照して、文脈を理解した返答をします
3. **アドバイザー**: 生活改善のヒントや気づきを提供します
4. **励まし**: ポジティブなサポートを提供します

## 応答のルール
- 200文字以内で簡潔に返答（LINE向け）
- 親しみやすいが、過度にカジュアルにはしない
- 質問には具体的に答える
- 過去の記録に関連する話題があれば、それを踏まえて返答
- 必要に応じて生活改善のアドバイスを添える
- 記録を促す場合は自然に提案する

## 注意
- 記録の保存が必要な内容の場合は、保存を提案してください
- 質問や会話だけの場合は、保存せずに会話を楽しんでください
{context_info}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": message}]
        )

        return response.content[0].text

    def should_save_message(self, message: str) -> Dict[str, Any]:
        """
        メッセージを保存すべきか判定

        Returns:
            {
                "should_save": bool,
                "reason": str,
                "suggested_category": str or None
            }
        """
        prompt = f"""以下のメッセージを分析して、知識管理システムに保存すべきかを判定してください。

## 保存すべきもの
- 日記・振り返り（今日の出来事、感想など）
- 学習メモ（学んだこと、技術的な内容）
- アイデア・ひらめき
- タスク・TODO・予定

## 保存しないもの
- 単純な質問（「今何時？」「明日の天気は？」）
- 雑談・挨拶（「こんにちは」「元気？」）
- AIへの指示・リクエスト（「〇〇について教えて」）
- 確認（「先週何したっけ？」「タスクを見せて」）

## メッセージ
{message}

## 出力形式（JSON）
{{
  "should_save": true/false,
  "reason": "判定理由（10文字以内）",
  "suggested_category": "diary/learning/idea/task/null"
}}

JSONのみを出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        result = self._parse_json_response(content)

        if not result or "should_save" not in result:
            # デフォルトは保存する（安全側に倒す）
            return {
                "should_save": True,
                "reason": "判定不能",
                "suggested_category": None
            }

        return result

    def generate_advice(
        self,
        entries: List[Dict[str, Any]],
        focus_area: str = None
    ) -> str:
        """
        記録に基づいてアドバイスを生成

        Args:
            entries: 分析対象のエントリ
            focus_area: フォーカスエリア（health, productivity, learning等）

        Returns:
            アドバイステキスト
        """
        if not entries:
            return "まだ記録がないため、アドバイスを生成できません。日々の出来事や学びを記録してみましょう！"

        entries_json = json.dumps(entries[:20], ensure_ascii=False, indent=2)

        focus_prompt = ""
        if focus_area:
            focus_prompt = f"\n特に「{focus_area}」に関するアドバイスを重点的にお願いします。"

        prompt = f"""以下のユーザーの記録を分析し、生活改善のアドバイスを生成してください。

## ユーザーの記録
{entries_json}

## 指示
- 記録のパターンや傾向を分析
- 具体的で実行可能なアドバイスを3つ提供
- ポジティブな視点で、励ましを含める
- 200文字以内で簡潔に{focus_prompt}

アドバイスを出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def generate_market_summary(self) -> str:
        """蓄積記事の統合マーケット分析を生成"""
        prompt = """あなたはヘッジファンドのマーケットストラテジストです。
以下の3つの記事を統合分析し、投資判断を提供してください。

## 蓄積記事

### 記事1: L氏（元マルチ戦略HF PM）2026/2/26
- 主張: 市場はコンベックスをショートしており、上方向の急騰リスクが最大の危険
- 推奨: ソフトウェアロング、上方コンベクシティ確保
- キーファクター: ソフトウェアポジション歴史的下限、売り枯渇、自社株買い80%未実行

### 記事2: kokko氏 2026/2/15「時計仕掛けの摩天楼」
- 主張: 米国は循環的拡大局面だが、フロー要因による「事故」リスク積み上げ
- 推奨: プロテクション追加、レバレッジ解消、地域分散
- キーファクター: DSPX 99%タイル、VIXショート歴史的水準、台湾輸出+70%

### 記事3: kokko氏 2026/2/8「過剰解釈は禁物」
- 主張: ファンダは強いが市場の動きに違和感。マージンコール連鎖仮説
- 推奨: 慎重維持、プロテクション継続
- キーファクター: ISM製造業52.5、新規受注過去25年最大変化、QRA SOMA購入文言

## 最新データ (3/1時点)
- VIX: 19.86、CFTC VIXネットショート: -71,817枚
- DSPX: 35.92 (99%タイル継続)
- 金: $5,226 (史上最高値)
- IGV: $81.57 (-21.6% YTD)
- AAII弱気: 39.8%

## 出力形式（500文字以内、LINE向け）
1. コンセンサス（3者一致点）
2. 乖離点
3. 結論：株式/貴金属の方向性
4. 今週のアクション"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def analyze_market_article(self, article: str) -> str:
        """マーケット記事を分析"""
        prompt = f"""あなたはヘッジファンドのマーケットストラテジストです。
以下の記事を分析し、投資判断材料を抽出してください。

## 記事
{article[:3000]}

## 出力形式（500文字以内、LINE向け）
1. **主張**: 核心的主張（1文）
2. **推奨ポジション**: 著者の推奨
3. **キーファクター**: 重要な数値/事実（3つ）
4. **リスク評価**: 上方/下方リスク
5. **アクション示唆**: 具体的な投資行動

簡潔に出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def parse_intent(self, message: str) -> Dict[str, Any]:
        """
        ユーザーメッセージから意図を解析し、適切なコマンドを推測

        Returns:
            {
                "intent": "command|save|chat",
                "command": コマンド名 or None,
                "params": パラメータ or None,
                "confidence": 0.0-1.0
            }
        """
        prompt = f"""ユーザーのメッセージから意図を解析してください。

## 対応可能なコマンド
- market_summary: マーケット分析のサマリー表示
- market_data: 最新のマーケットデータ取得
- market_save: マーケット記事を保存
- market_list: 保存済み記事一覧
- market_analyze: 新規記事を分析
- diary: 日記として保存
- learning: 学習メモとして保存
- idea: アイデアとして保存
- task: タスクとして保存
- stats: 統計情報表示
- help: ヘルプ表示
- chat: 単なる会話（保存不要）

## ユーザーメッセージ
{message}

## 出力形式（JSON）
{{
  "intent": "command|save|chat",
  "command": "コマンド名 or null",
  "params": "パラメータ or null",
  "confidence": 0.0-1.0,
  "reason": "判定理由（10文字以内）"
}}

## 判定ルール
- 明確なコマンド（/で始まる）→ intent: "command"
- マーケット/市場/相場/分析 → market系コマンド
- サマリー/まとめ/統合/総合 → market_summary
- データ/最新/現在 → market_data
- 保存/記録/蓄積 → save系
- 統計/数値/レポート → stats
- 質問/会話/挨拶 → chat
- その他の記録すべき内容 → save系

JSONのみを出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        result = self._parse_json_response(content)

        if not result or "intent" not in result:
            return {
                "intent": "chat",
                "command": None,
                "params": None,
                "confidence": 0.5,
                "reason": "解析失敗"
            }

        return result

    def discuss_economic_indicator(
        self,
        indicator_data: Dict[str, Any],
        user_interpretation: str,
        historical_context: Optional[str] = None
    ) -> str:
        """
        経済指標についてユーザーの考察を深める対話を生成

        Args:
            indicator_data: 経済指標データ（指標名、カテゴリ、数値等）
            user_interpretation: ユーザーの解釈・考察
            historical_context: 過去データや関連情報（オプション）

        Returns:
            考察を深めるための応答
        """
        from .economic_data import EconomicDataManager

        prompt = EconomicDataManager.generate_discussion_prompt(
            indicator_data,
            user_interpretation,
            None  # TODO: 過去データの活用
        )

        # 過去の文脈があれば追加
        if historical_context:
            prompt += f"\n\n## 過去データ・関連情報\n{historical_context}"

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def extract_economic_indicator(self, text: str) -> Optional[Dict[str, Any]]:
        """
        テキストから経済指標データを抽出（Claude APIを使用した高精度版）

        Args:
            text: ユーザー入力テキスト

        Returns:
            抽出された指標データ、または None
        """
        prompt = f"""以下のテキストから経済指標データを抽出してください。

## テキスト
{text}

## 出力形式（JSON）
{{
  "has_indicator": true/false,
  "indicator": "指標名（PPI, CPI, NFP等）",
  "indicator_full_name": "完全な指標名",
  "category": "Inflation|Employment|Growth|Housing|Market",
  "actual": 数値 or null,
  "consensus": 予想値 or null,
  "previous": 前回値 or null,
  "unit": "単位（%MoM, K, M等）",
  "interpretation": "ユーザーの解釈・考察部分（抽出）",
  "confidence": 0.0-1.0
}}

## 抽出ルール
- 数値は数値型で出力（文字列でない）
- "コンセンサス"、"予想"、"見通し" → consensus
- "前回"、"前月"、"先月" → previous
- 解釈部分: 「これって〜」「〜だと思う」「〜の可能性」等の考察
- 経済指標が含まれていない場合は has_indicator: false

JSONのみを出力してください。"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text
        result = self._parse_json_response(content)

        if not result or not result.get('has_indicator', False):
            return None

        return result
