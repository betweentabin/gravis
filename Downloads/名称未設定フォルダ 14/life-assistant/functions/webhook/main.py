"""
LINE Webhook Handler
LINEからのWebhookを受信し、メッセージを処理する
"""
import sys
import os

# 共有モジュールへのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import functions_framework
import json
import asyncio
from typing import Dict, Any
from flask import Request, abort

from shared.config import get_config
from shared.line_client import LineClient
from shared.github_client import GitHubClient
from shared.classifier import MessageClassifier
from shared.formatter import MarkdownFormatter
from shared.claude_client import ClaudeClient


# グローバルインスタンス（コールドスタート対策）
config = None
line_client = None
github_client = None
classifier = None
formatter = None
claude_client = None
slide_generator = None
file_sharer = None


def get_clients():
    """クライアントインスタンスを取得（遅延初期化）"""
    global config, line_client, github_client, classifier, formatter, claude_client

    if config is None:
        config = get_config()
        line_client = LineClient(config)
        github_client = GitHubClient(config)
        classifier = MessageClassifier(config)
        formatter = MarkdownFormatter()
        claude_client = ClaudeClient(config)

    return config, line_client, github_client, classifier, formatter, claude_client


def get_slide_clients():
    """スライド関連クライアントを遅延初期化"""
    global slide_generator, file_sharer, config

    if config is None:
        config = get_config()

    if slide_generator is None:
        from shared.slide_generator import SlideGenerator
        from shared.email_sender import FileSharer
        slide_generator = SlideGenerator(config)
        file_sharer = FileSharer(config)

    return slide_generator, file_sharer


