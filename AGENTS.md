# AGENTS.md — Kindle AI 用量仪表盘

本文件记录项目方案与约定，所有代码与文档编写必须遵循。方案已经用户逐轮确认（v3），未与用户讨论前不得擅自变更架构性决策。

## 1. 项目目标

把 Kindle Paperwhite 3（第 7 代，固件 5.16.2.1.1）改造为独立运行的桌面仪表盘：

- **主体**：Kimi 开放平台余额、DeepSeek 余额（两大面板，占屏约 3/4）
- **次要**：模拟表盘时钟 + 当月日历（顶部约 1/4）
- 常亮插电运行，连家庭 WiFi，每分钟更新一次，脱离电脑

## 2. 架构（已定稿）

```
┌──────────────┐  每分钟 wget 一张图   ┌─────────────────────┐
│  Kindle PW3   │ ◄── HTTP(域名,80) ──│  阿里云服务器          │
│  越狱 + fbink │    dash.png          │  PM2 常驻 render.py   │
│  只下载+刷屏  │                      │  Pillow 渲染          │
└──────────────┘                      │  ↕ 调余额 API         │
                                      │  Kimi / DeepSeek      │
                                      └─────────────────────┘
```

核心原则：**Kindle 端零业务逻辑**，取数、渲染、时钟、日历全在服务器；API Key 只在服务器，Kindle 接触不到。

## 3. 数据来源

| 平台 | 接口 | 认证 | 字段 |
|---|---|---|---|
| Kimi | `GET https://api.moonshot.cn/v1/users/me/balance` | Bearer Key | available / voucher / cash |
| DeepSeek | `GET https://api.deepseek.com/user/balance` | Bearer Key | total / topped_up / granted |

- 展示口径：**余额 + 较昨日变化**（官方无用量明细 API，用户已确认接受）。服务器每天存一次快照到 `history.json`。
- **失败兜底分两层**：
  - 服务器取数失败：渲染时沿用最近一次成功数据，该数据标灰 + 图内 ⚠ 角标，不黑屏。
  - **Kindle 拉取失败（wget 失败/超时）**：显示本地缓存的上一张图，并用 fbink 在屏幕顶部叠加一行警告文字（如 `⚠ 更新失败 04:12`），下次成功拉取后警告自动消失。两级兜底互不相同：图内角标表示"服务器数据旧"，屏上叠字表示"Kindle 连不上服务器"。

## 4. 服务器端

- 部署路径 `/srv/kindle-dash/`（clone 本仓库），Python venv，**仅装 Pillow**，HTTP 请求用标准库 urllib，不加多余依赖。
- `render.py`：单文件（约 200 行），常驻循环：每分钟整点对齐地 取数 → 渲染 1072×1448 灰度 PNG → 写 `out/dash.png`；异常时记日志不退出。
- **PM2 托管**（用户已有 PM2，不用 cron）：`pm2 start ecosystem.config.js` → `pm2 save`，崩溃自重启、开机自启。
- **nginx**：复用现有 HTTP 站点（80 端口、域名访问），在其 server 块中新增 5 行（**对现有配置的唯一改动**；不新开端口、不动安全组）：

```nginx
location ^~ /kindle-dash-YOUR_TOKEN/ {
    alias /srv/kindle-dash/out/;
    add_header Cache-Control "no-store";
}
```

- YOUR_TOKEN 用 `openssl rand -hex 8` 生成，作为 URL 口令，与 `config.env` 中 `IMAGE_URL` 保持一致。

## 5. 配置与敏感信息（单一文件、入库、占位符）

仓库根目录 `config.env`，**提交进 git**，所有值留占位符，部署时手动填写：

```bash
# ---------- 服务器端必填 ----------
KIMI_API_KEY=
DEEPSEEK_API_KEY=
FONT_PATH=/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
# ---------- Kindle 端必填 ----------
IMAGE_URL=http://YOUR_DOMAIN/kindle-dash-YOUR_TOKEN/dash.png
# ---------- 可选（有默认值） ----------
FETCH_INTERVAL=60
FULL_REFRESH_EVERY=60
TIMEZONE=Asia/Shanghai
```

