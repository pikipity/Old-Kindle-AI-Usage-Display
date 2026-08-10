#!/bin/sh
# 启动仪表盘：禁止休眠 + 后台运行主循环
DASH=/mnt/us/dashboard
PID_FILE="$DASH/dashboard.pid"

# 已在跑就先停掉，避免重复启动
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    [ -n "$OLD_PID" ] && kill "$OLD_PID" 2>/dev/null
    rm -f "$PID_FILE"
    sleep 1
fi

if [ ! -f "$DASH/dashboard.sh" ] || [ ! -f "$DASH/config.env" ]; then
    echo "文件缺失：请按 docs/3-kindle-setup.md 把 dashboard.sh 和 config.env 拷到 $DASH/"
    exit 1
fi

# 常亮运行：禁止自动休眠
lipc-set-prop com.lab126.powerd preventScreenSaver 1

cd "$DASH" || exit 1
nohup sh ./dashboard.sh >> "$DASH/dashboard.log" 2>&1 &
echo "仪表盘已启动，日志：$DASH/dashboard.log"
