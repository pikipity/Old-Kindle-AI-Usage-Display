# 服务器端安装教程

本篇把仪表盘的服务器端跑起来：`render.py` 常驻运行，每分钟调用 Kimi Code / DeepSeek 的用量查询接口，用 Pillow 渲染出一张 1072×1448 灰度图写到 `out/dash.png`，再由 nginx 通过 HTTP 提供给 Kindle 下载。

完成后你会得到一个类似 `http://YOUR_DOMAIN/kindle-dash-YOUR_TOKEN/dash.png` 的图片地址，**浏览器打开能看到图，本篇就算成功**。

## 前置条件

开始之前，确认你已经有：

- 一台 Linux 服务器（教程以阿里云为例；Debian/Ubuntu 与 CentOS/Alibaba Cloud Linux 的命令略有不同，文中会分别给出）
- 服务器上已有一个跑在 **80 端口**的 nginx HTTP 站点（本篇只在它的配置里加 5 行，不新开端口、不动安全组）
- 已安装 PM2（`pm2 -v` 能输出版本号）
- git（`git --version`，选压缩包上传方式可以不用）
- Python 不用预装：第 2 步会用 uv 自动管理（服务器需要能访问 astral.sh 和 PyPI）
- 两个 API Key：
  - Kimi Code 控制台：<https://www.kimi.com/code/console>，在控制台里创建 API Key（注意：**与 Kimi 开放平台 platform.kimi.com 的 Key 不通用**，别拿错）
  - DeepSeek 开放平台：<https://platform.deepseek.com>，同样在控制台创建
  - 两个 Key 都只留在服务器上使用，不会下发到 Kindle
- 会基本的 SSH 登录和编辑 nginx 配置

## 第 1 步：上传代码到 /srv/kindle-dash/

项目约定部署路径为 `/srv/kindle-dash/`。两种上传方式任选其一。

### 方式 A：git clone（推荐，以后好更新）

```bash
sudo git clone https://github.com/pikipity/Old-Kindle-AI-Usage-Display.git /srv/kindle-dash
sudo chown -R $USER:$USER /srv/kindle-dash
```

`chown` 把目录属主改成你的登录用户，否则后面建 venv、写 `out/` 都会撞权限。

### 方式 B：scp/sftp 上传压缩包

在你自己的电脑上，把项目打包上传（Windows 用户也可以用 WinSCP 之类的 sftp 工具把压缩包拖到服务器 home 目录）：

```bash
# 在本地项目目录的上一级执行
tar czf kindle-dash.tar.gz Old-Kindle-AI-Usage-Display/
scp kindle-dash.tar.gz 用户名@服务器IP:~/
```

然后 SSH 到服务器解开：

```bash
sudo mkdir -p /srv/kindle-dash
sudo tar xzf ~/kindle-dash.tar.gz -C /srv/kindle-dash --strip-components=1
sudo chown -R $USER:$USER /srv/kindle-dash
```

### 验证

```bash
ls /srv/kindle-dash/
```

应能看到 `config.env`、`server/`、`kindle/`、`docs/` 等内容。

## 第 2 步：安装 uv 并创建 Python 环境

