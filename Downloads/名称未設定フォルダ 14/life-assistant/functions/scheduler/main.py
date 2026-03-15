"""
Scheduled Tasks Handler
定期実行タスク（週次レビュー、月次レビュー）を処理する
"""
import sys
import os

# 共有モジュールへのパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import functions_framework
from datetime import datetime, timezone, timedelta
import json
import asyncio

from shared.config import get_config
from shared.line_client import LineClient
from shared.github_client import GitHubClient
from shared.claude_client import ClaudeClient
from shared.formatter import MarkdownFormatter


JST = timezone(timedelta(hours=9))

# グローバルインスタンス
config = None
line_client = None
github_client = None
claude_client = None
formatter = None


def get_clients():
    """クライアントインスタンスを取得"""
    global config, line_client, github_client, claude_client, formatter

    if config is None:
        config = get_config()
        line_client = LineClient(config)
        github_client = GitHubClient(config)
        claude_client = ClaudeClient(config)
        formatter = MarkdownFormatter()

    return config, line_client, github_client, claude_client, formatter


@functions_framework.http
def scheduled_task(request):
    """
    スケジュールタスクのエントリポイント

    Cloud Schedulerからのトリガーを受信
    """
    try:
        request_json = request.get_json(silent=True) or {}
        task_type = request_json.get('task_type', 'weekly_review')

        if task_type == 'weekly_review':
            result = asyncio.run(generate_weekly_review())
        elif task_type == 'monthly_review':
            result = asyncio.run(generate_monthly_review())
        else:
            return {'error': f'Unknown task type: {task_type}'}, 400

        return {'success': True, 'result': result}, 200

    except Exception as e:
        print(f"Error in scheduled task: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}, 500


async def generate_weekly_review():
    """週次レビューを生成"""
    _, line, github, claude, fmt = get_clients()

    now = datetime.now(JST)

    # 先週の情報を計算
    # 週の開始を月曜日として計算
    days_since_monday = now.weekday()
    this_monday = now - timedelta(days=days_since_monday)
    last_monday = this_monday - timedelta(days=7)
    last_sunday = this_monday - timedelta(days=1)

    # 先週の週番号
    week_number = last_monday.isocalendar()[1]
    year = last_monday.year

    week_info = {
        "year": year,
        "week": week_number,
        "start_date": last_monday.strftime("%Y-%m-%d"),
        "end_date": last_sunday.strftime("%Y-%m-%d")
    }

    # 該当週のエントリを取得
    start_datetime = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_datetime = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)

    entries = await github.get_entries_for_period(start_datetime, end_datetime)

    if not entries:
        print(f"No entries for week {week_number}")
        return {
            "message": "No entries for this week",
            "week": week_info
        }

    # Claudeでレビュー生成
    review_content = claude.generate_weekly_review(entries, week_info)

    # Markdown整形
    markdown = fmt.format_weekly_review(
        content=review_content,
        week=week_number,
        year=year,
        start_date=week_info["start_date"],
        end_date=week_info["end_date"]
    )

    # GitHubに保存
    file_path = f"reviews/weekly/{year}/{year}-W{week_number:02d}.md"
    await github.create_or_update_file(
        file_path,
        markdown,
        f"Add weekly review for {year}-W{week_number:02d}"
    )

    # LINEに通知
    await notify_user(
        f"週次レビューを生成しました!\n\n"
        f"第{week_number}週 ({week_info['start_date']} ~ {week_info['end_date']}) の振り返りをご確認ください。\n\n"
        f"/review week で確認できます。"
    )

    return {
        "message": "Weekly review generated",
        "week": week_info,
        "entries_count": len(entries),
        "file_path": file_path
    }


async def generate_monthly_review():
    """月次レビューを生成"""
    _, line, github, claude, fmt = get_clients()

    now = datetime.now(JST)

    # 先月の情報
    if now.month == 1:
        target_month = 12
        target_year = now.year - 1
    else:
        target_month = now.month - 1
        target_year = now.year

    month_info = {
        "year": target_year,
        "month": target_month
    }

    # 先月の開始日と終了日
    start_date = datetime(target_year, target_month, 1, 0, 0, 0, tzinfo=JST)

    if target_month == 12:
        end_date = datetime(target_year + 1, 1, 1, tzinfo=JST) - timedelta(seconds=1)
    else:
        end_date = datetime(target_year, target_month + 1, 1, tzinfo=JST) - timedelta(seconds=1)

    # 該当月のエントリを取得
    entries = await github.get_entries_for_period(start_date, end_date)

    if not entries:
        print(f"No entries for {target_year}-{target_month:02d}")
        return {
            "message": "No entries for this month",
            "month": month_info
        }

    # 週次レビューを取得（その月の分）
    weekly_reviews = []
    # 先月に含まれる週のレビューを取得
    for week_offset in range(5):  # 最大5週間分
        week_date = start_date + timedelta(weeks=week_offset)
        if week_date > end_date:
            break

        week_num = week_date.isocalendar()[1]
        week_year = week_date.isocalendar()[0]

        review_path = f"reviews/weekly/{week_year}/{week_year}-W{week_num:02d}.md"
        review_content = await github.get_file_content(review_path)

        if review_content:
            weekly_reviews.append({
                "week": f"{week_year}-W{week_num:02d}",
                "summary": review_content[:500]  # 最初の500文字
            })

    # Claudeでレビュー生成
    review_content = claude.generate_monthly_review(
        entries,
        weekly_reviews,
        month_info
    )

    # Markdown整形
    markdown = fmt.format_monthly_review(
        content=review_content,
        month=target_month,
        year=target_year
    )

    # GitHubに保存
    file_path = f"reviews/monthly/{target_year}/{target_year}-{target_month:02d}.md"
    await github.create_or_update_file(
        file_path,
        markdown,
        f"Add monthly review for {target_year}-{target_month:02d}"
    )

    # LINEに通知
    await notify_user(
        f"月次レビューを生成しました!\n\n"
        f"{target_year}年{target_month}月の振り返りをご確認ください。\n\n"
        f"/review month で確認できます。"
    )

    return {
        "message": "Monthly review generated",
        "month": month_info,
        "entries_count": len(entries),
        "file_path": file_path
    }


async def notify_user(message: str):
    """ユーザーにLINE通知を送信"""
    _, line, github, _, _ = get_clients()

    try:
        user_config = await github.get_user_config()
        user_id = user_config.get("line_user_id")

        if user_id:
            await line.push_message(user_id, message)
            print(f"Notification sent to user {user_id}")
        else:
            print("No user_id configured, skipping notification")

    except Exception as e:
        print(f"Error sending notification: {e}")


# 手動テスト用エンドポイント
@functions_framework.http
def test_weekly_review(request):
    """週次レビューのテスト用エンドポイント"""
    try:
        result = asyncio.run(generate_weekly_review())
        return {'success': True, 'result': result}, 200
    except Exception as e:
        return {'error': str(e)}, 500


@functions_framework.http
def test_monthly_review(request):
    """月次レビューのテスト用エンドポイント"""
    try:
        result = asyncio.run(generate_monthly_review())
        return {'success': True, 'result': result}, 200
    except Exception as e:
        return {'error': str(e)}, 500
