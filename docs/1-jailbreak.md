# Kindle 越狱教程（LanguageBreak）

> 本教程是"Kindle AI 用量仪表盘"安装链的第 1 篇，以 **Kindle Paperwhite 3（第 7 代）**、固件 **5.16.2.1.1** 为例编写。LanguageBreak 本身支持所有固件 **≤ 5.16.2.1.1** 的 Kindle，步骤基本一致，界面文字可能略有差异。
>
> 后续两篇：[docs/2-server-setup.md](2-server-setup.md)（服务器端安装）、[docs/3-kindle-setup.md](3-kindle-setup.md)（Kindle 端软件安装）。

整个过程约需 30～60 分钟，只需要一台电脑（Windows/macOS 均可）和一根 USB 数据线，不需要任何命令行经验。请**先完整读一遍再动手**，每步末尾都有验证方法，确认无误再进入下一步。

---

## 一、风险清单与备份

动手之前，请务必了解以下事实：

- ⚠ **越狱过程会恢复出厂设置，清空 Kindle 里的所有本地内容**：书籍、个人文档、阅读进度、标注笔记全部删除。LanguageBreak 官方 README 原话是 "This method **will DELETE** all content on your device"。
- ⚠ 越狱（以及任何非官方修改）可能失去亚马逊保修，极端情况下有变砖风险。请自行权衡，量力而为。
- ⚠ 越狱后**升级固件**（超过 5.16.2.1.1）会修复漏洞、导致越狱失效；**再次恢复出厂设置**同样会清除越狱环境。这也是第六节要屏蔽自动更新的原因。

### 备份方法

1. 用 USB 数据线把 Kindle 连到电脑，打开出现的"Kindle"盘符。
2. 把 **`documents` 文件夹整个拷贝到电脑**上保存。这里面是你所有的本地书籍、个人文档，以及阅读进度和标注（`.sdr` 同名文件夹）。
3. 如果你用过 Send to Kindle 或个人文档邮箱，相关内容也在 `documents` 里，一并已备份。

关于云端内容，不用备份：

- **在亚马逊商店购买的书**：购买记录在云端，事后可重新下载，不受清空影响。
- **微信读书等第三方内容**：与本教程无关，不受影响。

---

## 二、前置检查

逐项确认，全部满足再开始：

