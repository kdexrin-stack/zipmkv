class AssStyle {
  const AssStyle({
    this.fontName = 'Microsoft YaHei',
    this.fontSize = 48,
    this.primaryColor = '&H00FFFFFF',
    this.outlineColor = '&H00000000',
    this.outline = 2,
  });
  final String fontName;
  final int fontSize;
  final String primaryColor;
  final String outlineColor;
  final double outline;
}

String _assTime(String value) {
  final parts = value.trim().replaceAll(',', '.').split(':');
  if (parts.length != 3) return '0:00:00.00';
  final seconds = double.tryParse(parts[2]) ?? 0;
  return '${int.tryParse(parts[0]) ?? 0}:${parts[1].padLeft(2, '0')}:${seconds.toStringAsFixed(2).padLeft(5, '0')}';
}

String srtToAss(String source, AssStyle style, {String? sampleAss}) {
  final playResX =
      RegExp(
        r'PlayResX:\s*(\d+)',
        caseSensitive: false,
      ).firstMatch(sampleAss ?? '')?.group(1) ??
      '1920';
  final playResY =
      RegExp(
        r'PlayResY:\s*(\d+)',
        caseSensitive: false,
      ).firstMatch(sampleAss ?? '')?.group(1) ??
      '1080';
  final sampleStyle = RegExp(
    r'^Style:\s*Default,.*$',
    caseSensitive: false,
    multiLine: true,
  ).firstMatch(sampleAss ?? '')?.group(0);
  final styleLine =
      sampleStyle ??
      'Style: Default,${style.fontName},${style.fontSize},${style.primaryColor},&H000000FF,${style.outlineColor},&H64000000,0,0,0,0,100,100,0,0,1,${style.outline},0,2,30,30,30,1';
  final cuePattern = RegExp(
    r'(\d+)\s*\r?\n\s*([^\r\n]+)\s*-->\s*([^\r\n]+)\r?\n([\s\S]*?)(?=\r?\n\r?\n|$)',
  );
  final dialogues = <String>[];
  for (final match in cuePattern.allMatches(source.trim())) {
    final text = match.group(4)!.trim().replaceAll(RegExp(r'\r?\n'), r'\N');
    dialogues.add(
      'Dialogue: 0,${_assTime(match.group(2)!)},${_assTime(match.group(3)!)},Default,,0,0,0,,$text',
    );
  }
  return '[Script Info]\nScriptType: v4.00+\nPlayResX: $playResX\nPlayResY: $playResY\n\n'
      '[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n'
      '$styleLine\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n${dialogues.join('\n')}\n';
}

String applyStyleToAss(String source, AssStyle style, {String? sampleAss}) {
  final sampleStyle = RegExp(
    r'^Style:\s*Default,.*$',
    caseSensitive: false,
    multiLine: true,
  ).firstMatch(sampleAss ?? '')?.group(0);
  final replacement =
      sampleStyle ??
      'Style: Default,${style.fontName},${style.fontSize},${style.primaryColor},&H000000FF,${style.outlineColor},&H64000000,0,0,0,0,100,100,0,0,1,${style.outline},0,2,30,30,30,1';
  final pattern = RegExp(
    r'^Style:\s*Default,.*$',
    caseSensitive: false,
    multiLine: true,
  );
  return pattern.hasMatch(source)
      ? source.replaceFirst(pattern, replacement)
      : source;
}
