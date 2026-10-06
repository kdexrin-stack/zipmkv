# zipmkv - 现代媒体与多功能离线处理工具箱

[![Release](https://img.shields.io/github/v/release/kdexrin-stack/zipmkv?color=2563eb&style=flat-square)](https://github.com/kdexrin-stack/zipmkv/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-slate.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg?style=flat-square)](https://github.com/kdexrin-stack/zipmkv)

- **开源仓库**: [https://github.com/kdexrin-stack/zipmkv](https://github.com/kdexrin-stack/zipmkv)
- **最新发布下载**: [https://github.com/kdexrin-stack/zipmkv/releases](https://github.com/kdexrin-stack/zipmkv/releases)

`zipmkv` 是一个专为 Windows 平台打造的高性能、现代 UI、完全离线的多媒体与文档批量处理工具箱。涵盖漫画/电子书归档、视频与字幕混流封装、音轨极速无损提取、B 站 XML 弹幕转 ASS 滚动字幕、文件智能批量重命名与繁简中文互转等核心场景。

当前桌面版本为 `1.3.1`。项目按“界面层、纯业务层、内置工具层”组织，文件夹输入会在后台递归扫描，界面线程只负责交互和日志显示；所有默认输出都写入新目录，源文件保持不变。

---

## ✨ 核心特性

### 1. 📚 文档合并与整理 (`image_archive_pdf`)
- **多素材自由混编**：支持单/多张图片（JPG/PNG/WebP/BMP 等）、压缩包（ZIP/RAR/7z/CBZ/CBR）、EPUB 电子书、PDF 与 TXT 文本。
- **无损合成输出**：图片按原像素高清写入，PDF 页面原生追加，文本排版渲染，一键合并为一个完整的 PDF 或 EPUB 电子书，亦支持按项逐一导出。

### 2. 🎬 字幕样式与音视频封装 (`subtitles`)
- **字幕样式批量修改**：支持 ASS/SSA 字体、字号、主颜色、描边、阴影与边距自定义调整，亦可导出为标准 SRT/VTT。
- **示例样式对齐**：选取标杆字幕或参考视频，自动提取其精美排版并套用到目标字幕。
- **MKV 混流与轨道管理**：内封多字幕轨提取、替换视频原字幕轨、追加新字幕轨生成独立 MKV。
- **双语字幕合成**：自动提取视频内全部字幕轨，也支持多个外挂字幕按时间轴配对；双语参考或单语参考均可用于样式，第二字幕自动缩小并置于下方，原有双行字幕可合并为单行，并可封装为新 MKV。
- **语言识别与单轨双语**：新增独立语言工具模块。只有一条字幕时自动识别中文简体/繁体，并使用内置 OpenCC 离线生成另一种中文；日文、英文、韩文等会识别并在日志中说明，不会把原文重复冒充翻译。
- **音轨无损提取**：一键秒级从 MP4/MKV/FLV 等视频中提取音频轨为 MP3、AAC、FLAC、WAV 或保留原流编码，无须重新编码。

### 3. 💬 XML 弹幕处理与转字幕 (`xml_danmaku`)
- **XML 弹幕转 ASS 滚动字幕**：将 B 站 XML 弹幕批量转换为高质量 ASS/SRT 字幕，内置智能分轨防碰撞算法、1080P/4K 高清分辨率自适应与颜色解析，可直接在 PotPlayer/VLC 加载或封装进 MKV。
- **弹幕清洗与平移**：一键过滤负时间戳无效弹幕、清理内嵌 ASS 样式标签，支持精准时间前后平移微调。

### 4. 🏷️ 批量文件智能重命名 (`rename_files`)
- **参考对齐模式**：B 组目标文件智能套用 A 组参考源文件名，自动按自然序号排序配对。
- **手动规则与模板**：支持前后缀设定、序号格式（`1`、`01`、`001`）、起始编号，以及自定义格式模板（如 `剧集_ep{num:02d}_1080P`）。
- **安全副本机制**：不覆盖源文件，在输出目录安全生成重命名副本。
- **冲突稳定处理**：原地改名采用临时文件分阶段执行，支持 A→B、B→A 交换，重复目标名和已有文件会记录为失败并保留源文件。

### 5. 🈳 繁简文字批量互转 (`zh_convert`)
- **多格式全支持**：支持纯文本（`.txt`）、字幕（`.srt`、`.ass`、`.vtt`）、弹幕（`.xml`）、Markdown（`.md`）与 HTML。
- **精准转换引擎**：集成 OpenCC 词库，支持简体转繁体（通用/台湾/香港）、繁体转简体及地域词汇转换，提供左右分栏实时对比。

---

## 🎨 现代 UI 与设计规范

- **蓝白工作台**：以高明度蓝白为主色，侧栏、工具区、日志和状态栏分层清晰，避免黑色大面积压迫感。
- **高 DPI 适配**：自适应 Windows 系统缩放比例（100%、125%、150%、200%），字体清晰平滑。
- **便捷交互**：功能搜索、Lucide 图标按钮、悬停提示、列表框 `Ctrl+A`/右键/`Delete` 操作，以及实时任务状态与耗时统计。
- **可视化反馈**：字幕结果区显示实际输出文件的预览图、事件数量、当前字幕文字和可点击时间轴；日志区固定在结果区，不会被输入表单挤出窗口。

界面交互参考了 [Sun Valley ttk theme](https://github.com/rdbende/Sun-Valley-ttk-theme) 的轻量控件层次和 [Subtitle Edit 主窗口](https://github.com/SubtitleEdit/subtitleedit/blob/main/docs/features/main-window.md) 的日志/预览分区思路。图标使用打包进程序的 [Lucide 静态资源](https://lucide.dev/guide/static)，不会在运行时联网。

---

## 🛠️ 内置离线工具链

本程序坚持**零网络依赖、开箱即用**原则，已内置完整工具链：

- **7-Zip 命令行工具**：内置于程序目录，支持 `.zip`、`.rar`、`.7z`、`.cbz`、`.cbr`、`.cb7`、`.epub`、`.tar`、`.gz` 等解压。
- **FFmpeg 媒体引擎**：构建时以高压缩 LZMA2 归档内置于单文件 EXE，运行时按需释放到 `tools/ffmpeg`，无需用户另行配置环境变量。

常见 JPEG、PNG、TIFF 图片转 PDF 时优先使用 `img2pdf` 直接嵌入图像数据，避免不必要的二次压缩；GIF、WebP、BMP 等格式使用兼容转换路径。

## 🧪 稳定性与性能设计

- 选择文件夹只登记输入，不在界面线程递归遍历；点击执行后才由后台线程扫描。
- 后台任务开始前会冻结输入列表和参数，避免处理过程中修改界面导致结果漂移。
- 日志通过队列回到主线程，并限制日志行数，长任务不会持续增长内存。
- 内置 7-Zip 解压 ZIP/EPUB 时校验目标路径，拒绝压缩包中的目录穿越路径。
- 所有输出名经过安全清理和冲突改名，重复运行不会覆盖已有结果。
- 双语字幕按字幕时间重叠和最近开始时间匹配，保留未匹配事件可选；输出采用两个独立 ASS 样式，避免不同字号的双语文本嵌在同一事件后出现渲染异常。
- 单轨字幕先进行语言识别；`auto_chinese` 只对简体/繁体执行可靠的离线互转，其他语言保持单语输出并明确记录原因，后续可在 `language_tools` 中接入经过授权的离线翻译模型。

---

## 🚀 运行与使用

### 1. 直接运行单文件绿色版
从 Releases 下载 `zipmkv.exe`，双击即可运行。程序运行时会在所在目录自动维护：
```text
config/   # 本地偏好设置
logs/     # 运行日志
output/   # 默认处理输出目录
temp/     # 临时处理中转目录
```

### 2. 源码运行
环境需求：Python 3.10+ (推荐 3.11 或 3.13)

```powershell
# 1. 克隆仓库
git clone https://github.com/kdexrin-stack/zipmkv.git
cd zipmkv

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动主程序
python .\app.py
```

### 3. 各模块独立启动调试
每个功能模块均可脱离主窗口独立启动：
```powershell
python .\image_archive_pdf\main.py
python .\rename_files\main.py
python .\subtitles\main.py
python .\xml_danmaku\main.py
python .\zh_convert\main.py
python .\language_tools\main.py
```

---

## 🧪 自动化测试

项目内置全功能烟测套件，可一键验证所有核心算法与 GUI 页面逻辑：

```powershell
python .\smoke_test.py
```

---

## 📦 编译与打包

执行项目根目录下的自动化打包脚本：

```powershell
python .\build_exe.py
```

打包脚本会自动执行：
1. 自动创建并管理项目隔离虚拟环境 `.build_venv`；
2. 安装与更新全部编译依赖；
3. 压缩并固化内置 7-Zip 与 FFmpeg 工具链；
4. 执行全链路烟测套件；
5. 调用 PyInstaller 生成高集成度单文件 `dist/zipmkv.exe`；
6. 在隔离空目录自动启动生成的 EXE 进行启动探测与各模块健康检查；
7. 安装回同名 `zipmkv.exe` 并刷新已有桌面快捷方式；若旧程序正在运行，会等待它退出后再替换，不保留版本化最终入口。

---

## 🧩 扩展新模块

项目采用极简的插件化架构，如需新增功能模块：

```text
new_feature/
├─ __init__.py
├─ core.py     # 纯业务与算法逻辑
├─ gui.py      # 继承 ToolFrame 的 FeatureFrame 界面类
└─ main.py     # 独立入口
```

在 `features.py` 的 `FEATURES` 列表中注册该模块规格，即可自动挂载至主程序侧边栏与导航系统。

---

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源发布。
