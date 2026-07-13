class DanmakuOptions {
  const DanmakuOptions({
    this.deleteNegative = true,
    this.stripAssTags = false,
    this.offsetSeconds = 0,
  });
  final bool deleteNegative;
  final bool stripAssTags;
  final double offsetSeconds;
}

String processDanmakuXml(String source, DanmakuOptions options) {
  final pattern = RegExp(r'<d\s+([^>]*\bp="([^"]*)"[^>]*)>([\s\S]*?)</d>');
  return source.replaceAllMapped(pattern, (match) {
    final attributes = match.group(1)!;
    final values = match.group(2)!.split(',');
    final originalTime = double.tryParse(values.first) ?? 0;
    if (options.deleteNegative && originalTime < 0) return '';
    values[0] = (originalTime + options.offsetSeconds)
        .clamp(0, double.infinity)
        .toStringAsFixed(3);
    var body = match.group(3)!;
    if (options.stripAssTags) {
      body = body.replaceAll(RegExp(r'\{\\[^}]+\}'), '');
    }
    final updatedAttributes = attributes.replaceFirst(
      match.group(2)!,
      values.join(','),
    );
    return '<d $updatedAttributes>$body</d>';
  });
}