服务器端的 Python 环境用 [uv](https://docs.astral.sh/uv/) 管理：比传统的 venv + pip 快得多，而且连 Python 版本本身都能自动处理。

先装 uv（官方一行脚本）：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

装完按终端提示把 uv 加进 PATH（一般是 `source ~/.local/bin/env`，或者干脆重新登录一次 SSH）。

> 服务器网络访问不了 astral.sh 的话，也可以用 `pip install uv` 或 pipx 安装，效果一样。

然后用 uv 建环境、装依赖（项目只依赖 Pillow 一个第三方库，声明在仓库根的 `pyproject.toml`）：

```bash
cd /srv/kindle-dash
uv sync
```

`uv sync` 会在项目根目录创建 `.venv/` 并装好全部依赖。系统 Python 太旧（< 3.9）也没关系，uv 会自动下载一个受管 Python 来用。

### 验证

```bash
uv --version
/srv/kindle-dash/.venv/bin/python -c "import PIL; print(PIL.__version__)"
```

两条都正常输出即可。

## 第 3 步：安装中文字体

图片上有中文（"余额""较昨日"等），需要 Noto Sans CJK 字体。

```bash
# Debian / Ubuntu
sudo apt install -y fonts-noto-cjk

# CentOS / Alibaba Cloud Linux
sudo yum install -y google-noto-sans-cjk-ttc-fonts
```

### 验证

```bash
fc-list :lang=zh
```

- Debian/Ubuntu 装完后字体默认就在 `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`，与 `config.env` 里 `FONT_PATH` 的默认值一致，不用改。
- CentOS/Alibaba Cloud Linux 的实际路径可能不同。从 `fc-list :lang=zh` 的输出里挑一个字重为 Regular 的 `.ttc` 文件，记下它的完整路径，等下填进 `FONT_PATH`。

## 第 4 步：生成 URL TOKEN

图片地址上带一段随机串当访问口令，避免余额信息被陌生人撞见。生成一个：

```bash
openssl rand -hex 8
```

输出类似 `3f9a1c7e82b0d456`。把它记下来（下文统称 `YOUR_TOKEN`），第 5 步填 `IMAGE_URL` 和第 7 步改 nginx 都要用，**两处必须完全一致**。

## 第 5 步：填写 config.env

仓库根目录的 `config.env` 是唯一的配置文件。格式严格 `KEY=VALUE`，**等号两边不能有空格**——Kindle 端的 shell 脚本会直接 `source` 它，服务器端也是按这个格式解析的。

```bash
cd /srv/kindle-dash
nano config.env   # 或用你顺手的编辑器
```

文件内容如下，逐项说明：

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

- `KIMI_CODE_API_KEY`：Kimi Code 控制台创建的 Key（`https://www.kimi.com/code/console`，与 Kimi 开放平台的 Key 不通用），直接跟在等号后面，不要加引号、不要带空格。
- `DEEPSEEK_API_KEY`：DeepSeek 开放平台控制台创建的 Key，同上。
- `FONT_PATH`：中文字体路径。Debian/Ubuntu 保持默认即可；CentOS/Alibaba Cloud Linux 填第 3 步 `fc-list` 查到的实际路径。
- `IMAGE_URL`：**服务器端的 render.py 用不到这一项**，它是给第 3 篇教程里 Kindle 端脚本用的。建议现在顺手填好：把 `YOUR_DOMAIN` 换成你的域名、`YOUR_TOKEN` 换成第 4 步生成的随机串。这份 `config.env` 之后会原样拷到 Kindle 上，填好一次省得再改。
- `FETCH_INTERVAL`：取数与渲染的间隔（秒），默认 `60`。
- `FULL_REFRESH_EVERY`：Kindle 端每 N 次局部刷新做一次全刷清残影，默认 `60`（即约每小时一次）。
- `TIMEZONE`：时钟面板使用的时区，默认 `Asia/Shanghai`。

填好保存。

### 防止真实 Key 被提交（仅 git clone 方式需要）

如果你是用 git clone 部署的，执行：

```bash
cd /srv/kindle-dash
git update-index --skip-worktree config.env
```

作用是让 git 假装这个文件没改过：真实 Key 不会被误提交带出去，以后 `git pull` 更新代码也不会和本地填的值冲突。哪天想恢复跟踪，执行 `git update-index --no-skip-worktree config.env`。

用压缩包上传的目录不是 git 仓库，跳过这一步即可。

## 第 6 步：自检——手动跑一次渲染

`render.py` 是常驻循环进程（每分钟整点对齐执行一轮：取数 → 渲染 → 写 `out/dash.png`），直接前台跑会一直占着终端。用 `timeout` 包一下，跑一分多钟看结果：

```bash
cd /srv/kindle-dash
timeout 90 uv run server/render.py
```

跑满 90 秒被自动杀掉是预期行为，不是报错。期间终端会打印取数和渲染日志。

### 验证

```bash
ls -l /srv/kindle-dash/out/dash.png
```

`out/` 目录由脚本自动创建，不用手动建。文件存在且修改时间就是刚才，说明渲染链路通了。

三个说明：

- **没填 API Key 也能出图**（对应面板上会显示未配置提示），所以 Key 还没申请下来也可以先把这一步跑通。
- 图片写入是原子的（先写临时文件再改名），不用担心 Kindle 拉到半张图。
- `render.py` 默认读仓库根的 `config.env`；如果配置文件在别的位置，用环境变量指定：

```bash
DASH_CONFIG=/path/to/config.env timeout 90 uv run server/render.py
```

## 第 7 步：nginx 加 location 并浏览器验证

打开你**现有 80 端口站点**的 nginx 配置文件（通常在 `/etc/nginx/sites-enabled/` 或 `/etc/nginx/conf.d/` 下，具体位置看你服务器的习惯），在它的 `server { ... }` 块里加入下面 5 行——这是对现有配置的唯一改动：

```nginx
location ^~ /kindle-dash-YOUR_TOKEN/ {
    alias /srv/kindle-dash/out/;
    add_header Cache-Control "no-store";
}
```

把 `YOUR_TOKEN` 换成第 4 步生成的随机串。仓库里的 `server/nginx.conf.example` 就是这段，可以对照复制。`Cache-Control: no-store` 是为了防止 CDN 或浏览器缓存旧图。

检查语法并重载：

```bash
sudo nginx -t && sudo systemctl reload nginx
```

`nginx -t` 输出 `syntax is ok` 和 `test is successful` 才算通过。

### 验证

浏览器访问：

```
http://YOUR_DOMAIN/kindle-dash-YOUR_TOKEN/dash.png
```

能看到仪表盘图片即成功。第 6 步自检生成的那张图，此刻就能通过 URL 看到了。

> 如果你的站点配置了强制跳转 HTTPS，注意 Kindle 端的 wget 对证书环境很挑。本项目默认前提就是纯 HTTP 的 80 端口站点，建议让这条 location 保持 HTTP 可访问。

## 第 8 步：PM2 托管常驻

自检没问题后，把 `render.py` 交给 PM2：崩溃自重启、开机自启。

```bash
cd /srv/kindle-dash
cp server/ecosystem.config.js.example ecosystem.config.js
```

模板已按 `/srv/kindle-dash` 的默认路径写好（解释器指向 uv 创建的 `/srv/kindle-dash/.venv/bin/python`）。按本教程部署的话不用改；部署路径不同的话，打开核对一遍再启动。

启动并保存进程列表：

```bash
pm2 start ecosystem.config.js
pm2 save
```

如果这台服务器还从没配过 PM2 开机自启，再执行一次 `pm2 startup`（它会打印一条需要你复制执行的 sudo 命令，照做即可）；以前配过就跳过。

### 验证

```bash
pm2 status
pm2 logs kindle-dash
```

- `pm2 status` 里 `kindle-dash` 状态为 `online`，运行时长随时间增长，而不是不停被重置回 0（不停重置说明在崩溃重启，去查下面的排错表）。
- `pm2 logs kindle-dash` 里能看到每分钟一轮的取数与"渲染完成"日志（脚本每分钟整点对齐执行一轮，耐心等待一两个整点）。

至此服务器端部署完成。

### 可选但建议：给 PM2 日志加轮转

PM2 默认把日志追加写在 `~/.pm2/logs/` 里，**不限制大小也不轮转**。本项目的日志量很小（每分钟一行，一年约几十 MB），但长期裸奔没好处。装一个 `pm2-logrotate` 模块即可自动按大小切分、压缩、清理：

```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M    # 单个日志超过 10MB 就切分
pm2 set pm2-logrotate:retain 7        # 最多保留 7 份历史
pm2 set pm2-logrotate:compress true   # 历史日志 gzip 压缩
```

注意这是 PM2 全局设置，对你服务器上**其他 PM2 应用**的日志同样生效（一般正是你想要的）。想手动清空所有日志可以随时 `pm2 flush`。装完不用重启任何应用，`pm2-logrotate` 作为独立模块进程自动生效；以后改了上面的 `pm2 set` 配置，`pm2 restart pm2-logrotate` 一次让它立刻生效即可。

## 常见错误对照表

| 现象 | 可能原因 | 处理 |
|---|---|---|
| 日志里 API 返回 401 / 鉴权失败 | Key 填错、没填，或复制时带了空格、引号；也可能是拿错了 Key 类型 | 检查 `config.env` 等号右侧是否干净。用 curl 直接验证 Key：`curl -H "Authorization: Bearer 你的Key" https://api.kimi.com/coding/v1/usages`（DeepSeek 换成 `https://api.deepseek.com/user/balance`），返回 JSON 说明 Key 本身没问题。Kimi 注意必须用 **Kimi Code 控制台**签发的 Key，开放平台的 Key 调这个接口会 401 |
| 日志提示字段解析失败 / 图上数据缺失 | 平台 API 改版，返回结构与脚本预期不符 | 用上面的 curl 看实际返回：Kimi 应含 `usage`（本周额度）、`limits`（频限窗口）、`boosterWallet`（加油包），DeepSeek 应含 `balance_infos[0].total_balance` / `topped_up_balance` / `granted_balance`。字段名对不上就改 `render.py` 里对应的解析，或提 issue |
| 日志报字体找不到（`cannot open resource` / `OSError`） | `FONT_PATH` 路径错，或字体根本没装 | 执行 `fc-list :lang=zh` 拿真实路径，与 `FONT_PATH` 逐字符核对；`fc-list` 无输出说明字体没装上，回第 3 步重装 |
| `pm2 logs` 里进程反复重启 | ecosystem 里解释器路径错，或环境/依赖没装好 | 确认 `ecosystem.config.js` 中解释器指向 `/srv/kindle-dash/.venv/bin/python` 且文件确实存在（`/srv/kindle-dash/.venv/bin/python --version` 试一下）；再回第 2 步重跑一次 `uv sync` |
| 浏览器访问图片 404 | location 没生效，或 URL 与配置不一致 | 确认片段加在 **80 端口站点**的 server 块里且已 reload；确认 URL 里的 TOKEN 与 nginx 片段完全一致；确认 `out/dash.png` 文件确实存在 |
| 浏览器访问图片 403 | `out/` 目录权限不够，nginx 用户读不到 | `ls -ld /srv /srv/kindle-dash /srv/kindle-dash/out` 逐级检查，保证其它用户有进入和读权限：目录 `chmod 755`、文件 `644` |
| 浏览器能访问但 Kindle 拉不到 | Kindle 侧的网络 / DNS / 系统时间问题，不是服务器问题 | 服务器端已确认正常，转向第 3 篇教程的排错表，排查 Kindle 的 WiFi、域名解析和系统时间 |
| `uv sync` 失败 | 网络不通（装 uv、下载 Python 或 Pillow 都要出网） | 确认服务器能访问 astral.sh 和 PyPI；PyPI 慢可以换国内镜像：`UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple uv sync` |
| 时钟面板时间不对，或"较昨日变化"明显异常 | 服务器时间或时区错 | `timedatectl` 检查系统时间，核对 `config.env` 的 `TIMEZONE`。每天首次成功取数会写 `history.json` 快照，系统时间错会让"较昨日"比较失真 |
| 图上面板右上角带 ⚠ "缓存数据"角标 | 服务器取数失败，正沿用最近一次成功数据渲染 | 这是设计好的兜底行为，程序没挂。看日志里取数报错的具体原因（网络、Key、API 变更），恢复后角标自动消失 |

## 安全提示

- `config.env` 里是真实 API Key：**不要**让它进入公开仓库。git 部署的务必执行第 5 步的 `skip-worktree`；如果哪天要推送代码，推送前用 `git diff --cached` 自查一遍暂存区里没有真实 Key、域名、IP、TOKEN。
- 图片 URL 里的 TOKEN 是唯一的访问口令，别贴到公开地方。怀疑泄露就重新 `openssl rand -hex 8` 生成一个，nginx 片段和 `IMAGE_URL` 两处一起换。
- 确认服务器时间正确：`timedatectl` 看一眼。每天的余额快照（`history.json`）、"较昨日变化"和时钟面板都依赖系统时间。

## 下一步

- Kindle 已经越狱完成 → 继续看 [docs/3-kindle-setup.md](3-kindle-setup.md)，部署 Kindle 端并联调。
- Kindle 还没越狱 → 先看 [docs/1-jailbreak.md](1-jailbreak.md)。
