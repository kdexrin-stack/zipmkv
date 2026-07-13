import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;

import '../../app/tool_module.dart';
import '../../common/file_service.dart';
import '../../common/input_list.dart';
import '../../common/selected_input.dart';
import 'subtitle_core.dart';

class SubtitleModule implements ToolModule {
  const SubtitleModule();
  @override
  String get id => 'subtitle';
  @override
  String get category => '字幕与弹幕';
  @override
  String get title => '字幕样式转换';
  @override
  String get description => '读取 SRT/ASS，按示例或手动样式生成 ASS。';
  @override
  IconData get icon => Icons.subtitles_outlined;
  @override
  Widget buildPage() => const SubtitlePage();
}

class SubtitlePage extends StatefulWidget {
  const SubtitlePage({super.key});
  @override
  State<SubtitlePage> createState() => _SubtitlePageState();
}

class _SubtitlePageState extends State<SubtitlePage> {
  final files = <SelectedInput>[];
  SelectedInput? sample;
  final font = TextEditingController(text: 'Microsoft YaHei');
  final size = TextEditingController(text: '48');
  final primary = TextEditingController(text: '&H00FFFFFF');
  final outlineColor = TextEditingController(text: '&H00000000');
  final outline = TextEditingController(text: '2');
  bool busy = false;
  String status = '';

  Future<void> pickTargets() async {
    final selected = await FileService.pickFiles(const ['srt', 'ass', 'ssa']);
    if (mounted && selected.isNotEmpty) setState(() => files.addAll(selected));
  }

  Future<void> pickSample() async {
    final selected = await FileService.pickOne(const ['ass', 'ssa']);
    if (mounted && selected != null) setState(() => sample = selected);
  }

  Future<void> run() async {
    if (files.isEmpty || busy) return;
    setState(() {
      busy = true;
      status = '正在生成 ASS...';
    });
    try {
      final style = AssStyle(
        fontName: font.text.trim().isEmpty
            ? 'Microsoft YaHei'
            : font.text.trim(),
        fontSize: int.tryParse(size.text) ?? 48,
        primaryColor: primary.text.trim(),
        outlineColor: outlineColor.text.trim(),
        outline: double.tryParse(outline.text) ?? 2,
      );
      final sampleText = sample == null
          ? null
          : utf8.decode(sample!.bytes, allowMalformed: true);
      final outputs = files.map((file) {
        final source = utf8.decode(file.bytes, allowMalformed: true);
        final ass = p.extension(file.name).toLowerCase() == '.srt'
            ? srtToAss(source, style, sampleAss: sampleText)
            : applyStyleToAss(source, style, sampleAss: sampleText);
        return GeneratedFile(
          '${p.basenameWithoutExtension(file.name)}_modified.ass',
          utf8.encode(ass),
        );
      }).toList();
      final path = await FileService.saveGenerated(outputs, 'zipmkv_字幕输出.zip');
      if (mounted) {
        setState(() => status = path == null ? '已取消保存。' : 'ASS 已生成，源字幕未修改。');
      }
    } catch (error) {
      if (mounted) setState(() => status = '处理失败：$error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('字幕样式转换')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: busy ? null : pickTargets,
                icon: const Icon(Icons.add),
                label: const Text('选择目标字幕'),
              ),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              onPressed: busy ? null : pickSample,
              icon: const Icon(Icons.palette_outlined),
              label: const Text('示例 ASS'),
            ),
          ],
        ),
        if (sample != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('示例：${sample!.name}'),
          ),
        InputList(
          files: files,
          onRemove: (index) => setState(() => files.removeAt(index)),
        ),
        TextField(
          controller: font,
          decoration: const InputDecoration(labelText: '字体'),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: size,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: '字号'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: outline,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                decoration: const InputDecoration(labelText: '描边'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        TextField(
          controller: primary,
          decoration: const InputDecoration(labelText: '主颜色（ASS 编码）'),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: outlineColor,
          decoration: const InputDecoration(labelText: '描边颜色（ASS 编码）'),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: files.isEmpty || busy ? null : run,
          icon: const Icon(Icons.play_arrow),
          label: const Text('生成 ASS'),
        ),
        if (status.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(status)),
      ],
    ),
  );
}
