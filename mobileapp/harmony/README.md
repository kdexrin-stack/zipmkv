# zipmkv 原生 HarmonyOS 应用

这是独立的 Stage 模型 ArkTS/HAP 工程，不是 Android APK 的改名或封装。

## 已实现

- 批量文件重命名：支持 `ep1`、`ep01`、`01`、`1`，固定前后缀和起始序号；通过无损文件复制生成新文件。
- XML 弹幕处理：删除负时间弹幕、整体平移时间、清理 ASS 标签。
- 字幕样式处理：SRT 转 ASS、ASS/SSA 样式修改、读取 ASS 示例样式；示例与手动参数冲突时，手动非空参数优先。
- 系统 FilePicker：一次选择一个或多个文件，每个输出均由用户确认保存位置，不覆盖源文件。
- 模块注册表：新增功能只需增加独立 `features/<name>`、页面和注册项。

## 真实构建条件

1. 从华为官方安装 DevEco Studio 或 Command Line Tools，以及与工程匹配的 HarmonyOS SDK。
2. 将 `DEVECO_TOOLS_HOME` 指向包含 `hvigor`、`ohpm` 的工具目录，将 `DEVECO_SDK_HOME` 指向真实 SDK。
3. 真机安装前，在 DevEco Studio 的 `File > Project Structure > Signing Configs` 配置您自己的证书和 Profile。
4. 执行：

```powershell
.\scripts\build_hap.ps1 -BuildMode debug
```

项目使用 `5.0.5(17)` 稳定 SDK 基线；更高版本 DevEco Studio 可以执行官方工程升级。构建脚本不会下载不明 SDK，也不会生成、伪造或提交签名身份。

## 侧载安装

开启设备开发者模式和 USB 调试，连接并授权后执行：

```powershell
.\scripts\install_hap.ps1 -HapPath .\entry\build\...\entry-default-signed.hap -HdcPath <HarmonyOS-SDK>\toolchains\hdc.exe
```

HarmonyOS 支持使用 `hdc install -r` 安装/覆盖安装 HAP，但真机仍只接受合法签名包。详见[华为开发入门的签名说明](https://developer.huawei.com/consumer/cn/develop-novice-guide/)和[官方 hdc 安装说明](https://gitee.com/openharmony/docs/blob/master/zh-cn/device-dev/subsystems/subsys-toolchain-hdc-guide.md)。

## 隐私

应用不联网、不注册账号、不含广告或分析 SDK，不申请宽泛存储权限。文件仅在用户通过系统 FilePicker 授权后读取，输出仍由用户选择保存位置。签名材料目录已被 Git 忽略。
