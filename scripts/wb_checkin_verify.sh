#!/bin/bash
# WorkBuddy 签到结果检查脚本
# 每天 00:15 运行，检查签到状态并通知用户

CACHE_DIR="$HOME/WorkBuddy/Claw/.workbuddy/cache"
DATE=$(date +%Y-%m-%d)
CACHE_FILE="$CACHE_DIR/checkin_$DATE"

mkdir -p "$CACHE_DIR"

# 清理 7 天前的旧缓存文件
find "$CACHE_DIR" -name "checkin_*.ok" -o -name "checkin_*.fail" -o -name "checkin_*.already" | xargs -I {} find {} -mtime +7 -delete 2>/dev/null

if [ ! -f "$CACHE_FILE" ]; then
  # 缓存文件不存在，说明 00:00 的签到任务可能没跑
  osascript -e 'display notification "⚠️ 未找到今日签到记录，请检查 WorkBuddy 是否运行" with title "Buddy加油站" sound name "Basso"'
  exit 1
fi

STATUS=$(cat "$CACHE_FILE")

if [ "$STATUS" = "ok" ]; then
  osascript -e 'display notification "✅ WorkBuddy 今日积分已领取成功" with title "Buddy加油站" sound name "Glass"'
elif [ "$STATUS" = "already" ]; then
  osascript -e 'display notification "✅ WorkBuddy 今日积分已领过" with title "Buddy加油站" sound name "Glass"'
else
  # 签到失败，尝试重试一次
  LOG_FILE="$HOME/.workbuddy/logs/wb_checkin_cua.log"
  SCRIPT_PATH="$HOME/.workbuddy/skills/workbuddy-checkin/scripts/wb_checkin_cua.py"
  PYTHON_PATH="$HOME/.workbuddy/skills/cua-mcp/.venv/bin/python3"

  $PYTHON_PATH "$SCRIPT_PATH" > /dev/null 2>&1

  LAST_ENTRY=$(tail -1 "$LOG_FILE")
  if echo "$LAST_ENTRY" | grep -q "OK"; then
    echo "ok" > "$CACHE_FILE"
    osascript -e 'display notification "✅ 重试成功，WorkBuddy 积分已领取" with title "Buddy加油站" sound name "Glass"'
  else
    osascript -e 'display notification "❌ WorkBuddy 签到失败，请手动检查" with title "Buddy加油站" sound name "Basso"'
  fi
fi
