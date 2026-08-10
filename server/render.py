#!/usr/bin/env python3
"""
Kindle AI 用量仪表盘 · 服务器渲染进程

常驻循环（由 PM2 托管）：每分钟整点对齐地
  拉取 Kimi / DeepSeek 余额 → 渲染 1072×1448 灰度 PNG → 原子写入 out/dash.png

设计原则：
- 任何单次取数/渲染异常只记日志、不退出，下一分钟再来
- 取数失败时沿用最近一次成功数据渲染（标灰 + 角标），不黑屏
- 每天首次成功取数写一次 history.json 快照，用于展示"较昨日变化"
- 配置改动无需重启：每轮循环重新读 config.env

配置：默认读取仓库根目录 config.env（KEY=VALUE 格式），可用环境变量
DASH_CONFIG 指定别的路径。
"""

import calendar
import json
import math
import os
import sys
import time
import traceback
import urllib.request
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python < 3.9
    ZoneInfo = None

# ---------- 常量 ----------
WIDTH, HEIGHT = 1072, 1448
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"
OUT_FILE = OUT_DIR / "dash.png"
STATE_FILE = OUT_DIR / "state.json"      # 最近一次成功的数据（进程重启不丢）
HISTORY_FILE = ROOT / "history.json"     # 每日余额快照

KIMI_API = "https://api.kimi.com/coding/v1/usages"
DEEPSEEK_API = "https://api.deepseek.com/user/balance"

BLACK, GRAY, LIGHT, WHITE = 0, 110, 210, 255

WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"]


# ---------- 配置 ----------
def load_config(path):
    """解析 KEY=VALUE 配置文件，返回带默认值的 dict。"""
    cfg = {
        "KIMI_CODE_API_KEY": "",
        "DEEPSEEK_API_KEY": "",
        "FONT_PATH": "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "FETCH_INTERVAL": "60",
        "TIMEZONE": "Asia/Shanghai",
    }
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            cfg[key.strip()] = value.strip()
    except FileNotFoundError:
        log(f"警告：配置文件 {path} 不存在，使用全部默认值（API Key 为空）")
    return cfg


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


def get_tz(name):
    if ZoneInfo and name:
        try:
            return ZoneInfo(name)
        except Exception as e:
            log(f"警告：时区 {name} 无效（{e}），回退到服务器本地时间")
    return None  # None = 系统本地时间


# ---------- 取数 ----------
def http_get_json(url, api_key):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "kindle-dash/1.0",
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _num(value):
    """API 数值兼容字符串和数字，失败返回 None。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_reset(value):
    """resetTime 兼容 ISO 字符串和秒/毫秒时间戳，统一返回 epoch 秒，失败 None。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value / 1000 if value > 1e12 else float(value)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def fetch_kimi(key):
    """Kimi For Coding 订阅用量：本周额度 / 5 小时窗口 / 加油包余额。"""
    data = http_get_json(KIMI_API, key)
    out = {"kind": "plan"}

    usage = data.get("usage") or {}
    limit, remaining = _num(usage.get("limit")), _num(usage.get("remaining"))
    if limit and remaining is not None:
        out["week"] = {
            "pct": max(0.0, (limit - remaining) / limit * 100),
            "reset": _parse_reset(usage.get("resetTime")),
        }

    # 频限窗口：取 5 小时窗（window.duration=300 分钟），没有就用第一条
    limits = data.get("limits") or []
    five = next((i for i in limits
                 if _num((i.get("window") or {}).get("duration")) == 300),
                limits[0] if limits else None)
    if five:
        detail = five.get("detail") or {}
        d_limit, d_remaining = _num(detail.get("limit")), _num(detail.get("remaining"))
        if d_limit and d_remaining is not None:
            out["five_hour"] = {
                "pct": max(0.0, (d_limit - d_remaining) / d_limit * 100),
                "reset": _parse_reset(detail.get("resetTime")),
            }

    # 加油包：未开通/停用时余额按 0 展示
    wallet = data.get("boosterWallet") or {}
    status = str(wallet.get("status") or "").upper()
    if status in ("STATUS_ACTIVE", "STATUS_ENABLED"):
        left = _num((wallet.get("balance") or {}).get("amountLeft"))
        out["booster"] = max(0.0, left / 1e8) if left is not None else None
    else:
        out["booster"] = 0.0 if wallet else None
    return out