@functions_framework.http
def webhook(request: Request):
    """
    LINE Webhook エンドポイント

    POST /webhook
    Headers:
        X-Line-Signature: 署名
    Body:
        LINE Webhook Event
    """
    _, line, _, _, _, _ = get_clients()

    # 署名検証
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data()

    if not line.verify_signature(body, signature):
        print("Invalid signature")
        abort(403)

    # イベント処理
    try:
        events = json.loads(body).get('events', [])

        for event in events:
            asyncio.run(handle_event(event))

        return 'OK', 200

    except Exception as e:
        print(f"Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return 'Internal Server Error', 500


async def handle_event(event: dict):
    """イベントハンドラー"""
    event_type = event.get('type')

    if event_type == 'message':
        await handle_message(event)
    elif event_type == 'follow':
        await handle_follow(event)
    elif event_type == 'unfollow':
        await handle_unfollow(event)


async def handle_message(event: dict):
    """メッセージイベントの処理"""
    _, line, github, clf, fmt, claude = get_clients()

    message = event.get('message', {})
    reply_token = event.get('replyToken')
    user_id = event['source'].get('userId')

    if message.get('type') != 'text':
        await line.reply_text(
            reply_token,
            "現在はテキストメッセージのみ対応しています。"
        )
        return

    text = message.get('text', '').strip()
    message_id = message.get('id', '')

    # コマンド処理（/で始まる明確なコマンド）
    if text.startswith('/'):
        result = await handle_command(text, user_id, message_id)
        await line.reply_text(reply_token, result)
        return

    # 自然言語での意図解釈を試みる
    print(f"[DEBUG] Parsing intent for message: {text[:50]}...")
    intent_result = claude.parse_intent(text)
    print(f"[DEBUG] Intent result: {intent_result}")

    # 意図が明確なコマンドの場合
    if intent_result.get('intent') == 'command' and intent_result.get('confidence', 0) > 0.7:
        command = intent_result.get('command')
        params = intent_result.get('params', '')

        print(f"[DEBUG] Detected command: {command}, params: {params}")

        # コマンドを実行
        if command == 'market_summary':
            result = await generate_market_summary(user_id)
            await line.reply_text(reply_token, result)
            return
        elif command == 'market_data':
            result = await fetch_market_data(user_id)
            await line.reply_text(reply_token, result)
            return
        elif command == 'market_list':
            result = await list_market_articles(user_id)
            await line.reply_text(reply_token, result)
            return
        elif command == 'market_save' and params:
            result = await save_market_article(params, user_id)
            await line.reply_text(reply_token, result)
            return
        elif command == 'market_analyze' and params:
            result = await analyze_market_article(params, user_id)
            await line.reply_text(reply_token, result)
            return
        elif command == 'stats':
            result = await show_stats(user_id)
            await line.reply_text(reply_token, result)
            return
        elif command == 'help':
            result = await show_help()
            await line.reply_text(reply_token, result)
            return

    # 経済指標の検出と処理（自然言語対応）
    indicator_data = claude.extract_economic_indicator(text)
    if indicator_data and indicator_data.get('confidence', 0) > 0.7:
        print(f"[DEBUG] Economic indicator detected: {indicator_data}")
        result = await handle_economic_indicator(indicator_data, user_id, reply_token)
        await line.reply_text(reply_token, result)
        return

    # メッセージを保存すべきか判定
    save_check = claude.should_save_message(text)

    if save_check.get('should_save', True):
        # 保存が必要な場合は従来の自動分類処理
        await process_message(text, reply_token, user_id, message_id)
    else:
        # 会話モード：保存せずに返答
        await process_chat(text, reply_token, user_id)


async def handle_command(text: str, user_id: str, message_id: str) -> str:
    """コマンドの処理"""
    print(f"[DEBUG] handle_command: text='{text}'")
    parts = text.split(' ', 1)
    command = parts[0].lower()
    content = parts[1].strip() if len(parts) > 1 else ''
    print(f"[DEBUG] handle_command: command='{command}', content='{content}'")

    handlers = {
        '/diary': lambda: save_as_type('diary', content, user_id, message_id),
        '/learn': lambda: save_as_type('learning', content, user_id, message_id),
        '/idea': lambda: save_as_type('idea', content, user_id, message_id),
        '/task': lambda: save_as_type('task', content, user_id, message_id),
        '/done': lambda: complete_task(content, user_id),
        '/review': lambda: show_review(content, user_id),
        '/search': lambda: search_entries(content, user_id),
        '/stats': lambda: show_stats(user_id),
        '/advice': lambda: show_advice(content, user_id),
        '/slide': lambda: generate_slide(content, user_id),
        '/market': lambda: handle_market_analysis(content, user_id),
        '/help': lambda: show_help(),
    }

    print(f"[DEBUG] Available commands: {list(handlers.keys())}")
    print(f"[DEBUG] Command in handlers: {command in handlers}")

    handler = handlers.get(command)
    if handler:
        print(f"[DEBUG] Calling handler for command: {command}")
        return await handler()
    else:
        print(f"[DEBUG] Unknown command: {command}")
        return await show_unknown_command()


async def process_chat(text: str, reply_token: str, user_id: str):
    """会話モード：保存せずにAIと対話"""
    _, line, github, _, _, claude = get_clients()

    try:
        # 最近の記録を取得してコンテキストとして使用
        recent_entries = await github.get_recent_entries(limit=10)

        # Claude で返答を生成
        response = claude.chat(
            message=text,
            context={"user_id": user_id},
            recent_entries=recent_entries
        )

        await line.reply_text(reply_token, response)

    except Exception as e:
        print(f"Error in chat mode: {e}")
        import traceback
        traceback.print_exc()
        await line.reply_text(reply_token, "すみません、うまく返答できませんでした。")


async def process_message(text: str, reply_token: str, user_id: str, message_id: str):
    """メッセージの自動分類と保存"""
    _, line, github, clf, fmt, _ = get_clients()

    try:
        # Claude APIで分類
        classification = clf.classify(text)

        # メタデータ準備
        metadata = {
            'tags': classification.get('tags', []),
            'summary': classification.get('summary', ''),
            'title': classification.get('summary', ''),
            'line_message_id': message_id,
            'extracted_data': classification.get('extracted_data', {})
        }

        # Markdown生成
        markdown = fmt.format_entry(
            entry_type=classification['category'],
            content=text,
            metadata=metadata
        )

        # ファイルパス生成
        file_path = fmt.generate_file_path(
            classification['category'],
            title=classification.get('summary', '')
        )

        # GitHubに保存
        await github.create_or_update_file(file_path, markdown)

        # インデックス更新
        entry_id = fmt.generate_entry_id(classification['category'])
        await github.update_index({
            'id': entry_id,
            'type': classification['category'],
            'path': file_path,
            'date': fmt.JST.localize(fmt.datetime.now()).strftime("%Y-%m-%d") if hasattr(fmt, 'datetime') else __import__('datetime').datetime.now(fmt.JST).strftime("%Y-%m-%d"),
            'tags': classification.get('tags', []),
            'created_at': __import__('datetime').datetime.now(fmt.JST).isoformat()
        })

        # 確認メッセージ
        category_names = {
            'diary': '日記',
            'learning': '学習メモ',
            'idea': 'アイデア',
            'task': 'タスク'
        }

        reply_message = f"""保存しました!

カテゴリ: {category_names.get(classification['category'], classification['category'])}
タグ: {', '.join(classification.get('tags', [])) or 'なし'}
要約: {classification.get('summary', '')}

別のカテゴリで保存したい場合：
/diary, /learn, /idea, /task"""

        await line.reply_text(reply_token, reply_message)

    except Exception as e:
        print(f"Error processing message: {e}")
        import traceback
        traceback.print_exc()
        await line.reply_text(reply_token, f"エラーが発生しました。もう一度お試しください。")


async def save_as_type(entry_type: str, content: str, user_id: str, message_id: str) -> str:
    """指定されたタイプで保存"""
    if not content:
        type_names = {
            'diary': '日記',
            'learning': '学習メモ',
            'idea': 'アイデア',
            'task': 'タスク'
        }
        return f"保存する内容を入力してください。\n例: /{entry_type.replace('learning', 'learn')} {type_names.get(entry_type, '')}の内容"

    _, _, github, clf, fmt, _ = get_clients()

    try:
        # 分析（タグ抽出など）
        analysis = clf.analyze(content, entry_type)

        # メタデータ準備
        metadata = {
            'tags': analysis.get('tags', []),
            'summary': clf.extract_title(content, entry_type),
            'title': clf.extract_title(content, entry_type),
            'line_message_id': message_id,
            'extracted_data': analysis
        }

        # Markdown生成
        markdown = fmt.format_entry(
            entry_type=entry_type,
            content=content,
            metadata=metadata
        )

        # ファイルパス生成
        file_path = fmt.generate_file_path(entry_type, title=metadata['title'])

        # GitHubに保存
        await github.create_or_update_file(file_path, markdown)

        # インデックス更新
        from datetime import datetime
        entry_id = fmt.generate_entry_id(entry_type)
        await github.update_index({
            'id': entry_id,
            'type': entry_type,
            'path': file_path,
            'date': datetime.now(fmt.JST).strftime("%Y-%m-%d"),
            'tags': analysis.get('tags', []),
            'created_at': datetime.now(fmt.JST).isoformat()
        })

        category_names = {
            'diary': '日記',
            'learning': '学習メモ',
            'idea': 'アイデア',
            'task': 'タスク'
        }

        return f"{category_names.get(entry_type, entry_type)}として保存しました!\nタグ: {', '.join(analysis.get('tags', [])) or 'なし'}"

    except Exception as e:
        print(f"Error saving as {entry_type}: {e}")
        import traceback
        traceback.print_exc()
        return "保存中にエラーが発生しました。"


async def complete_task(task_name: str, user_id: str) -> str:
    """タスクを完了にする"""
    if not task_name:
        return "完了するタスク名を入力してください。\n例: /done 資料作成"

    _, _, github, _, _, _ = get_clients()

    try:
        result = await github.complete_task(task_name)

        if result:
            return f"タスク「{task_name}」を完了しました!"
        else:
            return f"タスク「{task_name}」が見つかりませんでした。"

    except Exception as e:
        print(f"Error completing task: {e}")
        return "タスク完了処理中にエラーが発生しました。"


async def show_review(period: str, user_id: str) -> str:
    """レビューを表示"""
    _, _, github, _, _, _ = get_clients()

    try:
        period_lower = period.lower() if period else ""

        if period_lower in ['week', 'weekly', '週']:
            review = await github.get_latest_weekly_review()
            if review:
                # 長い場合は切り詰め
                if len(review) > 2000:
                    review = review[:1997] + "..."
                return review
            return "週次レビューがまだありません。"

        elif period_lower in ['month', 'monthly', '月']:
            review = await github.get_latest_monthly_review()
            if review:
                if len(review) > 2000:
                    review = review[:1997] + "..."
                return review
            return "月次レビューがまだありません。"

        else:
            return "期間を指定してください。\n例: /review week または /review month"

    except Exception as e:
        print(f"Error showing review: {e}")
        return "レビュー取得中にエラーが発生しました。"


async def search_entries(query: str, user_id: str) -> str:
    """エントリを検索"""
    if not query:
        return "検索キーワードを入力してください。\n例: /search Python"

    _, _, github, _, _, _ = get_clients()

    try:
        results = await github.search_entries(query)

        if not results:
            return f"「{query}」に一致するエントリが見つかりませんでした。"

        response = f"「{query}」の検索結果:\n\n"
        for i, result in enumerate(results[:5], 1):
            tags = ', '.join(result.get('tags', [])[:3])
            response += f"{i}. [{result['type']}] {result.get('title', '無題')}\n"
            response += f"   日付: {result.get('date', '不明')}\n"
            if tags:
                response += f"   タグ: {tags}\n"
            response += "\n"

        return response.strip()

    except Exception as e:
        print(f"Error searching: {e}")
        return "検索中にエラーが発生しました。"


async def show_stats(user_id: str) -> str:
    """統計を表示"""
    _, _, github, _, _, _ = get_clients()

    try:
        stats = await github.get_stats()

        top_tags = stats.get('top_tags', [])[:5]
        tags_str = ', '.join(top_tags) if top_tags else 'なし'

        return f"""統計情報

総エントリ数: {stats['total']}件
- 日記: {stats['diary']}件
- 学習メモ: {stats['learning']}件
- アイデア: {stats['ideas']}件
- タスク: {stats['tasks']}件 (完了: {stats['tasks_completed']}件)

今週の記録: {stats['this_week']}件
今月の記録: {stats['this_month']}件

よく使うタグ: {tags_str}"""

    except Exception as e:
        print(f"Error showing stats: {e}")
        return "統計取得中にエラーが発生しました。"


async def show_advice(focus_area: str, user_id: str) -> str:
    """アドバイスを表示"""
    _, _, github, _, _, claude = get_clients()

    try:
        # 最近のエントリを取得
        recent_entries = await github.get_recent_entries(limit=20)

        if not recent_entries:
            return "まだ記録がないため、アドバイスを生成できません。日々の出来事や学びを記録してみましょう！"

        # アドバイス生成
        advice = claude.generate_advice(recent_entries, focus_area if focus_area else None)

        return advice

    except Exception as e:
        print(f"Error generating advice: {e}")
        return "アドバイスの生成中にエラーが発生しました。"


async def generate_slide(content: str, user_id: str) -> str:
    """議事録からスライドを生成"""
    slide_gen, fshare = get_slide_clients()

    if not content:
        return """スライド生成の使い方：

/slide [議事録内容]

例：
/slide
会議: 週次定例
日時: 2024/2/13
参加者: 田中、鈴木

議題:
1. 進捗報告
2. 来週の予定

決定事項:
- プロジェクトAは来週完了予定
- 新機能のリリースは3月

アクション:
- 田中: 資料作成（2/15まで）
- 鈴木: テスト実施"""

    try:
        # スライド生成
        pptx_data = slide_gen.generate_from_text(content)

        # 会議タイトルを取得
        meeting_data = slide_gen.parse_meeting_notes(content)
        title = meeting_data.get("title", "会議")

        # Cloud Storageにアップロード
        result = await fshare.upload_slides(pptx_data, title)

        if result.get("success"):
            return f"""スライドを作成しました！

タイトル: {title}
ダウンロード: {result['url']}

※リンクは72時間有効です"""
        else:
            return f"スライドのアップロードに失敗しました: {result.get('error', '不明なエラー')}"

    except Exception as e:
        print(f"Error generating slide: {e}")
        import traceback
        traceback.print_exc()
        return "スライド生成中にエラーが発生しました。"


async def handle_market_analysis(content: str, user_id: str) -> str:
    """マーケット分析機能"""
    _, _, github, _, _, claude = get_clients()

    # デバッグ用ログ
    print(f"[DEBUG] handle_market_analysis called with content: '{content}'")
    print(f"[DEBUG] content length: {len(content) if content else 0}")
    print(f"[DEBUG] content type: {type(content)}")

    if not content:
        return """📈 マーケット分析の使い方:

/market data - 最新マーケットデータ取得
/market summary - 蓄積記事の統合分析
/market save [記事] - 記事を保存
/market list - 保存済み記事一覧
/market [記事本文] - 新規記事を分析

蓄積中の記事:
1. L氏「本当のリスクはここから上」(2/26)
2. kokko氏「時計仕掛けの摩天楼」(2/15)
3. kokko氏「過剰解釈は禁物」(2/8)"""

    content_lower = content.lower().strip()
    print(f"[DEBUG] content_lower: '{content_lower}'")

    if content_lower == 'summary':
        # 統合分析
        print("[DEBUG] Calling generate_market_summary")
        return await generate_market_summary(user_id)
    elif content_lower == 'data':
        # 最新データ取得
        print("[DEBUG] Calling fetch_market_data")
        return await fetch_market_data(user_id)
    elif content_lower.startswith('save '):
        # 記事を保存
        print("[DEBUG] Calling save_market_article")
        article = content[5:].strip()
        return await save_market_article(article, user_id)
    elif content_lower == 'list':
        # 保存済み記事一覧
        print("[DEBUG] Calling list_market_articles")
        return await list_market_articles(user_id)
    else:
        # 新規記事分析
        print("[DEBUG] Calling analyze_market_article")
        return await analyze_market_article(content, user_id)


async def generate_market_summary(user_id: str) -> str:
    """蓄積記事の統合分析"""
    try:
        print("[DEBUG] generate_market_summary: Getting clients")
        _, _, _, _, _, claude = get_clients()
        print("[DEBUG] generate_market_summary: Calling claude.generate_market_summary()")
        summary = claude.generate_market_summary()
        print(f"[DEBUG] generate_market_summary: Success, summary length: {len(summary)}")
        return summary
    except Exception as e:
        print(f"[ERROR] Error generating market summary: {e}")
        import traceback
        traceback.print_exc()
        return f"マーケット分析の生成中にエラーが発生しました: {str(e)[:100]}"


async def fetch_market_data(user_id: str) -> str:
    """最新マーケットデータをリアルタイム取得"""
    import httpx
    from datetime import datetime
    import pytz

    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst).strftime('%m/%d %H:%M')

    # Yahoo Finance APIから取得するティッカー
    tickers = {
        'SPY': 'S&P 500',
        'QQQ': 'QQQ',
        'IGV': 'IGV',
        '^VIX': 'VIX',
        'GC=F': '金',
        'SI=F': '銀',
        'TLT': '米国債20年',
        '^TNX': '10年金利',
    }

    data = {}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for ticker, name in tickers.items():
                try:
                    # Yahoo Finance API (非公式だが広く使用されている)
                    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                    params = {"interval": "1d", "range": "5d"}
                    headers = {"User-Agent": "Mozilla/5.0"}

                    resp = await client.get(url, params=params, headers=headers)
                    if resp.status_code == 200:
                        result = resp.json()
                        meta = result.get('chart', {}).get('result', [{}])[0].get('meta', {})
                        price = meta.get('regularMarketPrice', 0)
                        prev_close = meta.get('previousClose', 0)

                        if price and prev_close:
                            change_pct = ((price - prev_close) / prev_close) * 100
                            data[name] = {
                                'price': price,
                                'change': change_pct
                            }
                except Exception as e:
                    print(f"Error fetching {ticker}: {e}")
                    continue

    except Exception as e:
        print(f"Error in market data fetch: {e}")
        return "マーケットデータの取得に失敗しました。しばらく後で再試行してください。"

    # 結果をフォーマット
    def fmt_price(name, decimals=2):
        if name in data:
            p = data[name]['price']
            c = data[name]['change']
            sign = '+' if c >= 0 else ''
            return f"{p:,.{decimals}f} ({sign}{c:.2f}%)"
        return "取得失敗"

    # 金銀比率を計算
    gold_silver_ratio = ""
    if '金' in data and '銀' in data:
        ratio = data['金']['price'] / data['銀']['price']
        gold_silver_ratio = f"\n金銀比率: {ratio:.1f}:1"

    response = f"""📊 マーケットデータ ({now} JST)

【指数】
S&P 500 (SPY): ${fmt_price('S&P 500')}
QQQ: ${fmt_price('QQQ')}
IGV: ${fmt_price('IGV')}

【ボラティリティ】
VIX: {fmt_price('VIX')}

【貴金属】
金先物: ${fmt_price('金')}
銀先物: ${fmt_price('銀')}{gold_silver_ratio}

【債券】
TLT: ${fmt_price('TLT')}
10年金利: {fmt_price('10年金利', 3)}%

💡 /market summary で統合分析
💡 /market [記事] で新規記事分析"""

    return response