约定：

- 格式严格 `KEY=VALUE`，等号两侧无空格——`dashboard.sh` 要 `source` 它；`render.py` 手写解析（约 10 行，可用 `DASH_CONFIG` 环境变量覆盖路径）。
- 严禁使用 `.env.example` + gitignore 模式（用户明确否决）。
- 部署后执行 `git update-index --skip-worktree config.env` 防止真实值被误提交、避免 pull 冲突——此步骤必须写进 docs。
- nginx `nginx.conf.example` 是复制粘贴用片段（含 YOUR_TOKEN 占位）。
- 推送前检查 `git diff --cached`，真实 Key、域名、IP、Token 永不入库。

## 6. 仓库结构

```
Old-Kindle-AI-Usage-Display/
├── README.md                    # 效果图、架构、快速开始
├── LICENSE                      # MIT
├── .gitignore                   # out/、history.json、*.log、venv（不排除配置文件）
├── AGENTS.md                    # 本文件
├── config.env                   # ★ 唯一配置：入库、占位符、部署时手改
├── docs/
│   ├── 1-jailbreak.md           # LanguageBreak 越狱指引 + 风险清单
│   ├── 2-server-setup.md        # venv → config.env → nginx 5行 → PM2
│   └── 3-kindle-setup.md        # fbink → 拷贝 → KUAL 启动
├── server/
│   ├── render.py
│   ├── requirements.txt         # 仅 pillow
│   ├── nginx.conf.example
│   └── ecosystem.config.js.example
├── kindle/
│   ├── dashboard.sh             # 主循环 + 失败叠字告警
│   └── kual/ai-dashboard/
│       ├── menu.json
│       └── bin/{start.sh, stop.sh}
└── assets/                      # README 效果图，后续补
```

刻意保持扁平简单，不拆模块、不上框架。

## 7. Kindle 端

- **越狱**（用户本人 + 数据线操作，agent 提供逐步指令写入 docs/1-jailbreak.md）：备份 → LanguageBreak（**会恢复出厂**）→ hotfix → KUAL + MRPI → **屏蔽 OTA**（此后永不升级固件、不恢复出厂）。
- 装 fbink；设备上布局：

```
/mnt/us/extensions/ai-dashboard/   # KUAL 扩展（菜单入口 start/stop）
/mnt/us/dashboard/
├── dashboard.sh
├── config.env                     # 只填 IMAGE_URL
└── cache/dash.png                 # 拉取失败时的兜底图
```

- 运行模式：常亮（`preventScreenSaver`）+ 插电 + WiFi 常开。
- 刷新策略：每分钟局部刷新；每 `FULL_REFRESH_EVERY` 次做一次全刷清残影；拉取失败按 §3 第二层兜底处理。

## 8. 屏幕布局

竖屏 1072×1448，高对比黑白灰度，大色块少渐变，两米外可读：

- 顶部约 1/4：模拟表盘时钟（左）+ 当月日历（右，今天圈出）
- 中部约 3/8：KIMI 面板——超大字号余额 + 余额条 + 现金/代金券明细 + 较昨日变化
- 下部约 3/8：DEEPSEEK 面板——同上（充值/赠送明细）
- 底部小字：最后更新时间 / 服务器数据异常 ⚠

## 9. 实施顺序

1. agent 写完全部代码与文档（本仓库骨架 + server/ + kindle/ + docs/）
2. 用户部署服务器端，浏览器访问图片 URL 验证出图
3. 用户越狱 Kindle（照 docs/1-jailbreak.md）
4. 用户拷入 Kindle 端文件，KUAL 启动，联调
5. 截图补进 README，开源发布（GitHub）

## 10. 编码约定

- 代码、注释、提交信息、文档：docs 用中文，代码标识符英文，注释适量中文
- 最小改动、最小依赖：服务器端仅 Pillow；Kindle 端纯 busybox shell + fbink，不引入 curl/jq/python
- 所有脚本失败时给出清晰中文报错，方便开源用户排查
- 不执行任何 git 提交/推送操作，除非用户明确要求
