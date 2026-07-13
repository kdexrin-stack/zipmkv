# zipmkv mobile

移动端包含两个彼此独立的工程：

- `mobileapp/`：Flutter Android 工程，可安装 APK，不依赖 Google Play 服务。
- `mobileapp/harmony/`：原生 HarmonyOS Stage 模型 ArkTS 工程，产物是 HAP，不是 APK 改名或套壳。

iOS 已按当前范围移除。

## 已实现模块

| 功能 | Android | HarmonyOS HAP |
| --- | --- | --- |
| 批量重命名副本 | 已实现 | 已实现 |
| XML 弹幕处理 | 已实现 | 已实现 |
| SRT/ASS 字幕样式 | 已实现 | 已实现 |
| 简体与繁体互转 | 已实现 | 后续扩展 |

所有文件都通过系统选择器授权，结果另存为新文件，不覆盖源文件。Android 与 HarmonyOS 的功能实现互相独立，便于按平台扩展。

## Android 构建

在本目录执行：

```powershell
.\scripts\build_android.ps1
```

脚本会把 Flutter、OpenJDK、Android SDK、Gradle/Pub 缓存和临时目录放在 `mobileapp/toolchain`，运行静态检查与测试，生成并签名 ARM64 APK，适用于当前主流华为及 Android 64 位设备。首次生成的 Android 发布密钥保存在被 Git 忽略的 `mobileapp/signing`，后续升级必须保留同一密钥。

仅在已经完成检查、只需快速重打包时使用：

```powershell
.\scripts\build_android.ps1 -SkipBootstrap -SkipChecks
```

## HarmonyOS 构建与侧载

请先阅读 [harmony/README.md](harmony/README.md)。必须使用华为官方 DevEco/HarmonyOS SDK 以及开发者自己的真实证书和 Profile：

```powershell
cd .\harmony
.\scripts\build_hap.ps1 -BuildMode debug
.\scripts\install_hap.ps1 -HapPath <signed.hap> -HdcPath <HarmonyOS-SDK>\toolchains\hdc.exe
```

构建脚本不会伪造 SDK、证书、Profile 或 HAP。`hdc install -r` 可以侧载合法签名的 HAP，但不能绕过签名校验。

## 扩展模块

Android 新功能实现 `ToolModule`，放入 `lib/features/<feature>`，再注册到 `lib/app/module_registry.dart`。HarmonyOS 新功能放入 `harmony/entry/src/main/ets/features/<feature>`，再注册到 `ToolModule.ets` 与首页路由。

发布说明和隐私审核材料位于 `store_assets/`。