async def analyze_market_article(article: str, user_id: str) -> str:
    """新規記事を分析"""
    try:
        _, _, _, _, _, claude = get_clients()
        analysis = claude.analyze_market_article(article)
        return analysis
    except Exception as e:
        print(f"Error analyzing market article: {e}")
        import traceback
        traceback.print_exc()
        return f"記事分析中にエラーが発生しました: {str(e)[:100]}"


async def handle_economic_indicator(indicator_data: Dict[str, Any], user_id: str, reply_token: str) -> str:
    """
    経済指標の記録と考察の深掘り

    Args:
        indicator_data: 抽出された経済指標データ
        user_id: ユーザーID
        reply_token: LINE reply token

    Returns:
        応答メッセージ
    """
    try:
        _, _, github, _, _, claude = get_clients()

        indicator = indicator_data.get('indicator', 'Unknown')
        interpretation = indicator_data.get('interpretation', '')

        # 1. データを保存
        await github.save_economic_indicator(indicator_data)
        print(f"[DEBUG] Saved economic indicator: {indicator}")

        # 2. 過去データを取得
        history = await github.get_indicator_history(indicator, limit=5)
        historical_context = None
        if history:
            historical_context = f"過去{len(history)}回のデータ:\n"
            for h in history:
                actual = h.get('actual', 'N/A')
                saved_at = h.get('saved_at', 'N/A')[:10]
                historical_context += f"- {saved_at}: {actual}\n"

        # 3. データ保存確認メッセージ
        actual = indicator_data.get('actual', 'N/A')
        consensus = indicator_data.get('consensus')
        unit = indicator_data.get('unit', '')

        save_msg = f"📊 {indicator_data.get('indicator_full_name', indicator)} を記録しました\n\n"
        save_msg += f"実績: {actual}{unit}\n"
        if consensus:
            save_msg += f"予想: {consensus}{unit}\n"
        if history:
            save_msg += f"\n過去データ: {len(history)}件記録済み"

        # 4. 解釈がある場合は考察を深める
        if interpretation and len(interpretation) > 5:
            print(f"[DEBUG] User interpretation found: {interpretation[:50]}...")
            discussion = claude.discuss_economic_indicator(
                indicator_data,
                interpretation,
                historical_context
            )
            response = f"{save_msg}\n\n---\n\n💭 考察の深掘り:\n{discussion}"
        else:
            # 解釈がない場合は保存確認のみ
            response = save_msg
            if historical_context:
                response += f"\n\n{historical_context}"

        return response

    except Exception as e:
        print(f"[ERROR] Error handling economic indicator: {e}")
        import traceback
        traceback.print_exc()
        return f"経済指標の処理中にエラーが発生しました: {str(e)[:100]}"


