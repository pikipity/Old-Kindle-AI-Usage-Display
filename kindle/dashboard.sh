#!/bin/sh
# Kindle AI 用量仪表盘 · 主循环
# 每分钟从服务器拉取渲染好的图片并刷屏显示。
# 拉取失败：显示本地缓存的上一张图 + 屏幕顶部叠加告警横幅，恢复后自动消失。

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG="$DIR/config.env"
CACHE_DIR="$DIR/cache"
CACHE_IMG="$CACHE_DIR/dash.png"
TMP_IMG="$CACHE_DIR/dash.tmp"
WARN_IMG="$DIR/warning.png"
PID_FILE="$DIR/dashboard.pid"

# --- 读配置（KEY=VALUE 格式，直接 source） ---
if [ ! -f "$CONFIG" ]; then
    echo "错误：找不到配置文件 $CONFIG（请按 docs/3-kindle-setup.md 拷贝并填写）" >&2
    exit 1
fi
. "$CONFIG"

FETCH_INTERVAL=${FETCH_INTERVAL:-60}
FULL_REFRESH_EVERY=${FULL_REFRESH_EVERY:-60}

if [ -z "$IMAGE_URL" ] || echo "$IMAGE_URL" | grep -q "YOUR_DOMAIN"; then
    echo "错误：请先在 config.env 里把 IMAGE_URL 改成真实的图片地址" >&2
    exit 1
fi

# --- 探测 fbink（按常见安装位置逐个找） ---
FBINK=""
for p in "$(command -v fbink 2>/dev/null)" \
         /mnt/us/fbink/bin/fbink \
         /mnt/us/extensions/fbink/bin/fbink \
         /usr/local/bin/fbink; do
    if [ -n "$p" ] && [ -x "$p" ]; then
        FBINK="$p"
        break
    fi
done
if [ -z "$FBINK" ]; then
    echo "错误：找不到 fbink，请先安装 FBInk（见 docs/1-jailbreak.md）" >&2
    exit 1
fi

mkdir -p "$CACHE_DIR"
echo $$ > "$PID_FILE"

echo "$(date '+%F %T') 启动，地址：$IMAGE_URL"
echo "$(date '+%F %T') 每 ${FETCH_INTERVAL}s 刷新，每 ${FULL_REFRESH_EVERY} 次全刷，fbink：$FBINK"

count=0
while true; do
    count=$((count + 1))
    # 每隔 FULL_REFRESH_EVERY 次做一次闪烁全刷（-f），清残影；其余为普通刷新
    if [ $((count % FULL_REFRESH_EVERY)) -eq 0 ]; then
        FLASH="-f"
    else
        FLASH=""
    fi

    ok=0
    if wget -q -T 20 -O "$TMP_IMG" "$IMAGE_URL" 2>/dev/null && [ -s "$TMP_IMG" ]; then
        mv "$TMP_IMG" "$CACHE_IMG"
        ok=1
    else
        rm -f "$TMP_IMG"
    fi

    if [ "$ok" -eq 1 ]; then
        "$FBINK" -q -g file="$CACHE_IMG" -W GC16 $FLASH
    elif [ -f "$CACHE_IMG" ]; then
        echo "$(date '+%F %T') 拉取失败，显示缓存图并叠加告警" >&2
        # 先写帧缓冲（-b 不刷新），最后统一刷新一次，避免闪两下
        "$FBINK" -q -b -g file="$CACHE_IMG"
        if [ -f "$WARN_IMG" ]; then
            "$FBINK" -q -b -g file="$WARN_IMG"
        fi
        "$FBINK" -q -s -W GC16 $FLASH
    else
        echo "$(date '+%F %T') 拉取失败且无缓存图，${FETCH_INTERVAL}s 后重试" >&2
    fi

    sleep "$FETCH_INTERVAL"
done