1. **固件版本 ≤ 5.16.2.1.1**
   - 查看路径：【菜单（右上角三个点）→ 设置 → 设备选项 → 设备信息】，看"固件版本"一行。
   - 版本号高于 5.16.2.1.1：漏洞已修复，**LanguageBreak 不可用**，请停止（新固件的越狱方法参见 [kindlemodding.org](https://kindlemodding.org)，不在本教程范围）。
   - 版本号低于 5.16.2.1.1：可以用，但官方建议先升到 5.16.2.1.1 以提高成功率（该漏洞在 5.16.2 附近表现最好）。PW3 的 5.16.2.1.1 固件直链：
     `https://s3.amazonaws.com/firmwaredownloads/update_kindle_all_new_paperwhite_5.16.2.1.1.bin`
     下载后拷到 Kindle 根目录，然后【设置 → 右上角菜单 → 更新您的 Kindle】即可升级。
2. **设备没有密码锁**
   - 有密码必须先去【设置 → 设备选项 → 设备密码】关闭，否则演示模式流程会出问题。
   - 如果忘了密码：在密码输入框输入 `111222777` 可以重置设备（**会清空所有数据**，请确认已完成第一节的备份）。
3. **电量充足**：建议 50% 以上，避免过程中断电。
4. **一根能传数据的 USB 线**：连接电脑后要能看到 Kindle 盘符。只显示充电、看不到盘符的就是纯充电线，换一根。
5. **打开飞行模式**：点屏幕顶部区域唤出快捷设置，点亮飞行模式图标。整个越狱过程不需要联网，且要防止后台自动下载固件。
6. **清理根目录残留**：连电脑检查 Kindle 根目录，删除所有 `.bin` 文件和名为 `update.bin.tmp.partial` 的文件/文件夹——它们可能是待安装的 OTA 更新，留着会干扰越狱。

---

## 三、LanguageBreak 越狱

原理一句话：利用 Kindle 演示模式在选择"简体中文"时触发的一个漏洞，把越狱文件注入系统。步骤看着多，照着做即可。界面文字不同批次设备**可能略有差异**，括号里附英文原文供对照。

### 3.1 下载并解压越狱包

1. 打开 LanguageBreak 的 GitHub 发布页：<https://github.com/notmarek/LanguageBreak/releases>
2. 下载最新版的 `LanguageBreak-XX.XX.XX.tar.gz`（写本教程时最新为 1.0.2.1，文件名 `LanguageBreak-16.11.23.tar.gz`，日期后缀随版本变化属正常）。
3. 解压：
   - **Windows**：建议安装免费的 [7-Zip](https://www.7-zip.org/) 解压（新版 Windows 11 自带的解压也能处理 `.tar.gz`，但 7-Zip 更稳）。注意要**解压两次**：先解出 `.tar`，再解出文件夹。
   - **macOS**：直接双击即可解压，或用自带解压工具。
4. 解压后应得到如下结构（先核对一遍，后面所有文件都从这里找）：

   ```
   ├── LanguageBreak/               # 越狱文件本体（文件夹）
   ├── Update_hotfix_languagebreak-zh-Hans-CN.bin   # 热修复补丁（按语言各一个，共十几个）
   ├── Update_hotfix_languagebreak-en-US.bin
   ├── ...（其他语言的 hotfix）
   ├── README.MD
   └── DEVICES.txt
   ```

### 3.2 进入演示模式

1. 在 Kindle 主页**顶部搜索框**输入 `;enter_demo`（注意开头有个分号），按回车。
2. 重启设备：【右上角菜单 → 重新启动】，或长按电源键在弹出的对话框里选重启。
3. 重启后进入演示模式初始化：跳过 WiFi 选择对话框（随便选一个网络再返回即可），"注册演示样机"表单随便填，点【继续】。
4. 在"正在获取可选的演示类型"界面点【跳过（Skip）】，然后选【Standard】，点【完成（Done）】。
5. 设备会白屏/转圈几分钟进行自动配置，属于正常现象，不要动它。
6. 配置完成后会停在"配置设备（CONFIGURE DEVICE）"或提示"展示机无内容或未连接网络"的界面，需要用**秘密手势**跳过：
   - 双指在屏幕（右下角区域成功率较高）轻点一下，紧接着向左滑动一段距离。
   - 一次不成功很正常，多试几次；也可以试试"双指按住不放，直接向左滑"的变体。官方指南在这里附了示意图，手法因人而异。
7. 手势成功后进入图书馆界面。在搜索框输入 `;demo` 按回车，进入"演示菜单"。

> 如果进不了演示模式或手势始终过不去，先看第七节的错误对照表。

### 3.3 载入越狱文件并完成越狱

1. 在演示菜单点【导入内容（Sideload Content）】。
2. 用 USB 线把 Kindle 连到电脑。
3. 把解压出的 **`LanguageBreak` 文件夹里面的全部内容**（`documents`、`jb`、`patchedUks.sqsh`、`DONT_CHECK_BATTERY`、`.demo` 等）拷到 Kindle **根目录**，提示覆盖就覆盖。
   - ⚠ 是拷贝"文件夹**里面**的内容"，不是把 `LanguageBreak` 文件夹本身拷进去。这是最常见的失败原因。
   - 拷完后根目录应该直接能看到 `jb`、`patchedUks.sqsh` 这些文件，和原有的 `documents` 文件夹并列。
4. 在电脑上**弹出（安全删除）Kindle 盘符**，然后拔掉 USB 线。
5. 回到演示菜单（如果界面退出了，再输一次 `;demo`），依次点【销售设备（Resell Device）】→【销售 / Yes】确认。
6. 稍等片刻，屏幕出现"请按电源键（Press the Power Button）"的按钮示意图——**立刻**把 USB 线插回电脑（这一步有时间窗口，手要快）。
7. **再次**把 `LanguageBreak` 文件夹里面的全部内容拷到 Kindle 根目录，覆盖已有文件。
8. 拷贝完成后在电脑上弹出盘符，然后**按住 Kindle 电源键不放**，直到设备重启。
9. 重启后出现语言选择界面：找到【简体中文】（位置大致在日语下方、`Pseudot` 上方，分栏布局可能略有差异），点它，再点屏幕中部出现的中文按钮（下一步）。
10. 设备再次重启，屏幕角落（右上角）会滚动出现一些日志文字——**这就是越狱成功的标志**。

### 3.4 安装热修复补丁（hotfix）

hotfix 的作用是让越狱在重启后依然生效，必装。根据上一步后设备的状态二选一：

**情况 A：重启后仍在演示模式**

1. 搜索框输入 `;uzb` 按回车，开启演示模式下的 USB 传输。
2. 连电脑，把与你 Kindle 界面语言对应的 hotfix 拷到根目录。界面是简体中文就选 `Update_hotfix_languagebreak-zh-Hans-CN.bin`（美式英语是 `-en-US`，以此类推）。
3. 弹出盘符、拔线。搜索框输入 `;dsts` 按回车进入设置页，找到【更新您的 Kindle（Update your Kindle）】点它并确认。
4. 设备自动重启并退出演示模式，越狱完成。

**情况 B：重启后已退出演示模式（进了正常系统）**

1. 直接连电脑，把对应语言的 hotfix 拷到根目录。
2. 弹出盘符、拔线。【设置 → 右上角菜单 → 更新您的 Kindle】，确认后等待重启。

> 如果安装时提示 "Update Error" 之类的错误，把 hotfix 重新拷一遍、再装一次即可（官方 README 说明这是已知的小毛病）。

### 3.5 验证越狱成功 & 收尾

**验证方法**（两个都过才算稳）：

1. 连电脑看 Kindle 根目录，应该多了一个 **`mkk` 文件夹**（越狱密钥落地的标志）。
2. 在 Kindle 搜索框输入 `;log` 按回车，屏幕角落会出现一段日志文字（说明越狱的命令钩子已生效）。

**收尾清理**：越狱后根目录会留下几个文件，其中 `languagebreak_log`、`LanguageBreakRan`、`patchedUks.sqsh` 可以删掉；`libkh`、`mkk`、`rp` 三个文件夹**必须保留**，别动。

**如果 WiFi、设置等功能被锁（Managed 模式）**：少数设备越狱后会进入"受管理"状态，设置项变灰、提示联系系统管理员。处理办法：

- 设备**未注册**亚马逊账号：搜索框输 `;demo` 回车，弹出两个按钮的对话框时点**右边**那个，设备重启即恢复。
- 设备**已注册**账号：输 `;enter_demo` 回车并重启 → 用手势进主界面 → 输 `;demo` 回车 → 选【Resell device】确认 → 重启后恢复正常，必要时重装一遍 hotfix。

---

## 四、安装 KUAL + MRPI

KUAL（Kindle Unified Application Launcher）是第三方插件的启动菜单；MRPI（MobileRead Package Installer）是插件安装器。两者配合是 Kindle 插件生态的标准底座，本项目的仪表盘菜单入口也挂在 KUAL 里。

先确认 Kindle 剩余空间大于 **220 MB**（连电脑右键 Kindle 盘符看"属性"即可；刚恢复出厂的 PW3 一般没问题）。

### 4.1 安装 MRPI

1. 下载 MRPI（kindlemodding.org 官方托管，Marek 维护版，PW3 等现代设备通用）：
   <https://kindlemodding.org/jailbreaking/post-jailbreak/installing-kual-mrpi/kual-mrinstaller-khf.zip>
2. 解压，得到 `extensions` 和 `mrpackages` 两个文件夹。
3. 连电脑，把这两个文件夹拷到 Kindle **根目录**。如果根目录已有 `extensions` 文件夹，改成合并：把解压出的 `extensions` 里的内容拷进去，不要整个覆盖删除。
4. 拷完后目录结构应为：
   - `extensions/MRInstaller/`（里面有一堆文件）
   - `mrpackages/`（空文件夹，稍后放安装包用）

### 4.2 用 MRPI 安装 KUAL

1. 下载 KUAL。打开 NiLuJe 的插件合集帖（MobileRead 论坛）：<https://www.mobileread.com/forums/showthread.php?t=225030>，在一楼附件列表里找 **KUAL**。如果下载附件提示要登录，注册一个免费账号即可。
   - PW3（固件 5.9 以上）按 kindlemodding 官方指南选 **coplate 版**：压缩包文件名里带一串 commit 哈希，形如 `KUAL-f190a38-20240104.tar.xz`，解压出的安装包形如 `Update_KUALBooklet_f190a38_install.bin`。
   - 书伴的中文教程则把 KPW3 归到普通版（文件名带版本号，形如 `Update_KUALBooklet_v2.7.35_install.bin`）。两者装法完全一样，实际都有成功案例；**建议优先 coplate 版，装完打不开再换普通版重装**。
2. 解压（`.tar.xz` 在 Windows 上请用 7-Zip、macOS 用 Keka 或 `tar` 命令——**别用 WinZip**，它解压 `.xz` 会悄悄损坏文件，是已知的坑）。
3. 把解压出的 `Update_KUALBooklet_xxxxx_install.bin` 拷进 Kindle 根目录下的 **`mrpackages`** 文件夹。
   - 文件名里不要带浏览器自动加的 `(1)` 之类后缀，有就先改名去掉。
4. 弹出盘符、拔线。在 Kindle 搜索框**手动输入** `;log mrpi` 按回车。
   - ⚠ 不要用点击搜索历史记录的方式复用旧命令，可能触发的是历史里的报错记录，一定要逐字手输。
5. 屏幕下半部分出现 `Hush, little baby...` 字样，说明 MRPI 开始干活了。耐心等待安装，结束后设备会自动重启。

### 4.3 验证

1. 重启后回到主页/图书馆，应该出现一个名为 **KUAL** 的图标（长得像一本个人文档）。
2. 点开它，能看到一个菜单界面，里面有若干条目。
3. 菜单里找到【Helper → Install MR Packages】——这就是刚装好的 MRPI，说明两者都就位了。

> 排错：安装失败可连电脑查看日志 `extensions/MRInstaller/log/mrinstaller.log`，常见原因见第七节对照表。

**替代方案（可选了解）**：kindlemodding.org 目前推荐用 [PEKI](https://github.com/KindleTweaks/PEKI) 装 KUAL——把 PEKI.zip 里的 `KUAL.sh` 和 `KUAL.jar` 拷到 `documents` 文件夹，在图书馆点开即可，不需要 `;log mrpi`。本教程主路径仍采用 MRPI 方案（与本项目后续文档的假设一致），两条路殊途同归，最终得到的 KUAL 是同一个。

---

## 五、安装 fbink（刷屏工具）

fbink（FBInk）是往墨水屏直接写图/写字的命令行工具，本项目 Kindle 端的刷屏脚本依赖它。

1. 下载 FBInk 的 Kindle 二进制包：打开 MobileRead 的 FBInk 专帖 <https://www.mobileread.com/forums/showthread.php?t=299620>，一楼附件里有各版本压缩包，取最新即可（当前为 v1.25.0）。附件如需登录，注册免费账号。
   - 注意：FBInk 的 [GitHub release](https://github.com/NiLuJe/FBInk/releases) 页只有源码包，没有 Kindle 二进制，别下错。
2. 解压后里面有按设备分的文件夹（`K2`/`K3`/`K4`/`K5` 等）。**PW3 选 `K5`**。
3. 连电脑，在 Kindle 根目录新建一个 `fbink` 文件夹，把压缩包里 `K5` 文件夹的内容拷进去。拷完后关键文件应位于：
   - `/mnt/us/fbink/bin/fbink`（即"Kindle 根目录 → `fbink` → `bin` → `fbink`"）
   - 压缩包内部结构随版本可能略有差异，找到名为 `fbink` 的那个文件、按上述位置放好即可。**本项目的脚本会自动探测多个常见路径，位置略有出入没关系**。
4. 验证：重新连一次电脑，确认 `fbink/bin/fbink` 文件存在（几百 KB 的可执行文件）即可。不需要现在真的刷一张图，联调验证在 [docs/3-kindle-setup.md](3-kindle-setup.md) 里做。

---

## 六、屏蔽 OTA 自动更新（必做）

Kindle 连上 WiFi 就会自动下载并安装新固件，而**任何超过 5.16.2.1.1 的固件都会让越狱失效**。本项目又要求 Kindle 常连 WiFi，所以必须先堵死自动更新。PW3 固件为 5.16.x，用官方的 renameotabin 方案（原理：把系统更新程序改名，让它无法运行）。

1. 下载 renameotabin（kindlemodding.org 官方托管）：
   <https://kindlemodding.org/jailbreaking/post-jailbreak/renameotabin.zip>
2. 解压，得到 `renameotabin` 文件夹（如果解压出来是两层嵌套，取**最里层**那个，里面应有 `bin`、`menu.json`、`config.xml`）。
3. 连电脑，把 `renameotabin` 文件夹拷到 Kindle 根目录的 **`extensions`** 里，即 `extensions/renameotabin/`。
4. 顺手检查根目录，删掉任何 `.bin` 文件和 `update.bin.tmp.partial`，防止已下载的更新在下次重启时自动安装。
5. 弹出盘符、拔线。打开 **KUAL**，依次点【Rename OTA binaries → Rename】。设备会自动重启。
6. 重启后即屏蔽完成。此时可以**关闭飞行模式、打开 WiFi**了——设备能正常上网，但不会再下载安装系统更新（后续仪表盘正需要网络）。

> ⚠ **从此以后：永不升级固件、永不恢复出厂设置。**
> 升级固件会修复漏洞让越狱失效；恢复出厂会清空整个越狱环境和插件，本项目的一切配置都会丢失。如果将来确实需要手动刷固件或恢复出厂，先打开 KUAL 点【Rename OTA binaries → Restore】把更新程序改回去，操作完再重新执行一遍上面的屏蔽步骤。

---

## 七、常见错误对照表

| 现象 | 可能原因 | 解决办法 |
|---|---|---|
| 第 3.3 步选简体中文后没有日志，重启后也没有 `mkk` 文件夹 | 固件高于 5.16.2.1.1，漏洞已修复，越狱根本没生效 | 核对【设置 → 设备选项 → 设备信息】里的版本号。高于该版本请放弃 LanguageBreak，去 kindlemodding.org 查新固件对应的方法 |
| 演示模式进不去 / 流程卡住 | 设备有密码锁 | 回正常系统去【设置 → 设备选项 → 设备密码】关闭；忘记密码用 `111222777` 重置（会清数据） |
| `;enter_demo` 输了没反应 | 拼写错（漏了分号）、点成了搜索建议、或固件不兼容 | 逐字手输、注意开头的 `;`；仍不行可用备选进法：根目录放一个名为 `DONT_CHECK_BATTERY` 的空文件后直接输 `;demo` 回车 |
| 秘密手势怎么都过不去 | 手法不对 | 三种常见手法轮换试：①双指轻点右下角紧接着单指左滑；②双指按住右下角，抬一根手指另一根左滑；③双指按住直接左滑。每次等界面稳定再试 |
| 弹出 "Collecting Debug Info" | 演示模式里的操作顺序错了，在错误的状态重试 | 需要重置演示模式：输 `;uzb` 回车 → 连电脑在根目录放一个名为 `DO_FACTORY_RESTORE` 的空文件（无扩展名）→ 重启，然后从头开始 |
| 【更新您的 Kindle】按钮是灰的 | 根目录没有有效的 `.bin`；文件名被浏览器加了 `(1)` 后缀；或处于 Managed 模式 | 检查 hotfix 文件名和位置；Managed 模式按 3.5 节的办法退出后再装 |
| 越狱后没有 `mkk` 文件夹 / `;log` 无输出 | 越狱没成功：常见是拷成了 `LanguageBreak` 文件夹本身（应多套了一层），或第 3.3-6 步插线太慢错过时间窗口 | 恢复出厂后重做 3.2～3.3，注意"拷内容不拷文件夹"，且按钮示意图一出现就立刻插线 |
| `;log mrpi` 没反应 | `extensions`/`mrpackages` 位置不对；`.tar.xz` 被 WinZip 解压损坏；点了搜索历史记录 | 核对目录结构；换 7-Zip（Windows）/Keka（macOS）重新解压拷贝；逐字手输命令；重启 Kindle 再试 |
| KUAL 图标出现但点开白屏/闪退 | KUAL 变体与设备不搭 | 换另一个变体（coplate ↔ 普通版）的 `_install.bin` 放进 `mrpackages`，重新 `;log mrpi` |
| 装完插件 WiFi、设置被锁 | 进了 Managed 模式 | 见 3.5 节"Managed 模式"处理办法 |
| KUAL 里看不到 Rename OTA binaries | `renameotabin` 文件夹放错位置或嵌套多了一层 | 确认路径是 `extensions/renameotabin/menu.json` 这个层级，重启 Kindle 后再看 |

---

## 参考链接

本教程步骤核实自以下来源（按使用顺序）：

- [notmarek/LanguageBreak（GitHub）](https://github.com/notmarek/LanguageBreak) — 越狱官方 README、release 包结构与 hotfix 说明
- [KindleModding 官方 Wiki：LanguageBreak 指南](https://kindlemodding.org/jailbreaking/Legacy/LanguageBreak.html) — 演示模式流程、手势、备选进法
- [KindleModding 官方 Wiki：安装 KUAL 与 MRPI](https://kindlemodding.org/jailbreaking/post-jailbreak/installing-kual-mrpi/) — MRPI 下载与目录结构、排错建议
- [KindleModding 官方 Wiki：屏蔽 OTA 更新](https://kindlemodding.org/jailbreaking/post-jailbreak/disable-ota.html) — renameotabin 方案全流程
- [KindleModding Wiki（旧站存档）：KUAL/MRPI 安装](https://kindlemodding.gitbook.io/kindlemodding/post-jailbreak/installing-kual-mrpi) — KUAL coplate/普通版的区分
- [MobileRead：NiLuJe 插件合集帖](https://www.mobileread.com/forums/showthread.php?t=225030) — KUAL、MRPI 原版下载
- [MobileRead：FBInk 专帖](https://www.mobileread.com/forums/showthread.php?t=299620) — FBInk Kindle 二进制下载
- [MobileRead：LanguageBreak 原帖](https://www.mobileread.com/forums/showthread.php?t=356872) — 疑难问题讨论
- [KindleTweaks/PEKI（GitHub）](https://github.com/KindleTweaks/PEKI) — KUAL 的替代安装器
- [书伴：Kindle 通用越狱教程（≤5.16.2.1.1）](https://bookfere.com/post/1075.html) — 中文界面菜单名对照
- [书伴：Kindle 越狱插件资源下载及详细安装步骤](https://bookfere.com/post/311.html) — MRPI/KUAL 中文安装流程

---

## 完成后下一步

越狱环境到此就绪（已越狱 + KUAL/MRPI + fbink + 已屏蔽 OTA）。接下来：

1. **搭建服务器端**（渲染仪表盘图片）：照 [docs/2-server-setup.md](2-server-setup.md) 操作，最后在浏览器里能看到 `dash.png` 就算完成。
2. **安装 Kindle 端软件**（拷脚本、KUAL 菜单启动）：照 [docs/3-kindle-setup.md](3-kindle-setup.md) 操作，与本篇装好的 KUAL、fbink 对接。
