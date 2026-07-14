# zipmkv

公开源码：https://github.com/kdexrin-stack/zipmkv

发布包：https://github.com/kdexrin-stack/zipmkv/releases

`zipmkv` 是一个可扩展的桌面工具箱，面向压缩包、图片、PDF、弹幕和字幕处理。项目原则是：不破坏源文件，默认在源路径附近生成新文件夹保存结果，也可以手动选择输出目录。

## 功能

- 图片/压缩包/PDF/EPUB/TXT 整理：支持单/多图片、压缩包、EPUB、PDF、TXT 和文件夹扫描，可合并为一个大的 PDF 或 EPUB，也可逐项输出
- 批量文件重命名副本生成：支持参考文件名配对，也支持手动规则生成 `1`、`01`、`ep1`、`ep01`、`视频ep01视频` 等名称
- XML 弹幕批量处理
- 字幕样式修改，支持单独字幕文件和视频内封字幕；可把修改后的字幕封装进 MKV，也可单独给视频增加/删除字幕轨
- 简体与繁体文件批量互转

## 运行

统一入口：

```powershell
python .\app.py
```

单文件 EXE：

```text
dist\zipmkv.exe
```

这个 EXE 可以复制到其他位置运行。运行时会在 EXE 所在目录自动创建：

```text
config/
logs/
output/
temp/
```

## 自带工具

项目已内置：

- 7-Zip 命令行工具：用于 `.zip`、`.rar`、`.7z`、`.cbz`、`.cbr`、`.cb7`、`.epub`、`.tar`、`.gz` 等格式。
- FFmpeg：构建时通过 `imageio-ffmpeg` 准备，并以单份内置工具打进 EXE，用于读取、修改和封装视频内字幕。

程序只使用项目/EXE 内置的 7-Zip，不再查找电脑上安装的 7-Zip、WinRAR 或 tar。

## 选择方式

压缩包、弹幕、字幕等功能都支持：

- 选择单个文件
- 选择多个文件
- 选择文件夹后自动扫描

字幕示例支持多选和文件夹扫描，界面会形成示例列表，修改时综合多个示例样式。

## 输出策略

- PDF 输出：原 PDF 页面直接追加，图片按原像素尺寸写入，TXT/EPUB 文本生成文本页，尽量不压缩、不降低图片清晰度。
- EPUB 输出：图片生成图页，TXT/EPUB 文本生成章节；PDF 会提取可复制文本生成章节，扫描版图片 PDF 可能无法提取正文。
- 重命名：不直接改源文件，而是在 `重命名输出` 文件夹或自选目录里生成重命名副本；手动规则可设置固定前缀、编号样式、固定后缀，也可用自定义模板如 `视频ep{num:02d}视频`。
- XML 弹幕：输出到 `已修改的弹幕` 文件夹或功能指定目录，不覆盖源 XML。
- 字幕：默认优先保留原扩展名，也可以手动选择输出 `.ass`、`.srt`、`.vtt`；视频封装会生成新的 MKV，可选择保留原字幕并追加，或替换原字幕轨。

注意：ASS 样式只有输出 ASS/SSA 时能完整保留；输出 SRT/VTT 会保留时间和文本，样式会自然降级。

## 效果示例

PDF 相关功能界面右侧有随机效果示例，会在生成过程中随机抽取一张源图片显示缩略图，并显示对应输出 PDF。

## 单独启动

每个功能都可以单独启动：

```powershell
python .\image_archive_pdf\main.py
python .\rename_files\main.py
python .\xml_danmaku\main.py
python .\subtitles\main.py
python .\zh_convert\main.py
```

## 打包

```powershell
python .\build_exe.py
```

打包脚本会自动完成：

- 创建或复用项目内 `.build_venv`
- 安装/更新 PyInstaller、Pillow、ReportLab、img2pdf、natsort、imageio-ffmpeg
- 检查并准备项目内置 7-Zip
- 运行烟测
- 生成单文件 `dist/zipmkv.exe`

不需要手动激活 venv。

## 烟测

```powershell
python .\smoke_test.py
```

烟测覆盖：

- 内置 7-Zip 检测
- 图片文件夹转 PDF
- ZIP/EPUB 转 PDF
- 批量重命名副本
- XML 弹幕处理
- 字幕 ASS/SRT 输出

## 移动端

`mobileapp` 中包含 Android 与原生 HarmonyOS 两套独立工程，iOS 不在当前范围：

- Android：执行 `mobileapp\scripts\build_android.ps1` 生成签名 APK。
- HarmonyOS：Stage 模型 ArkTS 工程，使用真实 HarmonyOS SDK、证书和 Profile 生成 HAP，并可通过官方 `hdc install -r` 侧载。

HarmonyOS 构建不会伪造 SDK、证书、Profile 或 HAP。详细步骤、权限说明和发布审核材料见 [mobileapp/README.md](mobileapp/README.md) 与 `mobileapp/store_assets`。

## 扩展新功能

新增功能建议结构：

```text
new_feature/
├─ __init__.py
├─ core.py
├─ gui.py
└─ main.py
```

约定：

- `core.py` 放纯处理逻辑。
- `gui.py` 暴露 `FeatureFrame`。
- `main.py` 让该功能可以独立启动。
- 在 `features.py` 的 `FEATURES` 列表中增加一项，即可出现在统一界面。
