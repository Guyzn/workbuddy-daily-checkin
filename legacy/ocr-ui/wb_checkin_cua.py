#!/usr/bin/env python3
"""
wb_checkin_cua.py — WorkBuddy 每日签到（CUA/UI 自动化版）

背景：2026-09-23 WorkBuddy 升级后 accessToken 静态加密 + 签到接口强制
Turing 设备指纹头，原 HTTP 脚本 (wb_daily_checkin.py) 失效。
本脚本改用 UI 自动化驱动官方链路：激活 App → 点头像 → Buddy加油站 → 立即领取。

用法：直接用 cua-mcp 的 venv 解释器运行（或系统 python3 + 已装依赖）：
  ~/.workbuddy/skills/cua-mcp/.venv/bin/python3 wb_checkin_cua.py

依赖：cua-mcp skill 的 modules（Quartz/AppKit/Pillow）+ 系统 tesseract（chi_sim）。
退出码：0=签到成功或今日已签；1=失败（详见 stderr/日志）。
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUA_MCP_CANDIDATES = [
    os.path.join(SKILL_DIR, "..", "cua-mcp"),           # 同级的 cua-mcp skill
    os.path.expanduser("~/.workbuddy/skills/cua-mcp"),  # 用户级 cua-mcp
]
CUA_MCP_DIR = next((p for p in CUA_MCP_CANDIDATES if os.path.isdir(p)), None)
if not CUA_MCP_DIR:
    sys.stderr.write("ERROR: cua-mcp skill not found. Install it first.\n")
    sys.exit(1)
sys.path.insert(0, CUA_MCP_DIR)

LOG_FILE = os.path.expanduser("~/.workbuddy/logs/wb_checkin_cua.log")
SHOT_DIR = os.path.expanduser("~/.workbuddy/logs/wb_checkin_shots")  # 保留最近 3 次截图便于排查
APP_NAME = "WorkBuddy"
KEEP_RUNS = 3  # 截图按「运行批次」保留最近 N 次


def preflight():
    """启动自检：依赖缺失时给出人话提示再退出。"""
    if subprocess.run(["which", "tesseract"], capture_output=True).returncode != 0:
        sys.stderr.write(
            "ERROR: 未安装 tesseract。执行 brew install tesseract tesseract-lang 后重试，"
            "或按 references/manual-click-guide.md 走手动兜底。\n"
        )
        sys.exit(1)
    try:
        import Quartz  # noqa: F401
        ok = Quartz.AXIsProcessTrustedWithOptions(None)
        if not ok:
            sys.stderr.write(
                "ERROR: 未授予辅助功能权限。系统设置 → 隐私与安全性 → 辅助功能 → 打开本终端/App，"
                "然后重试；或按 references/manual-click-guide.md 走手动兜底。\n"
            )
            sys.exit(1)
    except (ImportError, AttributeError):
        pass  # 环境无 Quartz 时由后续截图调用自行报错


def log(msg):
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


def ocr_words(png_path, upscale=3):
    """tesseract TSV OCR → [(text, x, y, w, h)]，坐标已换算回原图像素。"""
    from PIL import Image
    im = Image.open(png_path)
    big = im.resize((int(im.width * upscale), int(im.height * upscale)), Image.LANCZOS)
    big_path = png_path + ".big.png"
    big.save(big_path)
    base = png_path + ".ocr"
    subprocess.run(
        ["tesseract", big_path, base, "-l", "chi_sim", "--psm", "6", "tsv"],
        check=True, capture_output=True, timeout=60,
    )
    words = []
    with open(base + ".tsv") as f:
        for line in f.readlines()[1:]:
            cols = line.rstrip("\n").split("\t")
            if len(cols) >= 12 and cols[11].strip():
                x, y, w, h = (int(cols[i]) / upscale for i in (6, 7, 8, 9))
                words.append((cols[11].strip(), x, y, w, h))
    return words


def find_phrase(words, phrase):
    """在同一行（y 接近）的词里找包含短语的连续词段，返回其中心坐标。

    只取「第一个包含短语字符的词」开始的连续段，避免行首图标被 OCR 误识别
    成的杂词（如「抱」）把点击中心带偏。
    """
    phrase = phrase.replace(" ", "")
    first_char = phrase[0]
    rows = {}
    for text, x, y, w, h in words:
        rows.setdefault(round(y / 14), []).append((x, y, w, h, text.replace(" ", "")))
    for items in rows.values():
        items.sort()
        # 用滑动起点：从每个包含首字符的词开始向后拼接
        for start in range(len(items)):
            if first_char not in items[start][4]:
                continue
            joined = ""
            seg = []
            for sp in items[start:]:
                joined += sp[4]
                seg.append(sp)
                if phrase in joined:
                    x0 = seg[0][0]
                    y0 = min(s[1] for s in seg)
                    x1 = max(s[0] + s[2] for s in seg)
                    y1 = max(s[1] + s[3] for s in seg)
                    return ((x0 + x1) / 2, (y0 + y1) / 2)
    return None


class Checkin:
    def __init__(self):
        import asyncio
        from modules import computer_control as cc
        from modules import screenshot as ss
        self.asyncio = asyncio
        self.cc = cc
        self.ss = ss
        os.makedirs(SHOT_DIR, exist_ok=True)
        self.run_tag = time.strftime("%Y%m%d-%H%M%S")  # 本批截图前缀
        self._gc_shots()
        self.win = None  # (x, y, w, h)

    @staticmethod
    def _gc_shots():
        """按运行批次（时间戳前缀）只保留最近 KEEP_RUNS 次，防垃圾累积。"""
        try:
            prefixes = sorted({
                f.split("-", 1)[0] + "-" + f.split("-", 2)[1]
                for f in os.listdir(SHOT_DIR)
                if re.match(r"\d{8}-\d{6}-", f)
            })
            for old in prefixes[:-KEEP_RUNS]:
                for f in os.listdir(SHOT_DIR):
                    if f.startswith(old + "-"):
                        try:
                            os.remove(os.path.join(SHOT_DIR, f))
                        except OSError:
                            pass
        except OSError:
            pass

    def run_async(self, coro):
        return self.asyncio.run(coro)

    def activate(self):
        self.run_async(self.cc.activate_app(APP_NAME))
        time.sleep(2.0)  # 焦点切换慢，多等一拍
        wm = self.cc.WindowManager()
        for w in wm.list_windows():
            title = str(w.get("title", ""))
            owner = str(w.get("owner", ""))
            if APP_NAME in title or APP_NAME in owner:
                b = w["bounds"]
                self.win = (b["X"], b["Y"], b["Width"], b["Height"])
                break
        if not self.win:
            raise RuntimeError("找不到 %s 窗口（App 未在运行？）" % APP_NAME)
        log("window: %s" % (self.win,))

    def sidebar_region(self):
        """应用侧栏区域（窗口左部），签到气泡/面板都出现在这里。"""
        wx, wy, ww, wh = self.win
        return (wx, wy, min(420, ww // 4), wh)

    def shot(self, name, region=None):
        if region:
            png = self.ss.capture_region_quartz(*region)
        else:
            png = self.ss.capture_fullscreen_quartz()
        path = os.path.join(SHOT_DIR, "%s-%s.png" % (self.run_tag, name))
        with open(path, "wb") as f:
            f.write(png)
        return path

    def click(self, x, y):
        log("click (%.0f, %.0f)" % (x, y))
        self.run_async(self.cc.mouse_click(int(x), int(y)))

    def ocr_find_click(self, name, region, phrase, must=True):
        """对区域截图 OCR 找短语并点击（屏幕坐标）。返回是否点击。"""
        path = self.shot(name, region)
        words = ocr_words(path)
        hit = find_phrase(words, phrase)
        if not hit:
            if must:
                log("OCR 未找到「%s」，词表: %s" % (phrase, [w[0] for w in words][:30]))
            return False
        self.click(region[0] + hit[0], region[1] + hit[1])
        return True

    def run(self):
        self.activate()
        wx, wy, ww, wh = self.win

        # 0) 前置：若侧栏底部已有签到气泡（上轮残留），先关掉
        sidebar = self.sidebar_region()
        words = ocr_words(self.shot("pre", sidebar), upscale=3)
        hit = find_phrase(words, "今日可领") or find_phrase(words, "每日可领")
        if hit:
            self.click(wx + ww // 2, wy + wh // 2)  # 点主区域空白处关闭
            time.sleep(1.0)

        # 1) 点左下角头像弹出菜单（菜单展开慢/点击偶尔落空，重试 3 次）
        menu_region = (wx, max(0, wy + wh - 560), 520, 540)
        for attempt in range(3):
            self.click(wx + 22, wy + wh - 28)
            time.sleep(2.0 + attempt * 0.5)
            if self.ocr_find_click("menu%d" % attempt, menu_region, "Buddy加油站", must=False):
                break
        else:
            raise RuntimeError("头像菜单里没找到 Buddy加油站入口（重试3次均失败）")
        # 3) 等签到面板出现（有时要几秒），对侧栏 OCR 找「立即领取」
        sidebar = self.sidebar_region()
        words = []
        for attempt in range(4):
            time.sleep(2.5)
            words = ocr_words(self.shot("panel%d" % attempt, sidebar), upscale=2)
            hit = find_phrase(words, "立即领取")
            if hit:
                break
            text = "".join(w[0] for w in words)
            if re.search(r"已领\d+天", text):
                break
        else:
            hit = None
        if not hit:
            text = "".join(w[0] for w in words)
            if re.search(r"已领\d+天", text):
                log("未找到「立即领取」且出现「已领N天」→ 今日已签到，跳过")
                return "already"
            raise RuntimeError("面板里没找到「立即领取」，词表: %s" % [w[0] for w in words][:40])
        # 点击前记录当前天数，用于事后交叉验证 N → N+1
        m_before = re.search(r"已领(\d+)天", "".join(w[0] for w in words))
        days_before = int(m_before.group(1)) if m_before else None
        self.click(sidebar[0] + hit[0], sidebar[1] + hit[1])
        time.sleep(3.0)

        # 4) 验证：「立即领取」消失 + 天数 +1（双判据）
        words = ocr_words(self.shot("verify", sidebar), upscale=2)
        text = "".join(w[0] for w in words)
        if find_phrase(words, "立即领取"):
            raise RuntimeError("点击后「立即领取」仍在，签到未生效")
        m_after = re.search(r"已领(\d+)天", text)
        if m_after:
            days_after = int(m_after.group(1))
            if days_before is not None and days_after != days_before + 1:
                raise RuntimeError("天数未 +1（前 %s 后 %s），疑似未生效" % (days_before, days_after))
            log("验证通过：已领%d天（+%d）" % (days_after, days_after - (days_before or days_after - 1)))
        else:
            log("验证通过：按钮已消失（天数 OCR 未读出，单判据通过）")
        return "claimed"


def main():
    preflight()
    try:
        result = Checkin().run()
    except Exception as e:
        log("FAIL: %s" % e)
        return 1
    log("OK: %s" % result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
