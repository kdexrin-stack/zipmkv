import 'package:flutter/material.dart';

import 'selected_input.dart';

class InputList extends StatelessWidget {
  const InputList({super.key, required this.files, required this.onRemove});
  final List<SelectedInput> files;
  final ValueChanged<int> onRemove;

  @override
  Widget build(BuildContext context) {
    if (files.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 20),
        child: Center(child: Text('尚未选择文件')),
      );
    }
    return Column(
      children: [
        for (var index = 0; index < files.length; index++)
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.insert_drive_file_outlined),
            title: Text(
              files[index].name,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            trailing: IconButton(
              tooltip: '移除',
              onPressed: () => onRemove(index),
              icon: const Icon(Icons.close),
            ),
          ),
      ],
    );
  }
}
