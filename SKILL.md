---
name: workbuddy-checkin
description: WorkBuddy Desktop「Buddy加油站」每日签到领积分自动化。当需要执行每日签到、领取积分、修复签到失败、或处理「签到 401 / 已断签」类问题时使用。触发词：签到、领积分、Buddy加油站、每日签到、checkin、打卡、积分、401。
agent_created: true
---

# WorkBuddy 每日签到（Buddy加油站领积分）

## Overview

WorkBuddy Desktop 的「Buddy加油站」每天可领 100 通用积分。2026-09-23 App 升级后，原 HTTP 直领脚本因**凭证静态加密 + Turing 设备指纹头**双重锁定而失效（网关 401）。本 skill 提供两条互补路径：

- **自动（首选）**：OCR 驱动的 UI 自动化脚本 `scripts/wb_checkin_cua.py`，一条命令全程无人值守。
- **手动（兜底）**：Shadow 总结的五步点击法，见 `references/manual-click-guide.md`，用于脚本失效或环境不支持时。

## 前置依赖

- **cua-mcp skill**（截图/鼠标/窗口控制），脚本会自动在同级目录或 `~/.workbuddy/skills/cua-mcp` 查找。
- **tesseract** + `chi_sim` 语言包（OCR 中文按钮）：`brew install tesseract tesseract-lang`。
- **辅助功能权限**（点击的必要条件）：系统设置 → 隐私与安全性 → 辅助功能 → 打开执行终端/IDE。缺失时点击静默落空，脚本启动自检会拦截并提示。
- WorkBuddy Desktop 已登录且窗口可见（未被其他窗口完全遮挡）。

## 不处理（负面触发）

以下场景**不属于**本 skill，别强行套用：
- WorkBuddy 登录失效/账号问题 → 引导用户重新登录。
- 积分规则、活动期数、奖励额度咨询 → 以 App 内展示为准。
- 离线解密 accessToken / 还原旧 HTTP 脚本 → 已验证不可行，见背景文档。

## Workflow Decision Tree

```
要签到
  ├─ 跑脚本（首选）→ scripts/wb_checkin_cua.py
  │   ├─ exit=0 → 成功或今日已签（幂等）
  │   ├─ exit=1 → 看 ~/.workbuddy/logs/wb_checkin_cua.log + wb_checkin_shots/ 截图排查
  │   └─ 排查后仍失败 → 走手动兜底
  └─ 手动兜底 → references/manual-click-guide.md 五步法
```

## 自动模式（首选）

### 直接执行

```bash
~/.workbuddy/skills/cua-mcp/.venv/bin/python3 \
  ~/.workbuddy/skills/workbuddy-checkin/scripts/wb_checkin_cua.py
```

### 脚本行为

1. 激活 WorkBuddy，动态取窗口 bounds（多屏/挪窗自适应）。
2. 点左下角头像 → OCR 找「Buddy加油站」菜单项并点击。
3. 等签到面板出现（重试 4 次 × 2.5s），OCR 找「立即领取」并点击。
4. 验证「已领N天」出现且「立即领取」消失 → exit 0。
5. 若一开始就是「已领N天」→ 幂等跳过 → exit 0。

### 退出码

| 码 | 含义 |
|---|---|
| 0 | 签到成功，或今日已签（幂等） |
| 1 | 失败（看日志和截图定位卡点） |

### 日志与排查

- 日志：`~/.workbuddy/logs/wb_checkin_cua.log`（每次追加）
- 截图：`~/.workbuddy/logs/wb_checkin_shots/`，文件名带运行批次前缀（`YYYYMMDD-HHMMSS-pre/menu/panel0-3/verify`），自动只保留最近 3 次，用于定位卡在哪一步。

### 已知坑（调参时参考）

- ⚠️ **「OK: already」假阳性（2026-09-26 实测）**：卡片上「已领N天 | 累计领取N分」是**累计统计行**，领取前就显示在卡上。脚本的 already 分支（找不到「立即领取」→ 查「已领N天」）会把它误判成"今日已签"直接跳过——实际按钮还没点。复核必须看**三判据**：按钮消失（变「今日已领」灰钮）+ 天数 +1 + 累积分 +100；只看「已领N天」存在不算数。修复方向：already 分支前先确认「立即领取」按钮确实不在屏上（OCR 漏读按钮时可用几何定位兜底：卡片锚点行「Buddy加油站·9期」中心 +33px、x=66 侧栏内）。
- `ocr_words` 的 upscale 必须是 int（PIL resize 不接受 float）。
- 签到面板小字用 **2x** 放大 OCR，4x 会把字打散反而识别失败。
- 行首图标会被 OCR 误识别成杂词（如「抱」），`find_phrase` 用滑动起点跳过。
- 点菜单前先点主区域空白，关掉可能残留的签到气泡。
- 窗口坐标每次运行时动态获取，不硬编码；多屏场景 X 可能 > 主屏宽度，属正常。

## 手动兜底

脚本失效或环境不支持时，按 `references/manual-click-guide.md` 的五步法手动点：取窗口坐标 → 整窗截图找卡片 → 区域放大算按钮中心 → 点击 → 截图复核（文案+天数+累计分三判据）。**点完必须复核，不许跳过。**

## 定时自动化

用 automation 工具建每日任务，直接调脚本即可。示例（每天 01:00）：

```
prompt: 运行 ~/.workbuddy/skills/cua-mcp/.venv/bin/python3 ~/.workbuddy/skills/workbuddy-checkin/scripts/wb_checkin_cua.py，退出码 0 报成功，1 时读日志和最新截图说明卡点。
rrule: FREQ=DAILY;BYHOUR=1;BYMINUTE=0
```

## 背景：为什么旧 HTTP 脚本失效

详见 `references/background-why-http-broken.md`。核心：accessToken 被 AES-256-GCM 静态加密（密钥在定制 Electron native 层，离线解不出），且签到接口新增强制 Turing 设备指纹头（腾讯天御 SDK 生成），裸脚本拿不到。两条路都堵死，只能走 UI 自动化。

## Resources

### scripts/
- `wb_checkin_cua.py` — OCR 驱动的全自动签到脚本（首选路径）。

### references/
- `manual-click-guide.md` — Shadow 总结的手动五步点击法（兜底路径）。
- `background-why-http-broken.md` — 401 根因与加密方案逆向细节（仅供理解，不要试图重做离线解密）。

## 变更记录

- **2026-09-24 v1.2**：Darwin Round 2 runtime 验收。修复 R5：头像点击偶尔落空、菜单展开时机不稳 → 头像点击并入重试循环（3次，逐次延长等待），App 激活后等待 1.2s→2.0s。
- **2026-09-24 v1.1**：Darwin 优化 Round 1。新增启动自检（tesseract/辅助功能权限缺失时人话提示并引导手动兜底）；截图按批次保留最近 3 次防垃圾累积；验证改为双判据（「立即领取」消失 + 天数 +1 交叉比对）；删死代码；SKILL.md 补辅助功能权限前置与负面触发边界。
- **2026-09-24 v1.0**：合并版首发。自动 OCR 脚本（Guy 侧）+ 手动五步法（Shadow 侧）+ 401 根因背景。
