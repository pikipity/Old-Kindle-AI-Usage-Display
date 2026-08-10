#!/usr/bin/env python3
"""生成 Kindle 端告警横幅 kindle/warning.png（拉取失败时叠加在屏幕顶部）。

仅开发/打包时需要运行一次，产物已提交进仓库，普通使用者无需执行。
用法：python tools/make_warning.py
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "kindle" / "warning.png"
W, H = 1072, 64

# 各平台常见中文字体，按顺序找
FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


def find_font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    print("警告：找不到中文字体，横幅文字可能缺字", file=sys.stderr)
    return ImageFont.load_default()


def main():
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    # 手画警告三角（不依赖字体里的 ⚠ 字形）
    cx, cy, r = 44, H // 2, 20
    d.polygon([(cx - r, cy + r - 4), (cx, cy - r), (cx + r, cy + r - 4)],
              outline=0, width=4)
    d.line([cx, cy - 8, cx, cy + 6], fill=0, width=4)
    d.point((cx, cy + 12), fill=0)

    text = "更新失败，正在显示缓存画面"
    font = find_font(32)
    d.text((84, (H - 36) // 2), text, font=font, fill=0)

    # 底部一条分割线，和下方画面区分开
    d.line([0, H - 2, W, H - 2], fill=0, width=2)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, optimize=True)
    print(f"已生成 {OUT}")


if __name__ == "__main__":
    sys.exit(main())
