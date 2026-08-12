#!/bin/sh
# Kindle AI 用量仪表盘 · 主循环
# 每分钟从服务器拉取渲染好的图片并刷屏显示。
# 拉取失败：显示本地缓存的上一张图 + 屏幕顶部叠加告警横幅，恢复后自动消失。
# 左上角常显 WiFi 状态图标（扇形）：有 IP=连接，无 IP=断开（斜杠）。
# 屏幕方向由 /mnt/us/dashboard/orientation 决定（portrait / landscape-cw / landscape-ccw），
# 每轮读取，KUAL 菜单切换方向后下一轮刷新即生效。

DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CONFIG="$DIR/config.env"
CACHE_DIR="$DIR/cache"
CACHE_IMG="$CACHE_DIR/dash.png"
TMP_IMG="$CACHE_DIR/dash.tmp"
WARN_IMG="$DIR/warning.png"
ORIENTATION_FILE="$DIR/orientation"
WIFI_ON_IMG="$DIR/icons/wifi-on.png"
WIFI_OFF_IMG="$DIR/icons/wifi-off.png"
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

# WiFi 是否已连接（有 IPv4 地址）
wifi_up() {
    ifconfig wlan0 2>/dev/null | grep -q "inet addr"
}

# 根据方向标记选图片 URL（横版图与竖版图同目录，换文件名即可）
current_url() {
    ori=$(cat "$ORIENTATION_FILE" 2>/dev/null)
    case "$ori" in
        landscape-cw)  echo "${IMAGE_URL%/*}/dash-landscape-cw.png" ;;
        landscape-ccw) echo "${IMAGE_URL%/*}/dash-landscape-ccw.png" ;;
        *)             echo "$IMAGE_URL" ;;
    esac
}

# 刷屏：$1=图片，$2=warn 时叠加告警横幅；WiFi 图标永远最后画
show_screen() {
    "$FBINK" -q -b -g file="$1"
    if [ "$2" = "warn" ] && [ -f "$WARN_IMG" ]; then
        "$FBINK" -q -b -g file="$WARN_IMG"
    fi
    if wifi_up; then
        [ -f "$WIFI_ON_IMG" ] && "$FBINK" -q -b -g file="$WIFI_ON_IMG,x=44,y=14"
    else
        [ -f "$WIFI_OFF_IMG" ] && "$FBINK" -q -b -g file="$WIFI_OFF_IMG,x=44,y=14"
    fi
    "$FBINK" -q -s -W GC16 $FLASH
}

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

    URL=$(current_url)
    ok=0
    if wget -q -T 20 -O "$TMP_IMG" "$URL" 2>/dev/null && [ -s "$TMP_IMG" ]; then
        mv "$TMP_IMG" "$CACHE_IMG"
        ok=1
    else
        rm -f "$TMP_IMG"
    fi

    if [ "$ok" -eq 1 ]; then
        show_screen "$CACHE_IMG"
    elif [ -f "$CACHE_IMG" ]; then
        echo "$(date '+%F %T') 拉取失败（$URL），显示缓存图并叠加告警" >&2
        show_screen "$CACHE_IMG" warn
    else
        echo "$(date '+%F %T') 拉取失败且无缓存图，${FETCH_INTERVAL}s 后重试" >&2
    fi

    sleep "$FETCH_INTERVAL"
done