def fetch_deepseek(key):
    data = http_get_json(DEEPSEEK_API, key)
    infos = data.get("balance_infos") or [{}]
    info = infos[0]
    return {
        "total": float(info.get("total_balance") or 0),
        "currency": info.get("currency") or "CNY",
        "is_available": bool(data.get("is_available", True)),
        "parts": [
            ("充值", float(info.get("topped_up_balance") or 0)),
            ("赠送", float(info.get("granted_balance") or 0)),
        ],
    }


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def collect(cfg, now):
    """
    逐个平台取数，失败时沿用 state.json 里的最近一次成功数据。
    返回 {"kimi": {"ok": bool, "data": dict|None, "ts": str|None, "reason": str}, ...}
    """
    state = load_json(STATE_FILE, {})
    result = {}
    for name, fetcher, key in (
        ("kimi", fetch_kimi, cfg["KIMI_CODE_API_KEY"]),
        ("deepseek", fetch_deepseek, cfg["DEEPSEEK_API_KEY"]),
    ):
        old = state.get(name) or {}
        if not key:
            result[name] = {"ok": False, "data": old.get("data"),
                            "ts": old.get("ts"), "reason": "未配置 API Key"}
            continue
        try:
            data = fetcher(key)
            result[name] = {"ok": True, "data": data, "ts": now.isoformat(), "reason": ""}
            state[name] = {"data": data, "ts": result[name]["ts"]}
        except Exception as e:
            log(f"{name} 取数失败：{e}")
            result[name] = {"ok": False, "data": old.get("data"),
                            "ts": old.get("ts"), "reason": str(e)}
    if any(r["ok"] for r in result.values()):
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return result


# ---------- 每日快照（较昨日） ----------
def update_history(result, today):
    hist = load_json(HISTORY_FILE, {})
    day = dict(hist.get(today) or {})
    changed = False
    for name in ("kimi", "deepseek"):
        # 只有余额类数据（含 total 字段）才做每日快照
        if (result[name]["ok"] and name not in day
                and "total" in (result[name]["data"] or {})):
            day[name] = round(result[name]["data"]["total"], 4)
            changed = True
    if changed:
        hist[today] = day
        keys = sorted(hist)
        if len(keys) > 120:  # 只保留最近 120 天
            for k in keys[:-120]:
                del hist[k]
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=1),
                                encoding="utf-8")
    return hist


def delta_vs_yesterday(hist, today, name, current):
    """找今天之前最近一天的快照做差值；没有则返回 None。"""
    prev = None
    for day in sorted(hist):
        if day < today and name in (hist[day] or {}):
            prev = hist[day][name]
    if prev is None:
        return None
    return round(current - prev, 2)


def delta_vs_today(hist, today, name, current):
    """与今天首次快照的差值（≈今日消耗，负数为减少）；今天还没有快照则 None。"""
    day = hist.get(today) or {}
    if name not in day:
        return None
    return round(current - day[name], 2)


# ---------- 字体 ----------
class Fonts:
    """集中加载字体；字体文件不可用时回退到内置点阵字体（中文会缺字，仅兜底）。"""

    SIZES = {
        "title": 46, "big": 108, "status": 26, "parts": 30, "delta": 32,
        "section": 32, "cal_title": 38, "cal_head": 24,
        "cal_day": 26, "footer": 24,
    }

    def __init__(self, font_path):
        self.ok = True
        try:
            self._fonts = {k: ImageFont.truetype(font_path, s)
                           for k, s in self.SIZES.items()}
        except Exception as e:
            log(f"警告：字体 {font_path} 加载失败（{e}），使用内置字体兜底")
            self.ok = False
            self._fonts = {k: ImageFont.load_default() for k in self.SIZES}

    def __getattr__(self, name):
        return self._fonts[name]


