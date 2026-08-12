# AGENTS.md — Kindle AI 用量仪表盘

本文件记录项目方案与约定，所有代码与文档编写必须遵循。方案已经用户逐轮确认（v3），未与用户讨论前不得擅自变更架构性决策。

## 1. 项目目标

把 Kindle Paperwhite 3（第 7 代，固件 5.16.2.1.1）改造为独立运行的桌面仪表盘：

- **主体**：Kimi Code 订阅用量（本周额度 / 5h 窗口 / 加油包）、DeepSeek 余额（两大面板，占屏约 3/4）
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
| Kimi Code（订阅） | `GET https://api.kimi.com/coding/v1/usages` | Bearer Key（Kimi Code 控制台签发，**与开放平台 Key 不通用**） | usage（本周 limit/remaining/resetTime）、limits（5h 窗口，`window.duration=300`）、boosterWallet（加油包，amountLeft 单位 1e-8 元） |
| DeepSeek | `GET https://api.deepseek.com/user/balance` | Bearer Key | total / topped_up / granted（数值是字符串，granted 为未过期赠金） |

- 展示口径：Kimi 面板 = 本周额度% + 进度条 + 5h 窗口 + 加油包；DeepSeek 面板 = 余额 + 构成 + **较昨日/今日变化**（官方无用量明细 API，服务器每天存一次快照到 `history.json` 算变化）。
- **失败兜底分两层**：
  - 服务器取数失败：渲染时沿用最近一次成功数据，面板右上角加 ⚠ 缓存角标（数据保持深色不标灰），不黑屏。
  - **Kindle 拉取失败（wget 失败/超时）**：显示本地缓存的上一张图，并用 fbink 在屏幕顶部叠加一行警告文字，下次成功拉取后警告自动消失。两级兜底互不相同：图内角标表示"服务器数据旧"，屏上叠字表示"Kindle 连不上服务器"。
- **WiFi 状态图标（Kindle 端叠加，与横幅同机制）**：画面角落常显 40×40 扇形图标——`ifconfig wlan0` 有 inet addr → 实心；无 → 斜杠。与 wget 成败组合：斜杠+横幅=断网；实心+横幅=服务器/远端问题。图标永远最后绘制，不被横幅遮盖。位置：三种方向都在**画面左上角**（表盘上方空白）——竖屏用帧缓冲 x44,y14；landscape-cw 用 x44,y1394（物理左下角）；landscape-ccw 用 x988,y14（物理右上角）。图标文件按方向预旋转（`wifi-*-cw/ccw.png`）。

## 4. 服务器端

