import 'package:flutter_test/flutter_test.dart';
import 'package:zipmkv_mobile/features/danmaku/danmaku_core.dart';
import 'package:zipmkv_mobile/features/rename/rename_core.dart';
import 'package:zipmkv_mobile/features/subtitle/subtitle_core.dart';

void main() {
  test('manual rename patterns preserve extension', () {
    const rule = RenameRule(prefix: '视频', suffix: '视频', numberStyle: 'ep01');
    expect(renamedFileName('raw.mkv', 0, rule), '视频ep01视频.mkv');
    expect(renamedFileName('raw.mkv', 1, rule), '视频ep02视频.mkv');
  });

  test('danmaku removes negative and shifts time', () {
    const source =
        '<i><d p="-1,1,25,0">bad</d><d p="1,1,25,0">{\\b1}ok</d></i>';
    final result = processDanmakuXml(
      source,
      const DanmakuOptions(
        deleteNegative: true,
        stripAssTags: true,
        offsetSeconds: 2,
      ),
    );
    expect(result, isNot(contains('bad')));
    expect(result, contains('3.000,1,25,0'));
    expect(result, isNot(contains(r'{\b1}')));
  });

  test('srt converts to styled ass', () {
    const source = '1\n00:00:01,000 --> 00:00:02,500\nhello\n';
    final result = srtToAss(
      source,
      const AssStyle(fontName: 'Noto Sans CJK SC', fontSize: 52),
    );
    expect(result, contains('Style: Default,Noto Sans CJK SC,52'));
    expect(result, contains('Dialogue: 0,0:00:01.00,0:00:02.50'));
  });
}
