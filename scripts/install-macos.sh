#!/bin/bash
# 装 WorkBuddy 每日签到的 macOS 定时任务。
# 用法
#   install-macos.sh            装好并跑一次
#   install-macos.sh status     看任务状态和最后一轮结果
#   install-macos.sh uninstall  卸载任务和 plist，数据留着
#   install-macos.sh uninstall --purge  连数据一起删

set -euo pipefail

# 上游固定在这个 commit，哈希是 signin.py 的。
# 上游有新提交不代表要跟，改之前先看 diff，改完把两个值一起换掉。
UPSTREAM_URL="https://github.com/88lin/workbuddy-auto-signin.git"
PIN_COMMIT="c5fe510adeae4ee2a7a6d498620dc9868647331c"
PIN_SHA256="a5aa672b340a0c7a7d4ffd589471528e28198480d7d9838e30e0ea7da591ec44"

# 必须 3.9 系。本机实测 3.14 跑这份脚本会卡住不返回。
PYTHON="/usr/bin/python3"

APP_DIR="$HOME/Library/Application Support/wb-signin"
REPO_DIR="$APP_DIR/repo"
PLIST="$HOME/Library/LaunchAgents/com.workbuddy.signin.plist"
LABEL="com.workbuddy.signin"
LOG_OUT="$HOME/Library/Logs/wb-signin.log"
LOG_ERR="$HOME/Library/Logs/wb-signin.err"

die() { printf '出错 %s\n' "$1" >&2; exit 1; }

need_macos() {
  [ "$(uname -s)" = "Darwin" ] || die "这份安装脚本只处理 macOS。Windows 直接跑 signin.py，用任务计划程序定时。"
}

cmd_install() {
  need_macos
  [ -x "$PYTHON" ] || die "找不到 $PYTHON。macOS 自带的那份就够，装了 Xcode 命令行工具才会有。"

  mkdir -p "$APP_DIR" "$(dirname "$PLIST")" "$(dirname "$LOG_OUT")"

  if [ ! -f "$REPO_DIR/signin.py" ]; then
    printf '拉上游到 %s\n' "$REPO_DIR"
    rm -rf "$REPO_DIR"
    mkdir -p "$REPO_DIR"
    git -C "$REPO_DIR" init -q
    git -C "$REPO_DIR" remote add origin "$UPSTREAM_URL"
    git -C "$REPO_DIR" fetch -q --depth 1 origin "$PIN_COMMIT"
    git -C "$REPO_DIR" checkout -q FETCH_HEAD
  fi

  local actual
  actual=$(shasum -a 256 "$REPO_DIR/signin.py" | awk '{print $1}')
  [ "$actual" = "$PIN_SHA256" ] || die "signin.py 哈希对不上，实际 $actual。上游可能变了，先看 diff 再改 PIN_SHA256。"

  printf '版本对上了 %s\n' "${PIN_COMMIT:0:7}"

  cat > "$PLIST" <<PLIST_END
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$REPO_DIR/signin.py</string>
        <string>auto</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>$LOG_OUT</string>
    <key>StandardErrorPath</key>
    <string>$LOG_ERR</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
PLIST_END

  plutil -lint "$PLIST" >/dev/null || die "plist 写坏了，检查 $PLIST"

  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST" || die "任务没加载上，手动看 launchctl bootstrap 的报错"

  printf '任务已加载。等它跑完这一轮\n'
  sleep 12
  cmd_status
}

cmd_status() {
  printf '\n任务状态\n'
  launchctl list | grep -F "$LABEL" || printf '没找到 %s，任务没加载\n' "$LABEL"
  if [ -f "$LOG_OUT" ]; then
    printf '\n最近一轮\n'
    tail -1 "$LOG_OUT"
    "$PYTHON" - "$LOG_OUT" <<'PY_END' || true
import json, sys
try:
    line = open(sys.argv[1]).read().strip().splitlines()[-1]
    d = json.loads(line)
    print("\n结果 %s ｜ 连续 %s 天 ｜ 累计 %s ｜ 需要处理 %s" % (
        d.get("result"), d.get("streak_days"), d.get("total_credits"), d.get("needs_attention")))
except Exception:
    pass
PY_END
  else
    printf '还没有日志 %s\n' "$LOG_OUT"
  fi
  if [ -s "$LOG_ERR" ]; then
    printf '\n错误输出有内容\n'
    tail -5 "$LOG_ERR"
  fi
}

cmd_uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  printf '任务和 plist 已清掉\n'
  if [ "${1:-}" = "--purge" ]; then
    rm -rf "$APP_DIR"
    printf '数据目录也删了 %s\n' "$APP_DIR"
  else
    printf '数据留着 %s，要删加 --purge\n' "$APP_DIR"
  fi
}

case "${1:-install}" in
  install)   cmd_install ;;
  status)    cmd_status ;;
  uninstall) cmd_uninstall "${2:-}" ;;
  *)         die "只认 install / status / uninstall" ;;
esac
