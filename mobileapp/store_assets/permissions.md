# 权限与数据审核

## Android 正式包

- `android/app/src/main/AndroidManifest.xml` 未声明网络、相机、麦克风、位置、通讯录或宽泛存储权限。
- `android.permission.INTERNET` 只存在于 Flutter 的 `src/debug` 清单，用于开发调试，不进入 release APK。
- 文件访问通过 Android Storage Access Framework，由系统选择器授予单个文件或保存位置。

## HarmonyOS 正式包

- `entry/src/main/module.json5` 未声明系统权限。
- 文件访问通过系统 DocumentViewPicker，由用户主动选择输入和输出。

## 发布前复核

1. 对最终 APK/HAP 解包或使用官方工具核对合并后的权限清单。
2. 检查包内不存在证书私钥、Profile、`key.properties`、本机绝对路径和测试文件。
3. 在断网状态完成所有审核操作，确认没有隐式联网依赖。
4. 新增依赖、权限或联网功能后，重新更新隐私政策与应用市场数据安全表。
