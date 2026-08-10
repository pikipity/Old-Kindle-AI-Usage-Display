# 教程三：Kindle 端安装

这是系列教程的最后一篇：把 Kindle 端文件装进已经越狱好的 Kindle Paperwhite 3，让仪表盘跑起来。

- 教程一：[1-jailbreak.md](1-jailbreak.md) —— 越狱，安装 KUAL / MRPI / fbink
- 教程二：[2-server-setup.md](2-server-setup.md) —— 服务器端渲染与出图
- 教程三（本篇）：Kindle 端安装、启动与日常使用

本篇不需要在 Kindle 上敲任何命令，全是"电脑上拷贝文件 + KUAL 里点菜单"。

## 一、前置条件

动手前逐条确认：

1. **Kindle 已越狱**，并已装好 KUAL、MRPI、fbink（照 [1-jailbreak.md](1-jailbreak.md) 完成）。验证：主界面能打开 KUAL 菜单。
2. **服务器端已跑通**（照 [2-server-setup.md](2-server-setup.md) 完成）。验证：电脑浏览器访问 `http://YOUR_DOMAIN/kindle-dash-YOUR_TOKEN/dash.png`，能看到一张仪表盘图片。
3. **Kindle 已连上家里的 WiFi**，屏幕右上角有 WiFi 信号图标。
4. 一根**能传数据的 USB 线**。有些廉价线只能充电，插上电脑没反应就换一根。
5. 电脑上有一个支持 LF 换行的文本编辑器：**VS Code 或 Notepad++**。不要用 Windows 自带的老版记事本——它会把换行符存成 CRLF，导致 Kindle 上的脚本读取配置失败。

## 二、逐步安装

### 第 1 步：把仓库下载到电脑

二选一：

- 会用 git：`git clone https://github.com/pikipity/Old-Kindle-AI-Usage-Display.git`
- 不用 git：在 GitHub 仓库页面点 **Code → Download ZIP**，下载后解压。

验证：打开仓库文件夹，能看到 `kindle/` 目录和根目录下的 `config.env` 文件。

### 第 2 步：USB 连接 Kindle，拷贝文件

1. Kindle 用 USB 线连电脑。Kindle 屏幕进入 USB 大容量模式，电脑上出现一个可移动磁盘（Windows 在"此电脑"里，Mac 在桌面或 Finder 侧栏）。
   - 这个可移动磁盘的根目录就是 Kindle 系统里的 `/mnt/us`，下文一律用 `/mnt/us` 表示。
   - Mac 注意：拷贝时系统可能在盘里生成 `._` 开头的小文件，无害，忽略即可。
2. 按下表拷贝（"→"左边是仓库里的位置，右边是 Kindle 磁盘里的位置）：

| 仓库里的文件 | 拷到 Kindle 的位置 |
|---|---|
| `kindle/dashboard.sh` | `/mnt/us/dashboard/dashboard.sh` |
| `kindle/warning.png` | `/mnt/us/dashboard/warning.png` |
| `config.env`（仓库根目录） | `/mnt/us/dashboard/config.env` |
| `kindle/kual/ai-dashboard/`（整个文件夹） | `/mnt/us/extensions/ai-dashboard/` |

说明：

- `dashboard` 文件夹磁盘上没有，自己新建一个。
- `extensions` 文件夹已经存在（装 KUAL 时建的），把 `ai-dashboard` 整个文件夹放进去即可。注意最终路径必须是 `/mnt/us/extensions/ai-dashboard/menu.json`，不要多套一层目录，也不要只把里面几个文件散着丢进去。

3. 拷完后，Kindle 磁盘上的布局应该是：

```text
/mnt/us/dashboard/
├── dashboard.sh
├── warning.png
└── config.env
/mnt/us/extensions/ai-dashboard/
├── config.xml
├── menu.json
└── bin/
    ├── start.sh
    └── stop.sh
```

（`/mnt/us/dashboard/cache/` 不用手工建，脚本第一次运行时会自己创建，用来存最近一张拉取成功的图。）

验证：对着上面的布局逐层点开检查，7 个文件一个不少、层级完全一致。

### 第 3 步：在电脑上编辑 config.env

此时 Kindle 还连着 USB、磁盘还挂载着，直接编辑磁盘里的 `/mnt/us/dashboard/config.env`：

