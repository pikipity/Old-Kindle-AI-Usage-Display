#!/bin/sh
# 停止仪表盘：杀掉主循环 + 恢复自动休眠 + 清屏
DASH=/mnt/us/dashboard
PID_FILE="$DASH/dashboard.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill "$PID" 2>/dev/null; then
        echo "已停止仪表盘进程（PID $PID）"
    fi
    rm -f "$PID_FILE"
else
    echo "仪表盘未在运行"
fi

lipc-set-prop com.lab126.powerd preventScreenSaver 0

# 恢复背光到中等亮度（配合 start.sh 的关背光）
lipc-set-prop com.lab126.powerd flIntensity 12

# 清屏（找到 fbink 就用，找不到就算了，下次开屏系统会自己重绘）
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
if [ -n "$FBINK" ]; then
    "$FBINK" -q -fk
    "$FBINK" -q -pm -M "Dashboard stopped"
fi

echo "已恢复自动休眠，按电源键或触摸屏幕返回系统界面"
