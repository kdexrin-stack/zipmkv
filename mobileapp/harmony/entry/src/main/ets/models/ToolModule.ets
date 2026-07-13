export class ToolModule {
  id: string;
  title: string;
  description: string;
  route: string;
  symbol: string;

  constructor(id: string, title: string, description: string, route: string, symbol: string) {
    this.id = id;
    this.title = title;
    this.description = description;
    this.route = route;
    this.symbol = symbol;
  }
}

export const TOOL_MODULES: Array<ToolModule> = [
  new ToolModule('rename', '批量文件重命名', '无损复制并按 ep1、ep01、01 等规则命名', 'pages/RenamePage', '文'),
  new ToolModule('danmaku', 'XML 弹幕处理', '删除负时间、整体平移并清理 ASS 标签', 'pages/DanmakuPage', '弹'),
  new ToolModule('subtitle', '字幕样式处理', 'SRT/ASS 转换并按示例或手动参数生成 ASS', 'pages/SubtitlePage', '字')
];
