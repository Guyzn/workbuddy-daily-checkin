#!/usr/bin/env python3
"""WorkBuddy Buddy加油站 每日自动领取积分。

读取 Desktop 端持久化的会话凭证（明文 JSON，由 App 自动刷新），
先查 checkin-activity-status，今日未领才调 daily-checkin。
token 过期时退出码 3，提醒手动登录 WorkBuddy 刷新。

用法: python3 wb_daily_checkin.py
退出码: 0=成功或今日已领, 1=接口失败, 2=凭证文件缺失, 3=token 过期
"""
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

AUTH_FILE = Path.home() / "Library/Application Support/CodeBuddyExtension/Data/Public/auth/workbuddy-desktop.info"
BASE = "https://www.workbuddy.cn"
LOG = Path.home() / ".workbuddy/logs/wb_daily_checkin.log"


def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)


def post(path: str, token: str, uid: str) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=b"{}",
        method="POST",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-User-Id": uid,
        },
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main() -> int:
    if not AUTH_FILE.exists():
        log(f"FAIL: auth file missing: {AUTH_FILE}")
        return 2

    info = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
    auth = info.get("auth", {})
    account = info.get("account", {})
    token = auth.get("accessToken", "")
    uid = account.get("uid", "")

    # token 有效期检查（expiresAt 毫秒时间戳，留 1 天余量）
    expires_at = auth.get("expiresAt", 0) / 1000
    if time.time() > expires_at - 86400:
        log("FAIL: access token expired or expiring soon — 需要打开 WorkBuddy 重新登录刷新凭证")
        return 3

    try:
        status = post("/v2/billing/meter/checkin-activity-status", token, uid)
    except urllib.error.HTTPError as e:
        log(f"FAIL: status HTTP {e.code} {e.read()[:200]}")
        return 1
    except Exception as e:
        log(f"FAIL: status error {e}")
        return 1

    data = status.get("data") or {}
    if status.get("code") != 0:
        log(f"FAIL: status code={status.get('code')} msg={status.get('msg')}")
        return 1

    if not data.get("active"):
        log(f"SKIP: 活动未进行 (activity={data.get('activity_name')}, end={data.get('end_time')})")
        return 0

    if data.get("today_checked_in"):
        log(f"SKIP: 今日已领 streak={data.get('streak_days')} total={data.get('total_credits')}")
        return 0

    try:
        result = post("/v2/billing/meter/daily-checkin", token, uid)
    except urllib.error.HTTPError as e:
        log(f"FAIL: checkin HTTP {e.code} {e.read()[:200]}")
        return 1
    except Exception as e:
        log(f"FAIL: checkin error {e}")
        return 1

    if result.get("code") == 0:
        d = result.get("data") or {}
        log(f"OK: +{d.get('credit', '?')} 积分 streak={d.get('streak_days', '?')}")
        return 0

    log(f"FAIL: checkin code={result.get('code')} msg={result.get('msg')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
