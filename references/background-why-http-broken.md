# 背景：为什么旧 HTTP 签到脚本失效（仅供理解，不要重做离线解密）

> 2026-09-23 WorkBuddy Desktop 升级后，原 HTTP 直领脚本永久失效。
> 本文档记录根因，供理解现状。**离线解密这条路已验证不通，别再花时间。**

## 现象

```
2026-09-23 00:04:13 OK: +100 积分 streak=8     ← 前一天还正常
2026-09-24 00:03:20 FAIL: status HTTP 401 ... openresty / apisix
```

401 来自网关层（openresty/apisix），不是业务接口——请求根本没通过鉴权。

## 根因（双重锁定）

### 锁 1：accessToken 静态加密

凭证文件：`~/Library/Application Support/CodeBuddyExtension/Data/Public/auth/workbuddy-desktop.info`

旧版（明文）：
```json
"accessToken": "eyJhbGciOi..."
```

新版（09-23 起）：
```json
"accessToken": { "$wbEncrypted": 1, "envelope": "eyJzdWl0ZSI6MSwia2V5SWQiOiI5MTI3ZGVhMWI0NDAyMGE3Ii..." }
```

脚本按字符串拼 `Authorization: Bearer <token>`，发出的实际是
`Bearer {'$wbEncrypted': 1, 'envelope': '...'}` → 必然 401。

### 锁 2：Turing 设备指纹头（强制风控）

9-23 新版给签到请求新增强制头 `X-Device-Token`，由腾讯天御风控 SDK（native `turing_sdk.node`）生成。远端有 product feature 开关（Issue #111936），默认开。裸脚本没有这个头，就算拿到明文 token 大概率仍被风控 401。

## 加密方案（从 app.asar 逆向，仅供理解）

- envelope 结构 `{suite:1, keyId, nonce, authTag, ciphertext}`，算法 **AES-256-GCM**，AAD 带 keyId + scheme(`sym-v1`) + 用途。
- `keyId = sha256(key).hex[:16]`（16 位小写 hex）。
- 主密钥（32 字节）存 `~/.workbuddy/keyblob`，被「静态钥」包裹：
  ```json
  {"version":1,"keyId":"74b20cb304ae31df",
   "slots":[{"type":"static-v1","protectorKeyId":"9127dea1b44020a7","wrapped":"<envelope>"}]}
  ```
- 静态钥 payload 叫 `atRestSecretKey`（44 字符 canonical base64），
  `实际 key = sha256(atRestSecretKey 字符串)`，`keyId = sha256(key).hex[:16]`。
- **静态钥不在磁盘上**：由定制 Electron 框架（v37.10.3 fork）C++ 侧 `electron.workbuddyStorage.loggerGet()` 在运行时提供。`loggerIn/loggerOut` 在 asar 里无 JS 调用点 → 密钥在 native 层自举，源码不开源。在 app.asar 和 Electron Framework 二进制里按 base64 候选扫过、用 keyId 逐个反验，**全部不匹配**。

## 结论

- token 本身没过期（expiresAt 2026-11-18），密文 1337 字节确认是正常 JWT 被加密。
- **离线解密不可行**（拿不到 atRestSecretKey），重启/刷新 token 也不改变文件形态（新版强制加密）。
- **唯一可行路径是 UI 自动化**（本 skill 的自动/手动两条路），让官方链路自己带齐加密 token + Turing 头。

## 旧 HTTP 接口存档（若将来 token 又能明文拿到，可直接用）

- `POST https://www.workbuddy.cn/v2/billing/meter/checkin-activity-status`
- `POST https://www.workbuddy.cn/v2/billing/meter/daily-checkin`
- Header：`Authorization: Bearer <accessToken>` + `X-User-Id: <uid>` + `X-Device-Token: <turing>`
- 旧脚本退出码：`0` 成功/已领 · `1` 接口失败 · `2` 凭证缺失 · `3` token 临期 · `4` 凭证已加密（走 UI）
