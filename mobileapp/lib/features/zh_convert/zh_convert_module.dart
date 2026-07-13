import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_open_chinese_convert/flutter_open_chinese_convert.dart';
import 'package:path/path.dart' as p;

import '../../app/tool_module.dart';
import '../../common/file_service.dart';
import '../../common/input_list.dart';
import '../../common/selected_input.dart';

class ZhConvertModule implements ToolModule {
  const ZhConvertModule();
  @override
  String get id => 'zh_convert';
  @override
  String get category => '文字工具';
  @override
  String get title => '繁简文字转换';
  @override
  String get description => '批量转换 TXT、字幕、XML 与 Markdown。';
  @override
  IconData get icon => Icons.translate;
  @override
  Widget buildPage() => const ZhConvertPage();
}

class ZhConvertPage extends StatefulWidget {
  const ZhConvertPage({super.key});
  @override
  State<ZhConvertPage> createState() => _ZhConvertPageState();
}

class _ZhConvertPageState extends State<ZhConvertPage> {
  final files = <SelectedInput>[];
  String mode = 't2s';
  bool busy = false;
  String status = '';

  Future<String> convert(String text) => switch (mode) {
    's2t' => ChineseConverter.convert(text, S2T()),
    's2tw' => ChineseConverter.convert(text, S2TWp()),
    _ => ChineseConverter.convert(text, T2S()),
  };

  Future<void> pick() async {
    final selected = await FileService.pickFiles(const [
      'txt',
      'md',
      'srt',
      'ass',
      'ssa',
      'vtt',
      'xml',
      'html',
    ]);
    if (mounted && selected.isNotEmpty) setState(() => files.addAll(selected));
  }

  Future<void> run() async {
    if (files.isEmpty || busy) return;
    setState(() {
      busy = true;
      status = '正在转换...';
    });
    try {
      final outputs = <GeneratedFile>[];
      for (final file in files) {
        final source = utf8.decode(file.bytes, allowMalformed: true);
        final converted = await convert(source);
        outputs.add(
          GeneratedFile(
            '${p.basenameWithoutExtension(file.name)}_$mode${p.extension(file.name)}',
            utf8.encode(converted),
          ),
        );
      }
      final path = await FileService.saveGenerated(
        outputs,
        'zipmkv_繁简转换输出.zip',
      );
      if (mounted) {
        setState(() => status = path == null ? '已取消保存。' : '转换完成，源文件未修改。');
      }
    } catch (error) {
      if (mounted) setState(() => status = '转换失败：$error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('繁简文字转换')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FilledButton.icon(
          onPressed: busy ? null : pick,
          icon: const Icon(Icons.add),
          label: const Text('选择文本/字幕/XML'),
        ),
        InputList(
          files: files,
          onRemove: (index) => setState(() => files.removeAt(index)),
        ),
        DropdownButtonFormField<String>(
          initialValue: mode,
          decoration: const InputDecoration(labelText: '转换方向'),
          items: const [
            DropdownMenuItem(value: 't2s', child: Text('繁体 → 简体')),
            DropdownMenuItem(value: 's2t', child: Text('简体 → 繁体')),
            DropdownMenuItem(value: 's2tw', child: Text('简体 → 台湾繁体')),
          ],
          onChanged: (value) => setState(() => mode = value ?? mode),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: files.isEmpty || busy ? null : run,
          icon: const Icon(Icons.play_arrow),
          label: const Text('开始转换'),
        ),
        if (status.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(status)),
      ],
    ),
  );
}
