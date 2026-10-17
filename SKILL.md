---
name: workbuddy-checkin
description: WorkBuddy Desktop 的「Buddy加油站」每日签到领积分。要签到、要领积分、要查今天领没领、或者签到不明原因失效时用。触发词 签到、领积分、Buddy加油站、每日签到、checkin、打卡、积分。
agent_created: true
---

# WorkBuddy 每日签到

每天一百积分。接口能直接领，就不该再截图找按钮。

## 现在的主路径

脚本 vendor 在 `~/Library/Application Support/wb-signin/repo/`。上游是 88lin/workbuddy-auto-signin，commit 和 `signin.py` 的 sha256 抄在同目录的 `VERSION.txt` 里。不自动更新，要升级先看 diff 再决定。

launchd 任务 `com.workbuddy.signin` 负责触发，登录时一次，每天上午九点一次，跑的都是 `signin.py auto`。日志在 `~/Library/Logs/wb-signin.log`，报错在 `~/Library/Logs/wb-signin.err`。

为什么不是零点零五。这台机器那个点几乎都在睡觉或者锁着屏，一切依赖屏幕或者依赖准点的方案到这儿都会失效。挪到登录时和九点，夜里错过的由 launchd 在唤醒后补跑，一天两次足够覆盖。

巡检只有一个动作

```bash
tail -1 ~/Library/Logs/wb-signin.log
```

`needs_attention` 是 false 就算过。连着两天 true 再叫人，那种情形多半是客户端升级把解密链路弄断了，重试没用。

## 解释器别乱换

必须用 `/usr/bin/python3`，本机是 3.9.6。同一份脚本换 3.14.7 跑，卡三分钟一个字节都不吐，最后也没结果。这不是网络慢，是它自己的毛病。plist 里已经写死 3.9.6，不要顺手升级。

## 两条旧结论是错的

这个 skill 早先写着「HTTP 路线已死」，理由是接口强制 Turing 设备指纹头，外加 accessToken 加密解不开。两条都被实测推翻了，别再引用。

指纹头那条，字段根本不用带。`/v2/billing/meter/checkin-activity-status` 不带它照样返回 200。

解密那条，离线确实解不出，密钥在客户端 native 层。但没必要离线解。借客户端自己的 Electron 运行时，`process._linkedBinding('electron_browser_workbuddy_storage').loggerGet()` 能把 at-rest 密钥取出来，在同一进程里做 AES-256-GCM 解密。密钥不出进程，明文 token 不落盘。这是正路。

## 兜底两条，都需要人在场

接口哪天真的挂了，才轮到这两条。

第一条是 OCR 加鼠标，脚本 `legacy/ocr-ui/wb_checkin_cua.py`。它绕开接口，是接口失效期唯一还能领的路。代价是苛刻到几乎没法无人值守，屏幕得亮着，窗口不能被挡，辅助功能权限要开，tesseract 得装，OCR 还得认得出「立即领取」四个字。2026 年 10 月 14 到 18 号，它连着五天没成。要跑就人在跟前跑。

第二条是手动，五步点击法见 `references/manual-click-guide.md`。点完必须复核，不许跳过。

## 不管的事

WorkBuddy 登录失效或者账号本身有问题，引导去重新登录，这里不做。积分规则、活动期数、奖励额度，以 App 里显示的为准，文档抄一遍只会过期。还有，别试图还原那份早就失效的纯 HTTP 老脚本，它死在凭证加密上，跟指纹头一点关系没有。

## 结果怎么看

输出是一行 JSON。`result` 常见四种，`OK` 是刚领到，`ALREADY` 是今天早领过，`INACTIVE` 是非活动期，`AUTH_ERROR` 才是真出事。`report` 字段是给人看的一句话，`needs_attention` 是给机器看的开关。

`auto` 除了签到，还会跑一遍成长中心，派 Buddy 出门、领旅行礼物、领任务奖、断登补登、连登兑换、开盲盒。这部分是写操作，脚本不做重试，宁可留到下一轮也不重复提交。

## 装和卸

装用仓库里的 `scripts/install-macos.sh`，它会 vendor 上游、校验哈希、写 plist、加载任务，最后跑一次给你看结果。

卸用同一条脚本加 `uninstall`，卸载任务和 plist，数据目录留着。确认不要了再加 `--purge`。

## 风险，写在明处

这是逆向私有接口加借用客户端解密钥，本质是绕开产品设计。腾讯改版就失效，理论上也有账号被风控的可能。失效不会断签，因为一天有两次机会，风控就只能认。要不要继续用，是使用者的取舍，不是技术文档能替他决定的。

## 变更记录

2026-10-18 v2.0 主路径换成 HTTP 直连，vendor 上游并 pin 住 commit。实测推翻指纹头和解密两条旧结论，实测 3.14 会卡死所以固定 3.9.6。launchd 从零点零五改成登录时加九点，下线两个长期空跑的 OCR 定时任务。OCR 脚本降级为人工在场的兜底。

2026-09-24 v1.2 修头像点击偶尔落空、菜单展开时机不稳。头像点击并入重试循环，每次多等一拍。

2026-09-24 v1.1 加启动自检，tesseract 或者辅助功能权限缺失时说人话。截图按批次只留三次。验证改成双判据。

2026-09-24 v1.0 首发，OCR 自动脚本加手动五步法。
