# 发布审核清单

- [ ] Android APK 已通过 `apksigner verify`，包名、版本号和 SHA-256 已记录。
- [ ] HarmonyOS HAP 使用真实 HarmonyOS SDK、证书和 Profile 构建并完成官方签名校验。
- [ ] HAP 已在目标鸿蒙真机通过 `hdc install -r` 安装并逐项测试。
- [ ] Android 截图来自实际 Flutter 界面；HarmonyOS 截图来自实际 ArkTS HAP，不能混用。
- [ ] 应用图标、名称、截图和说明中没有个人文件名、路径、账号、通知或设备标识。
- [ ] 正式包权限与 `permissions.md` 一致。
- [ ] Git 仓库未包含签名私钥、证书、Profile、密码、SDK、工具链、构建缓存和用户测试文件。
- [ ] 应用市场后台已填写开发者主体、支持邮箱、隐私政策公开链接和软件著作权等真实资料。
- [ ] 软件著作权、开发者实名、SDK、证书/Profile 均为真实材料，没有用占位内容提交审核。
