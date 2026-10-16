# workbuddy-daily-checkin

WorkBuddy Desktop「Buddy加油站」每日签到领积分自动化。

> **现行方案（v2）= OCR 驱动的 UI 自动化。** 2026-09-23 起，初版 HTTP 直领脚本因 accessToken 静态加密 + Turing 设备指纹头而永久失效（网关 401，根因见 [references/background-why-http-broken.md](references/background-why-http-broken.md)）。v2 改为驱动官方 UI 链路，让 App 自己带齐加密凭证。

## 目录结构

| 路径 | 说明 |
|------|------|
| `SKILL.md` | WorkBuddy Skill 定义（触发词 / 决策树 / 退出码 / 已知坑） |
| `scripts/wb_checkin_cua.py` | 全自动签到脚本（首选路径，OCR 定位 + 双判据验证 + 幂等） |
| `scripts/wb_checkin_scheduled.sh` | 定时 wrapper：跑签到 → 写缓存 → 系统通知 |
| `scripts/wb_checkin_verify.sh` | 签到复核：缓存缺失/失败时自动重试一次并通知 |
| `references/manual-click-guide.md` | 手动兜底五步点击法（脚本失效或环境不支持时用） |
| `references/background-why-http-broken.md` | 401 根因：为什么 HTTP 老路走不通 |
| `legacy/wb_daily_checkin.py` | 初版 HTTP 直领脚本（已失效，留档备查） |

## 前置条件

- macOS，WorkBuddy Desktop 已登录且窗口可见（未被完全遮挡）
- **tesseract** + 中文语言包：`brew install tesseract tesseract-lang`
- **辅助功能权限**：系统设置 → 隐私与安全性 → 辅助功能 → 勾选运行脚本的终端（缺失时点击会静默落空）
- Python 依赖：WorkBuddy 的 `cua-mcp` skill venv（Quartz / Pillow 等）

## 使用

### 安装为 WorkBuddy skill（推荐）

```bash
git clone https://github.com/Guyzn/workbuddy-daily-checkin.git \
  ~/.workbuddy/skills/workbuddy-checkin
```

脚本与 wrapper 默认按 `~/.workbuddy/skills/workbuddy-checkin/` 路径引用；放在其他位置需相应修改 `wb_checkin_scheduled.sh` / `wb_checkin_verify.sh` 顶部路径。

### 直接执行

```bash
~/.workbuddy/skills/cua-mcp/.venv/bin/python3 scripts/wb_checkin_cua.py
```

退出码：`0` = 签到成功 / 今日已签（幂等）· `1` = 失败（看日志与截图定位卡点）

### 定时执行

launchd / cron / WorkBuddy automation 任选，固定调 `scripts/wb_checkin_scheduled.sh`；再加一个 `wb_checkin_verify.sh`（如每天 00:15）做复核与失败重试。

### 日志与排查

- 日志：`~/.workbuddy/logs/wb_checkin_cua.log`（每次追加）
- 截图：`~/.workbuddy/logs/wb_checkin_shots/`（按运行批次自动只保留最近 3 次）

## 已知坑（必读）

- 卡片上「已领N天 | 累计领取N分」是**累计统计行**，领取前就显示——复核必须看三判据：按钮消失 + 天数 +1 + 累计分 +100，只看「已领N天」存在不算数。
- 签到面板小字 OCR 用 **2x** 放大（4x 会把字打散反而失败）。
- 窗口坐标每次运行时动态获取；多屏场景 X 可能大于主屏宽度，属正常。

更多调参细节见 `SKILL.md`。

## 版本历史

- **v2.0.0**（2026-09）：UI 自动化方案（现行）——自动脚本 + 手动兜底 + 定时复核通知。
- **v1.0**（2026-09-04）：HTTP 直领脚本（2026-09-23 起失效，留档 `legacy/`，若日后 token 回归明文可直接复用）。

## License

MIT
