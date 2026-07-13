import 'package:path/path.dart' as p;

class RenameRule {
  const RenameRule({
    this.prefix = '',
    this.suffix = '',
    this.numberStyle = 'ep01',
    this.start = 1,
    this.step = 1,
  });
  final String prefix;
  final String suffix;
  final String numberStyle;
  final int start;
  final int step;
}

String formatRename(int index, RenameRule rule) {
  final number = rule.start + index * rule.step;
  final formatted = switch (rule.numberStyle) {
    '1' => '$number',
    '01' => number.toString().padLeft(2, '0'),
    '001' => number.toString().padLeft(3, '0'),
    'ep1' => 'ep$number',
    'EP01' => 'EP${number.toString().padLeft(2, '0')}',
    _ => 'ep${number.toString().padLeft(2, '0')}',
  };
  return '${rule.prefix}$formatted${rule.suffix}';
}

String renamedFileName(String sourceName, int index, RenameRule rule) =>
    '${formatRename(index, rule)}${p.extension(sourceName)}';
