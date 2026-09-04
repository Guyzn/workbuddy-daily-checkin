# workbuddy-daily-checkin

WorkBuddy Buddy加油站 每日自动领取积分脚本。

读取 Desktop 端持久化的会话凭证，先查状态、未领才领，token 临期自动提醒。

## 使用

```bash
python3 wb_daily_checkin.py
```

退出码：`0`=成功/已领，`1`=接口失败，`2`=凭证文件缺失，`3`=token 过期。

## 配合 cron / 定时任务

```cron
0 1 * * * /usr/bin/python3 /path/to/wb_daily_checkin.py >> ~/.workbuddy/logs/wb_daily_checkin.log 2>&1
```

## 凭证文件

`~/Library/Application Support/CodeBuddyExtension/Data/Public/auth/workbuddy-desktop.info`

明文 JSON，含 `auth.accessToken`（60 天有效）和 `auth.refreshToken`，WorkBuddy Desktop 每次启动自动刷新。脚本本身不存储任何凭证。

## 接口

- `POST /v2/billing/meter/checkin-activity-status` — 查活动状态/今日是否已领
- `POST /v2/billing/meter/daily-checkin` — 领取当日积分

域名：`https://www.workbuddy.cn`，Header：`Authorization: Bearer <token>` + `X-User-Id: <uid>`。
