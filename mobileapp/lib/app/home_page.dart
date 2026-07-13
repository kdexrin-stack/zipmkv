import 'package:flutter/material.dart';

import 'module_registry.dart';
import 'tool_module.dart';

class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    final grouped = <String, List<ToolModule>>{};
    for (final module in toolModules) {
      grouped.putIfAbsent(module.category, () => <ToolModule>[]).add(module);
    }
    return Scaffold(
      appBar: AppBar(title: const Text('zipmkv')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
        children: [
          for (final group in grouped.entries) ...[
            Padding(
              padding: const EdgeInsets.only(top: 14, bottom: 8),
              child: Text(
                group.key,
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ),
            for (final module in group.value)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Card(
                  child: ListTile(
                    leading: Icon(module.icon),
                    title: Text(module.title),
                    subtitle: Text(
                      module.description,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => module.buildPage(),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ],
      ),
    );
  }
}
