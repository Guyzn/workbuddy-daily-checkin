#!/bin/bash
# WorkBuddy 每日签到 wrapper：跑签到脚本 → 解析结果 → 写缓存文件 → 弹系统通知

SCRIPT_DIR="$HOME/.workbuddy/skills/workbuddy-checkin/scripts"
LOG="$HOME/.workbuddy/logs/wb_checkin_cua.log"
CACHE_DIR="$HOME/WorkBuddy/Claw/.workbuddy/cache"
DATE=$(date +%Y-%m-%d)
CACHE_FILE="$CACHE_DIR/checkin_$DATE"

mkdir -p "$CACHE_DIR"

"$SCRIPT_DIR/../../.venv/bin/python3" "$SCRIPT_DIR/wb_checkin_cua.py" >> "$LOG" 2>&1

LAST=$(tail -1 "$LOG")

if echo "$LAST" | grep -q "OK: already"; then
  echo "already" > "$CACHE_FILE"
  osascript -e 'display notification "今日积分已领过 ✅" with title "WorkBuddy 签到" sound name "Glass"'
elif echo "$LAST" | grep -q "OK:"; then
  echo "ok" > "$CACHE_FILE"
  osascript -e 'display notification "签到成功 🎉" with title "WorkBuddy 签到" sound name "Glass"'
else
  echo "fail" > "$CACHE_FILE"
  osascript -e 'display notification "签到失败，请手动检查 ⚠️" with title "WorkBuddy 签到" sound name "Basso"'
fi