# ---------- 绘图 ----------
def draw_clock(d, cx, cy, r, now):
    """模拟表盘：外圈 + 刻度 + 时针分针（秒针不画，每分钟才刷新）。"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=8)
    for i in range(60):
        ang = math.radians(i * 6 - 90)
        is_hour = i % 5 == 0
        inner = r - (20 if is_hour else 10)
        width = 6 if is_hour else 2
        x0, y0 = cx + inner * math.cos(ang), cy + inner * math.sin(ang)
        x1, y1 = cx + (r - 4) * math.cos(ang), cy + (r - 4) * math.sin(ang)
        d.line([x0, y0, x1, y1], fill=BLACK, width=width)

    def hand(deg, length, width):
        ang = math.radians(deg - 90)
        d.line([cx, cy, cx + length * math.cos(ang), cy + length * math.sin(ang)],
               fill=BLACK, width=width)

    minute_deg = now.minute * 6
    hour_deg = (now.hour % 12) * 30 + now.minute * 0.5
    hand(hour_deg, r * 0.52, 11)
    hand(minute_deg, r * 0.80, 7)
    d.ellipse([cx - 9, cy - 9, cx + 9, cy + 9], fill=BLACK)


def draw_calendar(d, fonts, x0, x1, now):
    """当月日历，周一开头，今天用黑底白字圆点标出。"""
    title = f"{now.year} 年 {now.month} 月"
    tw = d.textlength(title, font=fonts.cal_title)
    d.text(((x0 + x1 - tw) / 2, 48), title, font=fonts.cal_title, fill=BLACK)

    cell_w = (x1 - x0) / 7
    head_y, grid_y, cell_h = 112, 152, 48
    for i, name in enumerate(WEEKDAYS):
        cx = x0 + cell_w * (i + 0.5)
        w = d.textlength(name, font=fonts.cal_head)
        d.text((cx - w / 2, head_y), name, font=fonts.cal_head, fill=GRAY)

    weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(now.year, now.month)
    for row, week in enumerate(weeks):
        for col, day in enumerate(week):
            if day == 0:
                continue
            cx = x0 + cell_w * (col + 0.5)
            cy = grid_y + cell_h * (row + 0.5)
            text = str(day)
            w = d.textlength(text, font=fonts.cal_day)
            if day == now.day:
                r = 22
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLACK)
                d.text((cx - w / 2, cy - 15), text, font=fonts.cal_day, fill=WHITE)
            else:
                d.text((cx - w / 2, cy - 15), text, font=fonts.cal_day, fill=BLACK)


def draw_warn_badge(d, x, y, size):
    """手画警告三角（不依赖字体里的 ⚠ 字形），返回文字起始 x。"""
    h = size
    d.polygon([(x, y + h), (x + h / 2, y), (x + h, y + h)], outline=BLACK, width=3)
    cx = x + h / 2
    d.line([cx, y + h * 0.38, cx, y + h * 0.68], fill=BLACK, width=3)
    d.point((cx, y + h * 0.82), fill=BLACK)
    return x + h + 10


def money(total, currency):
    symbol = "¥ " if currency == "CNY" else f"{currency} "
    return f"{symbol}{total:,.2f}"


def draw_panel(d, fonts, box, title, info, delta_yesterday, delta_today):
    """DeepSeek 余额面板：标题 + 状态 / 超大余额 / 构成条 / 构成明细 / 变化。

    取数失败沿用缓存数据时不再标灰（保持深色可读），只保留右上角 ⚠ 角标。
    """
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=16, outline=BLACK, width=5)
    ink = BLACK

    d.text((x0 + 34, y0 + 28), title, font=fonts.title, fill=BLACK)

    # 右上角状态行
    if not info["ok"]:
        if info["ts"]:
            status = f"缓存数据 · 上次 {info['ts'][11:16]}"
        else:
            status = "暂无数据"
        sx = draw_warn_badge(d, x1 - 34 - 26 - 10 -
                             d.textlength(status, font=fonts.status), y0 + 40, 26)
        d.text((sx, y0 + 38), status, font=fonts.status, fill=GRAY)
    elif info["data"] and not info["data"].get("is_available", True):
        status = "余额不可用"
        sx = draw_warn_badge(d, x1 - 34 - 26 - 10 -
                             d.textlength(status, font=fonts.status), y0 + 40, 26)
        d.text((sx, y0 + 38), status, font=fonts.status, fill=BLACK)
    elif info["ts"]:
        status = f"更新于 {info['ts'][11:16]}"
        d.text((x1 - 34 - d.textlength(status, font=fonts.status), y0 + 40),
               status, font=fonts.status, fill=GRAY)

    d.line([x0 + 30, y0 + 100, x1 - 30, y0 + 100], fill=BLACK, width=3)

    if info["data"] is None:
        # 从未取到数据：给部署期的明确提示
        reason = info["reason"] or "取数失败"
        d.text((x0 + 34, y0 + 150), "—", font=fonts.big, fill=GRAY)
        d.text((x0 + 34, y0 + 290), reason, font=fonts.parts, fill=GRAY)
        d.text((x0 + 34, y0 + 340), "请检查服务器 config.env 配置与网络",
               font=fonts.parts, fill=GRAY)
        return

    data = info["data"]
    total = data["total"]
    d.text((x0 + 34, y0 + 130), money(total, data.get("currency", "CNY")),
           font=fonts.big, fill=ink)

    # 构成条：按 现金/代金券（或 充值/赠送）占比分段，黑色段为前者
    bx0, by, bx1, bh = x0 + 34, y0 + 300, x1 - 34, 34
    d.rectangle([bx0, by, bx1, by + bh], outline=ink, width=3)
    parts = data.get("parts") or []
    if total > 0 and parts:
        first = max(0.0, min(1.0, parts[0][1] / total))
        if first > 0:
            d.rectangle([bx0 + 3, by + 3,
                         bx0 + 3 + (bx1 - bx0 - 6) * first, by + bh - 3], fill=ink)

    # 构成明细（含占比）
    if total > 0 and parts:
        legend = " ｜ ".join(f"{name} {amount:,.2f}（{amount / total:.0%}）"
                            for name, amount in parts)
    else:
        legend = " ｜ ".join(f"{name} {amount:,.2f}" for name, amount in parts)
    d.text((x0 + 34, y0 + 356), legend, font=fonts.parts, fill=ink)

    # 变化：较昨日 ｜ 今日（今日 = 与今日首次快照的差，≈今日消耗）
    def fmt_delta(v):
        if v is None:
            return "—"
        return f"{'+' if v > 0 else ''}{v:,.2f}"

    change = f"较昨日 {fmt_delta(delta_yesterday)} ｜ 今日 {fmt_delta(delta_today)}"
    d.text((x0 + 34, y0 + 402), change, font=fonts.delta, fill=ink)


def draw_quota_section(d, fonts, x0, x1, y, label, pct, reset_text):
    """一个额度区块：标签 + 已用百分比 + 重置时间（一行），下面一条进度条。

    返回区块底部 y 坐标。
    """
    d.text((x0 + 34, y), label, font=fonts.section, fill=BLACK)
    value = f"已用 {pct:.0f}%"
    vw = d.textlength(value, font=fonts.section)
    rx = x1 - 34
    if reset_text:
        rw = d.textlength(reset_text, font=fonts.status)
        d.text((rx - rw, y + 5), reset_text, font=fonts.status, fill=GRAY)
        rx -= rw + 18
    d.text((rx - vw, y), value, font=fonts.section, fill=BLACK)

    by = y + 50
    d.rectangle([x0 + 34, by, x1 - 34, by + 32], outline=BLACK, width=3)
    fill = max(0.0, min(1.0, pct / 100))
    if fill > 0:
        d.rectangle([x0 + 37, by + 3, x0 + 37 + (x1 - x0 - 74) * fill, by + 29],
                    fill=BLACK)
    return by + 32


def draw_plan_panel(d, fonts, box, title, info, now):
    """Kimi For Coding 订阅面板：本周额度 / 5 小时窗口（各含百分比+进度条+重置时间）
    / 加油包余额，三段式分区。"""
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=16, outline=BLACK, width=5)

    d.text((x0 + 34, y0 + 28), title, font=fonts.title, fill=BLACK)

    # 右上角状态行
    if not info["ok"]:
        status = f"缓存数据 · 上次 {info['ts'][11:16]}" if info["ts"] else "暂无数据"
        sx = draw_warn_badge(d, x1 - 34 - 26 - 10 -
                             d.textlength(status, font=fonts.status), y0 + 40, 26)
        d.text((sx, y0 + 38), status, font=fonts.status, fill=GRAY)
    elif info["ts"]:
        status = f"更新于 {info['ts'][11:16]}"
        d.text((x1 - 34 - d.textlength(status, font=fonts.status), y0 + 40),
               status, font=fonts.status, fill=GRAY)

    d.line([x0 + 30, y0 + 100, x1 - 30, y0 + 100], fill=BLACK, width=3)

    data = info["data"]
    if data is None or "week" not in data:
        reason = info["reason"] or "响应中缺少本周额度字段"
        d.text((x0 + 34, y0 + 150), "—", font=fonts.big, fill=GRAY)
        d.text((x0 + 34, y0 + 290), reason, font=fonts.parts, fill=GRAY)
        d.text((x0 + 34, y0 + 340), "请检查服务器 config.env 的 KIMI_CODE_API_KEY",
               font=fonts.parts, fill=GRAY)
        return

    # 区块一：本周额度
    week = data["week"]
    week_reset = None
    if week.get("reset"):
        reset_dt = datetime.fromtimestamp(week["reset"], now.tzinfo)
        week_reset = f"{reset_dt.month}月{reset_dt.day}日 重置"
    bottom = draw_quota_section(d, fonts, x0, x1, y0 + 122,
                                "本周额度", week["pct"], week_reset)

    d.line([x0 + 30, bottom + 20, x1 - 30, bottom + 20], fill=LIGHT, width=2)

    # 区块二：5 小时频限窗口
    five = data.get("five_hour")
    if five:
        five_reset = None
        if five.get("reset"):
            hours = max(0.0, (five["reset"] - now.timestamp()) / 3600)
            five_reset = f"约 {hours:.1f} 小时后重置"
        bottom = draw_quota_section(d, fonts, x0, x1, bottom + 40,
                                    "5 小时窗口", five["pct"], five_reset)
        d.line([x0 + 30, bottom + 20, x1 - 30, bottom + 20], fill=LIGHT, width=2)
        booster_y = bottom + 40
    else:
        booster_y = bottom + 34

    # 区块三：加油包（只显示金额）
    booster = data.get("booster")
    booster_text = "—" if booster is None else f"¥{booster:,.2f}"
    d.text((x0 + 34, booster_y), "加油包余额", font=fonts.section, fill=BLACK)
    bw = d.textlength(booster_text, font=fonts.section)
    d.text((x1 - 34 - bw, booster_y), booster_text, font=fonts.section, fill=BLACK)


def build_image(cfg, result, hist, now):
    """纯渲染：给定数据产出一张 1072×1448 灰度图（不取数、不写盘，便于测试）。"""
    fonts = Fonts(cfg["FONT_PATH"])
    img = Image.new("L", (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(img)

    # 顶部：表盘（左）+ 当月日历（右，今天黑底标出）
    draw_clock(d, 205, 225, 155, now)
    draw_calendar(d, fonts, 400, 1032, now)

    d.line([40, 460, 1032, 460], fill=LIGHT, width=2)

    # 两大面板：Kimi 订阅用量 + DeepSeek 余额
    today = now.strftime("%Y-%m-%d")
    draw_plan_panel(d, fonts, (40, 485, 1032, 935), "KIMI CODE", result["kimi"], now)

    ds = result["deepseek"]
    ds_total = ds["data"]["total"] if ds["data"] else 0.0
    if ds["data"] is None:
        d_yesterday = d_today = None
    else:
        d_yesterday = delta_vs_yesterday(hist, today, "deepseek", ds_total)
        d_today = delta_vs_today(hist, today, "deepseek", ds_total)
    draw_panel(d, fonts, (40, 950, 1032, 1400), "DEEPSEEK", ds, d_yesterday, d_today)

    # 底部状态行
    interval = cfg.get("FETCH_INTERVAL", "60")
    footer = f"渲染于 {now:%Y-%m-%d %H:%M} · 每 {interval} 秒更新"
    if not result["kimi"]["ok"] or not result["deepseek"]["ok"]:
        footer += " · 部分数据未更新"
    fw = d.textlength(footer, font=fonts.footer)
    d.text(((WIDTH - fw) / 2, HEIGHT - 36), footer, font=fonts.footer, fill=GRAY)
    return img


# ---------- 主流程 ----------
def render_once(cfg):
    tz = get_tz(cfg.get("TIMEZONE"))
    now = datetime.now(tz)
    result = collect(cfg, now)
    hist = update_history(result, now.strftime("%Y-%m-%d"))
    img = build_image(cfg, result, hist, now)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUT_DIR / "dash.png.tmp"
    img.save(tmp, format="PNG", optimize=True)
    os.replace(tmp, OUT_FILE)  # 原子替换，nginx 不会读到半截文件

    kimi = result["kimi"]
    ds = result["deepseek"]
    kimi_txt = (f"本周{kimi['data']['week']['pct']:.0f}%"
                if kimi["data"] and "week" in kimi["data"] else "失败")
    log("渲染完成 "
        f"kimi={kimi_txt} "
        f"deepseek={'¥%.2f' % ds['data']['total'] if ds['data'] else '失败'} "
        f"-> {OUT_FILE}")


def main():
    cfg_path = os.environ.get("DASH_CONFIG", str(ROOT / "config.env"))
    log(f"启动，配置文件：{cfg_path}")
    while True:
        started = time.time()
        try:
            cfg = load_config(cfg_path)  # 每轮重读，改配置不用重启
            render_once(cfg)
        except Exception:
            traceback.print_exc()
        interval = 60
        try:
            interval = max(15, int(cfg.get("FETCH_INTERVAL", "60")))
        except Exception:
            pass
        # 整点对齐：睡到 interval 的下一个整数倍（默认即下一分钟整）
        delay = interval - (time.time() % interval)
        if delay < 2:  # 上一轮耗时过长压到边界了，补一整轮
            delay += interval
        time.sleep(delay)


if __name__ == "__main__":
    sys.exit(main())