1. 用 VS Code 或 Notepad++ 打开它。
2. 只需要填一行：

```bash
IMAGE_URL=http://YOUR_DOMAIN/kindle-dash-YOUR_TOKEN/dash.png
```

把 `YOUR_DOMAIN` 换成你的域名、`YOUR_TOKEN` 换成服务器教程里生成的那个 token，必须与服务器 nginx 里配置的完全一致（对照 [2-server-setup.md](2-server-setup.md)）。其余字段（`KIMI_CODE_API_KEY` 等）是服务器端用的，在 Kindle 上留空不管。

3. 保存前检查三件事：
   - 等号两侧**没有空格**：是 `IMAGE_URL=http://...`，不是 `IMAGE_URL = http://...`；
   - 换行符是 **LF**：VS Code 看窗口右下角，显示 `CRLF` 就点它切换成 `LF`；Notepad++ 用菜单"编辑 → 文档格式转换 → 转为 Unix (LF)"；
   - URL 没有加引号、没有混入中文标点。
4. 保存。

验证：关掉文件重新打开，确认改动还在；再在电脑浏览器访问一次这个 `IMAGE_URL`，确认能出图——Kindle 待会儿每分钟拉的就是这个地址。

### 第 4 步：安全弹出 USB

1. Windows：右下角托盘 →"安全删除硬件"→ 弹出 Kindle；Mac：Finder 里点 Kindle 磁盘旁的推出按钮。
2. 等 Kindle 退出大容量模式、回到主界面。

**不要不弹出直接拔线**。磁盘有写缓存，直接拔可能让 `config.env` 的修改根本没写进去，之后排查半天才发现是这一步的问题。

### 第 5 步：从 KUAL 启动仪表盘

1. 在 Kindle 主界面打开 **KUAL**。
2. 在菜单里找到 **AI Dashboard**，点 **启动仪表盘**。
3. 启动脚本会做两件事：执行 `lipc-set-prop com.lab126.powerd preventScreenSaver 1` 禁止 Kindle 自动休眠，然后用 nohup 在后台运行 `dashboard.sh`（日志写在 `/mnt/us/dashboard/dashboard.log`）。

验证：

- 1 分钟内，屏幕应刷新出仪表盘画面：顶部是模拟表盘时钟和当月日历，中部是 KIMI 面板，下部是 DEEPSEEK 面板。
- 再等一两分钟，看时钟的分钟有没有变化——变了说明"每分钟拉图刷屏"的循环工作正常。
- 想进一步确认后台状态：重新连 USB，看 `/mnt/us/dashboard/dashboard.log` 里每分钟有日志，`/mnt/us/dashboard/cache/dash.png` 存在。

至此安装完成。Kindle 可以拔掉数据线、插上充电线，放桌上常亮运行。

## 三、日常使用

- **插电常亮**：启动脚本已禁止自动休眠，屏幕会一直显示。墨水屏静态显示本身不耗电，但 WiFi 和每分钟刷新耗电，建议一直插着充电器。
- **停止仪表盘**：KUAL → AI Dashboard → **停止仪表盘**。脚本会被杀掉、休眠设置还原（`preventScreenSaver 0`）、清屏提示返回系统。
- **重启 Kindle 后不会自动启动**，需要重新打开 KUAL 点一次"启动仪表盘"。
- **偶发拉取失败不用管**：某次拉取失败时，屏幕显示缓存的上一张图，并在顶部叠加一条告警横幅；下次拉取成功横幅自动消失。只有横幅**长时间不消失**才需要排查（见第四节）。
- **看日志**：USB 连电脑打开 `/mnt/us/dashboard/dashboard.log`，每分钟的运行记录都在里面，排查问题先看它。

## 四、常见错误对照表