async def save_market_article(article: str, user_id: str) -> str:
    """マーケット記事をGitHubに保存"""
    _, _, github, _, fmt, claude = get_clients()

    if not article or len(article) < 50:
        return "記事の内容が短すぎます。\n使い方: /market save [記事本文]"

    try:
        from datetime import datetime
        import pytz

        jst = pytz.timezone('Asia/Tokyo')
        now = datetime.now(jst)

        # 記事を分析
        analysis = claude.analyze_market_article(article)

        # 記事の最初の行からタイトルを抽出
        first_line = article.split('\n')[0][:50].strip()
        title = first_line if first_line else "マーケット記事"

        # Markdownファイルを作成
        markdown = f"""---
type: market_article
date: {now.strftime('%Y-%m-%d')}
title: "{title}"
---

# {title}

## 記事本文

{article[:2000]}

## AI分析

{analysis}

---
*保存日時: {now.strftime('%Y-%m-%d %H:%M')} JST*
"""

        # ファイルパス生成
        file_path = f"market/articles/{now.strftime('%Y-%m-%d')}_{title[:20].replace(' ', '_')}.md"

        # GitHubに保存
        await github.create_or_update_file(file_path, markdown)

        return f"""✅ 記事を保存しました

タイトル: {title}
日付: {now.strftime('%Y-%m-%d')}

分析サマリー:
{analysis[:500]}..."""

    except Exception as e:
        print(f"Error saving market article: {e}")
        import traceback
        traceback.print_exc()
        return "記事の保存中にエラーが発生しました。"


