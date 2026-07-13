import 'dart:convert';

import 'package:flutter/material.dart';

import '../../app/tool_module.dart';
import '../../common/file_service.dart';
import '../../common/input_list.dart';
import '../../common/selected_input.dart';
import 'danmaku_core.dart';

class DanmakuModule implements ToolModule {
  const DanmakuModule();
  @override
  String get id => 'danmaku';
  @override
  String get category => '字幕与弹幕';
  @override
  String get title => 'XML 弹幕批量处理';
  @override
  String get description => '删除负时间、整体平移并清理 ASS 标签。';
  @override
  IconData get icon => Icons.comment_outlined;
  @override
  Widget buildPage() => const DanmakuPage();
}

class DanmakuPage extends StatefulWidget {
  const DanmakuPage({super.key});
  @override
  State<DanmakuPage> createState() => _DanmakuPageState();
}

class _DanmakuPageState extends State<DanmakuPage> {
  final files = <SelectedInput>[];
  final offset = TextEditingController(text: '0');
  bool deleteNegative = true;
  bool stripTags = false;
  bool busy = false;
  String status = '';

  Future<void> pick() async {
    final selected = await FileService.pickFiles(const ['xml']);
    if (mounted && selected.isNotEmpty) setState(() => files.addAll(selected));
  }

  Future<void> run() async {
    if (files.isEmpty || busy) return;
    setState(() {
      busy = true;
      status = '正在处理弹幕...';
    });
    try {
      final options = DanmakuOptions(
        deleteNegative: deleteNegative,
        stripAssTags: stripTags,
        offsetSeconds: double.tryParse(offset.text) ?? 0,
      );
      final outputs = files.map((file) {
        final text = utf8.decode(file.bytes, allowMalformed: true);
        return GeneratedFile(
          file.name.replaceFirst(
            RegExp(r'\.xml$', caseSensitive: false),
            '_modified.xml',
          ),
          utf8.encode(processDanmakuXml(text, options)),
        );
      }).toList();
      final path = await FileService.saveGenerated(outputs, 'zipmkv_弹幕输出.zip');
      if (mounted) {
        setState(() => status = path == null ? '已取消保存。' : '处理完成，源 XML 未修改。');
      }
    } catch (error) {
      if (mounted) setState(() => status = '处理失败：$error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('XML 弹幕批量处理')),
    body: ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FilledButton.icon(
          onPressed: busy ? null : pick,
          icon: const Icon(Icons.add),
          label: const Text('选择 XML'),
        ),
        InputList(
          files: files,
          onRemove: (index) => setState(() => files.removeAt(index)),
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('删除负时间弹幕'),
          value: deleteNegative,
          onChanged: (value) => setState(() => deleteNegative = value),
        ),
        SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: const Text('清理 ASS 样式标签'),
          value: stripTags,
          onChanged: (value) => setState(() => stripTags = value),
        ),
        TextField(
          controller: offset,
          keyboardType: const TextInputType.numberWithOptions(
            decimal: true,
            signed: true,
          ),
          decoration: const InputDecoration(labelText: '时间平移（秒，负数为提前）'),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(
          onPressed: files.isEmpty || busy ? null : run,
          icon: const Icon(Icons.play_arrow),
          label: const Text('开始处理'),
        ),
        if (status.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 12), child: Text(status)),
      ],
    ),
  );
}
