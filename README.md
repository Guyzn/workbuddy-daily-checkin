# workbuddy-daily-checkin

WorkBuddy Desktop「Buddy加油站」每天的一百积分，让它自己到账。

现在是 v3。主路径走接口，不再点界面。

## 一行装好

```bash
curl -fsSL https://raw.githubusercontent.com/Guyzn/workbuddy-daily-checkin/main/scripts/install-macos.sh | bash
```

装了哪些东西，装完会告诉你。任务在登录时和每天上午九点各跑一次，跑完把结果追加到 `~/Library/Logs/wb-signin.log`。

不想 curl 管道进 bash 的话，clone 下来跑 `scripts/install-macos.sh`，效果一样。

查状态

```bash
scripts/install-macos.sh status
```

卸掉

```bash
scripts/install-macos.sh uninstall
```

## 为什么不用界面了

上一版是 OCR 加鼠标，截图、找「立即领取」、点它。理论上通，实际上一周里能成两天。屏幕得亮着，窗口不能被挡，辅助功能权限得开着，tesseract 得装，OCR 还得把那四个字认对。2026 年 10 月 14 到 18 号，它连着五天没成，日志里全是「面板里没找到立即领取」。

更丢人的是定时这一层。两个 launchd 任务一直在跑，wrapper 脚本里的 python 路径写错了，从来没真的执行过，日志空白。也就是说连着五天，我们以为在自动签到，其实什么都没发生。

现在换接口。脚本读本机的登录凭据，直接问服务端今天领没领，没领就领。一次跑完不到两秒，不需要屏幕，不需要权限，睡着了也不影响，因为 launchd 会在唤醒后补跑错过的。

## 顺便说清楚两件旧事

仓库里那份 `references/background-why-http-broken.md` 说 HTTP 走不通，理由有两条。两条现在都不成立，我留着它当史料。

第一条说接口强制 Turing 设备指纹头。实测不用带，`/v2/billing/meter/checkin-activity-status` 不带它一样返回 200。

第二条说 accessToken 静态加密解不开。离线解不出是真的，密钥在客户端 native 层。但不需要离线解。借客户端自己的 Electron 运行时取 at-rest 密钥，在同一个子进程里解密，密钥不出进程，明文不落盘。这活儿上游做得很干净，我们直接 vendor 它的脚本。

## 目录结构

| 路径 | 干什么 |
|------|--------|
| `scripts/install-macos.sh` | 装、查、卸，一条脚本三个动作 |
| `scripts/verify.sh` | 单独查一次签到状态，只读，不领 |
| `legacy/ocr-ui/wb_checkin_cua.py` | 老路，OCR 加鼠标，接口挂了才用得上 |
| `legacy/ocr-ui/wb_checkin_scheduled.sh` | 老路的定时 wrapper，已停用 |
| `legacy/ocr-ui/wb_checkin_verify.sh` | 老路的复核 wrapper，已停用 |
| `legacy/wb_daily_checkin.py` | 初版纯 HTTP 脚本，死在凭证加密上，留档 |
| `references/manual-click-guide.md` | 手动五步点击法，最后的兜底 |
| `references/background-why-http-broken.md` | 旧判断，已被推翻，留作史料 |
| `SKILL.md` | 装成 WorkBuddy skill 时读的定义 |

## 上游与版本

真正干活的是 [88lin/workbuddy-auto-signin](https://github.com/88lin/workbuddy-auto-signin)。本仓库不复制它的代码，安装时按固定 commit 拉下来，再用 sha256 核对，对不上就不装。这两个值写在 `scripts/install-macos.sh` 顶部和 `UPSTREAM.txt` 里。

上游有新提交不必跟着动。真要紧的时候看一眼 diff，改完把 commit 和哈希一起换，再提交这个仓库。

## 一个解释器的坑

必须用 `/usr/bin/python3`，本机是 3.9.6。同一份脚本换 3.14.7 跑，卡三分钟一个字节都不吐，最后什么也没返回。这不是网络慢。plist 里已经写死 3.9.6。

## 结果长什么样

```json
{"result": "ALREADY", "report": "今日已签过（今日 +100，连续 19 天，累计 1900 积分）；派 Buddy 去咖啡馆（2 小时后回）；连登兑换「进阶」（+50 积分 +3 能量 +1 次抽奖）；开盲盒获得：100 积分", "needs_attention": false}
```

`result` 四种，`OK` 刚领到，`ALREADY` 今天早领过，`INACTIVE` 非活动期，`AUTH_ERROR` 才是真出事。日常只看 `needs_attention`，false 就不用管。连着两天 true 再动手，多半是客户端升级把解密链路弄断了。

## 风险

这是逆向私有接口，并且借用客户端自己的能力解密钥，本质上绕开了产品设计。腾讯改版就会失效，理论上账号也有被风控的可能。失效不会断签，一天两次机会还在，风控就只能认。

要不要用，自己判断。

## 许可

MIT，版权归 Guyzn Huang，见 [LICENSE](LICENSE)。

上游 88lin/workbuddy-auto-signin 同样是 MIT，版权归 88lin。签到接口是从桌面端逆向来的，与本仓库作者和上游作者都没有官方关系，也和腾讯、WorkBuddy 无关。
