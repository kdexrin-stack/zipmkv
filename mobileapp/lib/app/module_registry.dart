import '../features/danmaku/danmaku_module.dart';
import '../features/rename/rename_module.dart';
import '../features/subtitle/subtitle_module.dart';
import '../features/zh_convert/zh_convert_module.dart';
import 'tool_module.dart';

const List<ToolModule> toolModules = <ToolModule>[
  RenameModule(),
  SubtitleModule(),
  DanmakuModule(),
  ZhConvertModule(),
];