async def list_market_articles(user_id: str) -> str:
    """保存済みマーケット記事一覧"""
    _, _, github, _, _, _ = get_clients()

    try:
        # GitHubから記事一覧を取得
        articles = await github.list_files("market/articles")

        if not articles:
            return """保存済みの記事はありません。

デフォルト蓄積記事:
1. L氏「本当のリスクはここから上」(2/26)
2. kokko氏「時計仕掛けの摩天楼」(2/15)
3. kokko氏「過剰解釈は禁物」(2/8)

新しい記事を保存: /market save [記事本文]"""

        response = "📚 保存済みマーケット記事:\n\n"
        for i, article in enumerate(articles[:10], 1):
            name = article.get('name', '').replace('.md', '')
            response += f"{i}. {name}\n"

        response += "\n/market summary で統合分析"
        return response

    except Exception as e:
        print(f"Error listing market articles: {e}")
        return """保存済み記事の取得に失敗しました。

デフォルト蓄積記事:
1. L氏「本当のリスクはここから上」(2/26)
2. kokko氏「時計仕掛けの摩天楼」(2/15)
3. kokko氏「過剰解釈は禁物」(2/8)"""


async def show_help() -> str:
    """ヘルプを表示"""
    return """Life Assistant ヘルプ

【基本的な使い方】
話しかけると会話ができます。
記録すべき内容を送ると、自動で分類して保存します。

【コマンド一覧】
/diary [内容] - 日記として保存
/learn [内容] - 学習メモとして保存
/idea [内容] - アイデアとして保存
/task [内容] - タスクとして追加
/done [タスク名] - タスクを完了
/review week - 週次レビュー表示
/review month - 月次レビュー表示
/search [キーワード] - 検索
/stats - 統計表示
/advice [分野] - アドバイス生成
/slide [議事録] - スライド作成
/market [記事/summary/data] - マーケット分析
/help - このヘルプを表示

【会話例】
「こんにちは」→ 会話モード
「今日Python学んだ」→ 自動保存
「先週何したっけ？」→ 会話モード"""


async def show_unknown_command() -> str:
    """不明なコマンド"""
    return "不明なコマンドです。/help でコマンド一覧を確認できます。"


async def handle_follow(event: dict):
    """フォロー（友だち追加）イベント"""
    _, line, github, _, _, _ = get_clients()

    user_id = event['source'].get('userId')
    reply_token = event.get('replyToken')

    welcome_message = """Life Assistantへようこそ!

このボットは、あなたの日々のインプット・アウトプットを整理し、知識として蓄積するお手伝いをします。

【使い方】
- メッセージを送信すると、AIが自動で分類して保存します
- コマンドで明示的に指定もできます：
  /diary - 日記として保存
  /learn - 学習メモとして保存
  /idea - アイデアとして保存
  /task - タスクとして追加
  /help - ヘルプを表示

さあ、何か記録してみましょう!"""

    await line.reply_text(reply_token, welcome_message)

    # ユーザー設定を保存
    try:
        await github.update_user_config({"line_user_id": user_id})
    except Exception as e:
        print(f"Error saving user config: {e}")


async def handle_unfollow(event: dict):
    """アンフォロー（ブロック）イベント"""
    user_id = event['source'].get('userId')
    print(f"User {user_id} unfollowed")
