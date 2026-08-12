#!/bin/sh
# 启动/切换仪表盘：记录方向 + 禁止休眠 + 关背光 + 后台运行主循环
# 用法：start.sh [portrait|landscape-cw|landscape-ccw]（默认 portrait）
# 重复启动会先杀旧进程，所以"启动即切换"（换方向直接点对应菜单项即可）
DASH=/mnt/us/dashboard
PID_FILE="$DASH/dashboard.pid"
ORIENTATION="${1:-portrait}"

case "$ORIENTATION" in
    portrait|landscape-cw|landscape-ccw) ;;
    *) echo "未知方向：$ORIENTATION（应为 portrait / landscape-cw / landscape-ccw）"; exit 1 ;;
esac

if [ ! -f "$DASH/dashboard.sh" ] || [ ! -f "$DASH/config.env" ]; then
    echo "文件缺失：请按 docs/3-kindle-setup.md 把 dashboard.sh 和 config.env 拷到 $DASH/"
    exit 1
fi

echo "$ORIENTATION" > "$DASH/orientation"

# 已在跑就先停掉，避免重复启动
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    [ -n "$OLD_PID" ] && kill "$OLD_PID" 2>/dev/null
    rm -f "$PID_FILE"
    sleep 1
fi

# 常亮运行：禁止自动休眠
lipc-set-prop com.lab126.powerd preventScreenSaver 1

# 关闭背光（0-24 档，0 = 熄灭；想保留背光就把 0 改成需要的亮度，或删掉这行）
lipc-set-prop com.lab126.powerd flIntensity 0

cd "$DASH" || exit 1
nohup sh ./dashboard.sh >> "$DASH/dashboard.log" 2>&1 &
echo "仪表盘已启动（方向：$ORIENTATION），日志：$DASH/dashboard.log"
