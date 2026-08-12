#!/usr/bin/env python3
"""用假数据渲染一张效果图到 assets/screenshot.png（README 用，也可当渲染冒烟测试）。

不联网、不需要 API Key。用法：python tools/make_demo.py
"""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "server"))

import render  # noqa: E402

FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


def main():
    font_path = next((p for p in FONT_CANDIDATES if Path(p).exists()),
                     render.__dict__ and "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
    cfg = {"FONT_PATH": font_path, "FETCH_INTERVAL": "60"}

    now = datetime(2026, 8, 10, 16, 9)
    result = {
        "kimi": {
            "ok": True, "ts": now.isoformat(), "reason": "",
            "data": {
                "kind": "plan",
                "week": {"pct": 42.3,
                         "reset": datetime(2026, 8, 17, 0, 0).timestamp()},
                "five_hour": {"pct": 58.0,
                              "reset": (now + __import__("datetime").timedelta(
                                  hours=2.35)).timestamp()},
                "booster": 25.30,
            },
        },
        "deepseek": {
            "ok": True, "ts": now.isoformat(), "reason": "",
            "data": {"total": 100.00, "currency": "CNY",
                     "parts": [("充值", 50.00), ("赠送", 50.00)]},
        },
    }
    hist = {
        "2026-08-09": {"deepseek": 101.20},
        "2026-08-10": {"deepseek": 100.60},
    }

    img = render.build_image(cfg, result, hist, now)
    out = ROOT / "assets" / "screenshot.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)

    land = render.build_landscape_image(cfg, result, hist, now)
    out_land = ROOT / "assets" / "screenshot-landscape.png"
    land.save(out_land, optimize=True)

    print(f"已生成 {out}")
    print(f"已生成 {out_land}（横版布局预览，未旋转；上机文件由服务器旋转 90°）")


if __name__ == "__main__":
    sys.exit(main())
