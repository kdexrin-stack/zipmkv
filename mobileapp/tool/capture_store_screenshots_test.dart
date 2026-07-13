import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zipmkv_mobile/app/zipmkv_app.dart';

Future<void> loadScreenshotFont() async {
  final file = File('toolchain/fonts/NotoSansCJKsc-Regular.otf');
  if (!file.existsSync()) {
    throw StateError(
      'Screenshot font is missing. Run scripts/capture_store_screenshots.ps1.',
    );
  }
  final bytes = Uint8List.fromList(file.readAsBytesSync());
  final loader = FontLoader('NotoSansSC')
    ..addFont(Future<ByteData>.value(ByteData.view(bytes.buffer)));
  await loader.load();

  final iconFile = File(
    'toolchain/flutter/bin/cache/artifacts/material_fonts/MaterialIcons-Regular.otf',
  );
  if (!iconFile.existsSync()) {
    throw StateError('Flutter Material Icons font is missing.');
  }
  final iconBytes = Uint8List.fromList(iconFile.readAsBytesSync());
  final iconLoader = FontLoader('MaterialIcons')
    ..addFont(Future<ByteData>.value(ByteData.view(iconBytes.buffer)));
  await iconLoader.load();
}

void configurePhone(WidgetTester tester) {
  tester.view.devicePixelRatio = 3;
  tester.view.physicalSize = const Size(1080, 2400);
  addTearDown(tester.view.reset);
}

void main() {
  setUpAll(loadScreenshotFont);

  testWidgets('capture privacy-safe store screenshots', (tester) async {
    configurePhone(tester);
    await tester.pumpWidget(const ZipMkvApp(fontFamily: 'NotoSansSC'));
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../store_assets/screenshots/android_home.png'),
    );

    await tester.tap(find.text('批量文件重命名'));
    await tester.pumpAndSettle();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../store_assets/screenshots/android_rename.png'),
    );

    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.text('字幕样式转换'));
    await tester.pumpAndSettle();
    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('../store_assets/screenshots/android_subtitle.png'),
    );
  });
}
