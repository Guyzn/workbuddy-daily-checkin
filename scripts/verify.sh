#!/bin/bash
# 只读查一次签到状态。不领取，不改任何东西，跑完打一行 JSON。
# 依赖已经装好的 vendor 目录，没装就先跑 install-macos.sh。

set -euo pipefail

PYTHON="/usr/bin/python3"
REPO_DIR="$HOME/Library/Application Support/wb-signin/repo"

[ -f "$REPO_DIR/signin.py" ] || {
  printf '还没装。先跑 scripts/install-macos.sh\n' >&2
  exit 1
}

exec "$PYTHON" "$REPO_DIR/signin.py" status
