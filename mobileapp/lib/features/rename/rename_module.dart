import 'package:flutter/material.dart';

import '../../app/tool_module.dart';
import '../../common/file_service.dart';
import '../../common/input_list.dart';
import '../../common/selected_input.dart';
import 'rename_core.dart';

class RenameModule implements ToolModule {
  const RenameModule();
  @override
  String get id => 'rename';
  @override
  String get category => '文件工具';
  @override
  String get title => '批量文件重命名';
  @override
  String get description => '按 ep1、ep01、01 等规则生成重命名副本。';
  @override
  IconData get icon => Icons.drive_file_rename_outline;
  @override
  Widget buildPage() => const RenamePage();
}

class RenamePage extends StatefulWidget {
  const RenamePage({super.key});
  @override
  State<RenamePage> createState() => _RenamePageState();
}

class _RenamePageState extends State<RenamePage> {
  final files = <SelectedInput>[];
  final prefix = TextEditingController();
  final suffix = TextEditingController();
  final start = TextEditingController(text: '1');
  String style = 'ep01';
  bool busy = false;
  String status = '';

  RenameRule get rule => RenameRule(
    prefix: prefix.text,
    suffix: suffix.text,
    numberStyle: style,
    start: int.tryParse(start.text) ?? 1,
  );

  Future<void> pick() async {
    final selected = await FileService.pickFiles(const [
      'mp4',
      'mkv',
      'avi',
      'mov',
      'jpg',
      'png',
      'txt',
      'srt',
      'ass',
      'zip',
    ]);
    if (mounted && selected.isNotEmpty) setState(() => files.addAll(selected));
  }

  Future<void> run() async {
    if (files.isEmpty || busy) return;
    setState(() {
      busy = true;
      status = '正在生成重命名副本...';
    });
    try {
      final outputs = <GeneratedFile>[
        for (var index = 0; index < files.length; index++)
          GeneratedFile(
            renamedFileName(files[index].name, index, rule),
            files[index].bytes,
          ),
      ];
      final path = await FileService.saveGenerated(outputs, 'zipmkv_重命名输出.zip');
      if (mounted) {
        setState(() => status = path == null ? '已取消保存。' : '处理完成，源文件未修改。');
      }
    } catch (error) {
      if (mounted) setState(() => status = '处理失败：$error');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final preview = files.take(3).toList();
    return Scaffold(
      appBar: AppBar(title: const Text('批量文件重命名')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FilledButton.icon(
            onPressed: busy ? null : pick,
            icon: const Icon(Icons.add),
            label: const Text('选择文件'),
          ),
          InputList(
            files: files,
            onRemove: (index) => setState(() => files.removeAt(index)),
          ),
          const Divider(),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: prefix,
                  decoration: const InputDecoration(labelText: '固定前缀'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: style,
                  decoration: const InputDecoration(labelText: '编号样式'),
                  items: const ['1', '01', '001', 'ep1', 'ep01', 'EP01']
                      .map(
                        (value) =>
                            DropdownMenuItem(value: value, child: Text(value)),
                      )
                      .toList(),
                  onChanged: (value) => setState(() => style = value ?? style),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: suffix,
                  decoration: const InputDecoration(labelText: '固定后缀'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: TextField(
                  controller: start,
                  keyboardType: TextInputType.number,
                  decoration: const InputDecoration(labelText: '起始编号'),
                ),
              ),
            ],
          ),
          if (preview.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text('预览', style: Theme.of(context).textTheme.titleSmall),
            for (var index = 0; index < preview.length; index++)
              Text(
                '${preview[index].name}  →  ${renamedFileName(preview[index].name, index, rule)}',
              ),
          ],
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: files.isEmpty || busy ? null : run,
            icon: const Icon(Icons.play_arrow),
            label: const Text('生成副本'),
          ),
          if (status.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(status),
            ),
        ],
      ),
    );
  }
}