| 现象 | 可能原因 | 排查与解决 |
|---|---|---|
| KUAL 里看不到"AI Dashboard"入口 | `ai-dashboard` 文件夹拷错了层级，或文件没拷全 | 检查 `/mnt/us/extensions/ai-dashboard/` 下必须有 `config.xml`、`menu.json`、`bin/start.sh`、`bin/stop.sh` 四个文件（**缺 `config.xml` 时 KUAL 完全看不到这个扩展**）。常见错误：拷成了 `extensions/ai-dashboard/ai-dashboard/`（多套一层），或把文件散丢在 `extensions/` 根下。改对后退出 KUAL 重新进 |
| 点了"启动仪表盘"没反应，屏幕不变 | 脚本丢了执行权限（ZIP 解压再拷贝容易出现） | 用 USBNetwork 的 SSH 连上 Kindle（装法见 [1-jailbreak.md](1-jailbreak.md)），执行 `chmod +x /mnt/us/dashboard/dashboard.sh /mnt/us/extensions/ai-dashboard/bin/start.sh /mnt/us/extensions/ai-dashboard/bin/stop.sh`，再回 KUAL 启动。若 chmod 不生效（`/mnt/us` 是 FAT 文件系统，权限位可能存不住），在 SSH 里手动执行 `sh /mnt/us/dashboard/dashboard.sh`，看实际报错再对症处理 |
| 屏幕有画面，但顶部告警横幅一直不消失 | 持续拉取失败：WiFi 断了 / `IMAGE_URL` 填错 / 服务器没跑 | ① 看 Kindle 右上角 WiFi 图标，断了就重连；② 电脑浏览器访问 `IMAGE_URL`，打不开就是地址或服务器问题：逐字符核对 `config.env` 里的域名、token 与服务器 nginx 配置是否一致（含结尾的 `dash.png`）；③ 服务器上 `pm2 logs` 看渲染程序是否还活着 |
| 横幅偶尔出现又自己消失 | 网络偶发超时（脚本里 `wget` 超时设为 20 秒） | 偶发可以不管。频繁出现则查：服务器安全组/防火墙是否放行 80 端口、家里路由器是否开了 AP 隔离、宽带运营商到服务器的链路是否稳定 |
| 画面有残影，字迹越看越灰 | 局部刷新累积的正常现象 | 把 `config.env` 里的 `FULL_REFRESH_EVERY` 调小（默认 60，可改成 30），即每 30 次刷新做一次全刷清残影。改完要在 KUAL 里停止再启动才生效 |
| 屏幕上残留系统状态栏或菜单的影子 | 系统 UI 曾在仪表盘运行时弹出过 | 点一下屏幕或等下一次刷新一般会盖掉。进阶做法：SSH 里 `stop lab126_gui` 彻底停掉系统界面——但系统 UI 会完全消失，想恢复要 `start lab126_gui` 或重启，新手不建议碰 |
| 改了 `config.env` 但没生效 | 换行符被存成 CRLF；没安全弹出就拔线导致没写进盘；改的是电脑上那份而不是 Kindle 里那份 | 确认改的是 **Kindle 磁盘里**的 `/mnt/us/dashboard/config.env`；用 VS Code/Notepad++ 存成 LF；保存后安全弹出再拔线；改完在 KUAL 里停止再启动，脚本才会重新读配置 |
| 仪表盘上的时钟时间不对 | Kindle 系统时间不准 | 让 Kindle 连着 WiFi 放一会儿，系统会自动联网对时；也可在 Kindle 设置里核对日期时间。若 Kindle 系统时间正常而图上时间仍不对，去服务器检查 `config.env` 里的 `TIMEZONE`（一般应为 `Asia/Shanghai`） |
| `dashboard.log` 里报 fbink 相关错误 | fbink 没装，或没装到常见路径 | 按 [1-jailbreak.md](1-jailbreak.md) 重装 fbink。脚本会自动探测 `/mnt/us/fbink/bin/fbink`、`/mnt/us/extensions/fbink/bin/fbink` 和 PATH 里的 `fbink`，装到这三处之一即可 |

## 五、以后更新文件

仓库以后更新了，升级方法很简单：

1. 下载新版仓库，USB 连上 Kindle，把**有变化的文件**按第二节的布局重新拷贝、覆盖到原位置。
2. 如果覆盖了 `dashboard.sh` 或 KUAL 扩展里的脚本，在 KUAL 里先"停止仪表盘"再"启动仪表盘"，让新文件生效。
3. Kindle 上那份 `config.env` 是你自己填好的，除非教程明确说明配置格式有变化，否则**不要**用仓库里的占位符版本覆盖它。

## 完成

到这里，三篇教程全部完成：越狱（一）、服务器（二）、Kindle 端（三）。你的 Kindle 现在应该已经作为 AI 用量仪表盘，常亮运行在桌上了。

项目整体介绍、架构说明和效果图，见仓库根目录的 [README.md](../README.md)。