- 部署路径 `/srv/kindle-dash/`（clone 本仓库），Python 环境用 **uv** 管理（根目录 `pyproject.toml` 声明依赖，`uv sync` 建 `.venv`，`uv.lock` 入库），**仅依赖 Pillow**，HTTP 请求用标准库 urllib，不加多余依赖。
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
KIMI_CODE_API_KEY=
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
│   ├── 1-jailbreak.md           # 详细越狱教程（大纲见 §9）
│   ├── 2-server-setup.md        # 详细服务器安装教程
│   └── 3-kindle-setup.md        # 详细 Kindle 端安装教程
├── server/
│   ├── render.py
│   ├── nginx.conf.example
│   └── ecosystem.config.js.example
├── pyproject.toml               # uv 依赖声明（仅 pillow）
├── kindle/
│   ├── dashboard.sh             # 主循环 + 失败叠字告警 + WiFi 图标 + 方向选择
│   ├── warning.png              # 告警横幅（make_warning.py 生成）
│   ├── icons/                   # WiFi 图标（make_icons.py 生成）
│   └── kual/ai-dashboard/
│       ├── config.xml             # KUAL 扩展声明（KUAL 靠它发现扩展）
│       ├── menu.json              # 四项：竖屏/横屏顺/横屏逆/关闭
│       └── bin/{start.sh, start-portrait.sh, start-landscape-cw.sh, start-landscape-ccw.sh, stop.sh}
├── tools/
│   ├── make_demo.py             # 假数据渲染效果图（冒烟测试）
│   ├── make_warning.py / make_icons.py
│   ├── powertest.sh / buttontest.sh   # 休眠方案验证脚本（方案已否决，留档）
└── assets/                      # README 效果图（竖版 + 横版）
```

刻意保持扁平简单，不拆模块、不上框架。

## 7. Kindle 端

- **越狱**（用户本人 + 数据线操作，agent 提供逐步指令写入 docs/1-jailbreak.md）：备份 → LanguageBreak（**会恢复出厂**）→ hotfix → KUAL + MRPI → **屏蔽 OTA**（此后永不升级固件、不恢复出厂）。
- 装 fbink；设备上布局：

```
/mnt/us/extensions/ai-dashboard/   # KUAL 扩展（菜单四项：竖屏/横屏顺/横屏逆/关闭）
/mnt/us/dashboard/
├── dashboard.sh
├── config.env                     # 只填 IMAGE_URL
├── icons/{wifi-on,wifi-off}.png   # WiFi 状态图标
├── orientation                    # 方向标记（start.sh 写入，dashboard.sh 每轮读）
└── cache/dash.png                 # 拉取失败时的兜底图
```

- 运行模式：常亮（`preventScreenSaver`）+ 背光关闭（start.sh 设 `flIntensity 0`）+ 插电 + WiFi 常开。
- 刷新策略：每分钟局部刷新；每 `FULL_REFRESH_EVERY` 次做一次全刷清残影；拉取失败按 §3 第二层兜底处理。
- **方向切换**：KUAL 点对应方向菜单项 → `start.sh <portrait|landscape-cw|landscape-ccw>` 写 orientation 标记 → 杀旧进程重启（启动即切换）；`dashboard.sh` 每轮读标记，把 `IMAGE_URL` 文件名替换为对应图（`dash.png` / `dash-landscape-cw.png` / `dash-landscape-ccw.png`）。

## 8. 屏幕布局

竖屏 1072×1448，高对比黑白灰度，大色块少渐变，两米外可读：

- 顶部约 1/4：模拟表盘时钟（左）+ 当月日历（右，今天黑底标出）
- 中部约 3/8：KIMI CODE 面板，三段式（细分隔线）：本周额度、5h 频限窗口各为"标签 + 已用百分比 + 进度条 + 重置时间"，加油包只显示余额
- 下部约 3/8：DEEPSEEK 面板——超大字号余额 + 构成条（充值/赠送占比）+ 构成明细（含百分比）+ 变化（较昨日 ｜ 今日；`is_available` 为假时显示"余额不可用"角标）
- 底部小字：渲染时间 / 数据异常提示；取数失败不标灰，仅右上角 ⚠ 角标

**横屏 1448×1072**（独立排版，非简单缩放）：左栏约 500px（表盘上、日历下），右栏约 900px（KIMI 面板上、DEEPSEEK 面板下，各 440 高），底部小字。服务器每轮输出三张图：`dash.png`（竖版）、`dash-landscape-cw.png` / `dash-landscape-ccw.png`（横版分别顺/逆时针旋转 90° 写入 1072×1448 文件，fbink 不做旋转）。

## 9. 安装教程大纲（docs/，必须详细到可照做）

三篇教程面向"没越狱过 Kindle、只会在服务器上改网站"的用户，每篇都包含：前置条件清单、逐步命令/操作、每步的验证方法、常见错误对照表。

### docs/1-jailbreak.md — Kindle 越狱

- 风险清单与备份（恢复出厂、书籍/个人文档导出、云端书籍说明）
- 前置检查：固件必须 ≤5.16.2.1.1、设备无密码锁、电量充足
- LanguageBreak 逐步操作：文件拷贝 → 演示模式触发 → hotfix 安装 → 重启验证越狱成功
- 安装 KUAL + MRPI
- 安装 fbink
- 屏蔽 OTA 更新（并强调：此后永不升级固件、永不恢复出厂）
- 每步附官方指南（kindlemodding / MobileRead）对应链接，命令与界面提示要具体到菜单层级

### docs/2-server-setup.md — 服务器端安装

- 前置条件：已有跑在 80 端口的 nginx 站点、Python3、PM2、git
- 上传代码（git clone 或 scp/sftp）到 `/srv/kindle-dash/`
- 安装 uv（官方脚本）+ `uv sync` 建环境装依赖
- 安装中文字体（Noto Sans CJK 的各发行版包名）
- 编辑 `config.env`（每项怎么填、Key 去哪申请、token 怎么生成）+ `git update-index --skip-worktree config.env`
- 单次手动运行 `render.py` 验证出图（看 `out/dash.png`）
- nginx：把 `nginx.conf.example` 片段并入现有 server 块 → `nginx -t` → reload → 浏览器访问图片 URL 验证
- PM2：复制 ecosystem 模板、填解释器路径 → `pm2 start` → `pm2 save` → `pm2 logs` 验证每分钟出图
- 排错表：API 401/余额字段缺失/字体找不到/权限问题/PM2 重启循环

### docs/3-kindle-setup.md — Kindle 端安装

- 前置条件：已越狱（docs/1）、已装 fbink
- 用 USB 大容量模式拷贝文件：`kindle/dashboard.sh` + 根目录 `config.env` → `/mnt/us/dashboard/`；`kindle/kual/ai-dashboard/` → `/mnt/us/extensions/`
- 在电脑上编辑 `config.env` 填 `IMAGE_URL`（强调用支持 LF 换行的编辑器，如 VS Code/Notepad++，别用 Windows 记事本旧版本）
- 安全弹出 USB
- KUAL 菜单启动仪表盘，验证刷屏；stop 恢复
- 排错表：脚本无执行权限/路径错/wget 超时/屏幕残留系统 UI

## 10. 实施顺序

1. agent 写完全部代码与文档（本仓库骨架 + server/ + kindle/ + docs/）
2. 用户部署服务器端，浏览器访问图片 URL 验证出图
3. 用户越狱 Kindle（照 docs/1-jailbreak.md）
4. 用户拷入 Kindle 端文件，KUAL 启动，联调
5. 截图补进 README，开源发布（GitHub）

## 11. 编码约定

- 代码、注释、提交信息、文档：docs 用中文，代码标识符英文，注释适量中文
- 最小改动、最小依赖：服务器端仅 Pillow；Kindle 端纯 busybox shell + fbink，不引入 curl/jq/python
- 所有脚本失败时给出清晰中文报错，方便开源用户排查
- 不执行任何 git 提交/推送操作，除非用户明确要求

## 12. 已评估并否决的方案（防止重复调研）

- **电源键休眠（2026-08 用户实测后否决）**：
  - 路径 B（真·系统休眠）：按键休眠/唤醒本身正常，但实测（tools/powertest.sh）`touchScreenSaverTimeout`、`deferSuspend`（单次与周期性）均无法禁用约 10 分钟的超时自动休眠，"按键睡但不自动睡"不成立，否决。
  - 路径 A（软休眠）：`readyToSuspend`/`wakeFromSuspend` 两个 lipc 事件名实测不存在；且软休眠无法真正禁用触摸（系统框架存活，需 evtest --grab 独占触摸节点才可解，引入额外二进制），用户放弃。
  - 已确认事实：内置屏保图在 `/usr/share/blanket/screensaver/`；`preventScreenSaver 1` 时电源键无休眠效果（恢复方法 `lipc-set-prop com.lab126.powerd preventScreenSaver 0`）。
- **重力感应自动旋转横屏**：PW3 无加速度计（Kindle 全系仅 Oasis/Scribe 线有），做不了；以 KUAL 菜单手动切换横屏（顺/逆时针）替代，已实现。
