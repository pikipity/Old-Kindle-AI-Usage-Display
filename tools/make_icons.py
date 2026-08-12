#!/usr/bin/env python3
"""生成 Kindle 端 WiFi 状态图标 + 样式候选预览图（供挑选）。

产物：
  kindle/icons/wifi-on.png / wifi-off.png   —— 实际使用的 40×40 图标（默认扇形款）
  assets/wifi-icon-candidates.png           —— 候选样式对比图，挑好款式后改 STYLE 重跑

用法：python tools/make_icons.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "kindle" / "icons"
SHEET = ROOT / "assets" / "wifi-icon-candidates.png"

STYLE = "fan"  # 定稿款式：fan（扇形）/ bars（信号柱）

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

BLACK, GRAY, WHITE = 0, 150, 255


def draw_fan(d, size, ink):
    """经典 WiFi 扇形：三条同心弧 + 圆点，中心在下边中点。"""
    cx, cy = size / 2, size * 0.86
    w = max(3, size // 9)
    for r in (size * 0.70, size * 0.48, size * 0.27):
        d.arc([cx - r, cy - r, cx + r, cy + r], 225, 315, fill=ink, width=w)
    dot = size * 0.09
    d.ellipse([cx - dot, cy - dot, cx + dot, cy + dot], fill=ink)


def draw_bars(d, size, ink):
    """信号柱：四根逐级升高的柱子。"""
    n = 4
    bw = size * 0.14
    gap = size * 0.07
    x = size * 0.08
    bottom = size * 0.88
    for i in range(n):
        h = size * (0.22 + 0.18 * i)
        d.rectangle([x, bottom - h, x + bw, bottom], fill=ink)
        x += bw + gap


def add_slash(d, size, ink):
    """断开标记：左上到右下一条斜杠。"""
    w = max(3, size // 10)
    m = size * 0.08
    d.line([m, m, size - m, size - m], fill=ink, width=w)


def make_icon(style, on, size=40):
    img = Image.new("L", (size, size), WHITE)
    d = ImageDraw.Draw(img)
    ink = BLACK if on else GRAY
    if style == "fan":
        draw_fan(d, size, ink)
    else:
        draw_bars(d, size, ink)
    if not on:
        add_slash(d, size, BLACK)
    return img


def find_font(sz):
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def make_sheet():
    """四宫格候选图：扇形/信号柱 × 连接/断开，放大展示便于挑选。"""
    cells = [
        ("A1 扇形·连接", make_icon("fan", True, 96)),
        ("A2 扇形·断开", make_icon("fan", False, 96)),
        ("B1 信号柱·连接", make_icon("bars", True, 96)),
        ("B2 信号柱·断开", make_icon("bars", False, 96)),
    ]
    cw, ch, pad = 240, 220, 20
    sheet = Image.new("L", (cw * 2 + pad * 3, ch * 2 + pad * 3), WHITE)
    d = ImageDraw.Draw(sheet)
    font = find_font(24)
    for i, (label, icon) in enumerate(cells):
        x = pad + (i % 2) * (cw + pad)
        y = pad + (i // 2) * (ch + pad)
        d.rectangle([x, y, x + cw, y + ch], outline=BLACK, width=2)
        sheet.paste(icon, (x + (cw - 96) // 2, y + 24))
        tw = d.textlength(label, font=font)
        d.text((x + (cw - tw) / 2, y + ch - 60), label, font=font, fill=BLACK)
    SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(SHEET, optimize=True)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_icon(STYLE, True).save(OUT_DIR / "wifi-on.png", optimize=True)
    make_icon(STYLE, False).save(OUT_DIR / "wifi-off.png", optimize=True)
    make_sheet()
    print(f"已生成 {OUT_DIR}/wifi-on.png, wifi-off.png（样式 {STYLE}）")
    print(f"候选对比图 {SHEET}")


if __name__ == "__main__":
    sys.exit(main())
