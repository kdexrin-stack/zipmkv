import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:file_picker/file_picker.dart';

import 'selected_input.dart';

class GeneratedFile {
  const GeneratedFile(this.name, this.bytes);
  final String name;
  final List<int> bytes;
}

class FileService {
  const FileService._();

  static Future<List<SelectedInput>> pickFiles(List<String> extensions) async {
    final result = await FilePicker.pickFiles(
      allowMultiple: true,
      type: FileType.custom,
      allowedExtensions: extensions,
      withData: true,
    );
    if (result == null) return const <SelectedInput>[];
    return result.files
        .where((file) => file.bytes != null)
        .map((file) => SelectedInput(name: file.name, bytes: file.bytes!))
        .toList(growable: false);
  }

  static Future<SelectedInput?> pickOne(List<String> extensions) async {
    final files = await pickFiles(extensions);
    return files.isEmpty ? null : files.first;
  }

  static Future<String?> saveGenerated(
    List<GeneratedFile> outputs,
    String archiveName,
  ) async {
    if (outputs.isEmpty) return null;
    if (outputs.length == 1) {
      final output = outputs.first;
      return FilePicker.saveFile(
        fileName: output.name,
        bytes: Uint8List.fromList(output.bytes),
      );
    }
    final archive = Archive();
    for (final output in outputs) {
      archive.addFile(
        ArchiveFile(output.name, output.bytes.length, output.bytes),
      );
    }
    final zipBytes = ZipEncoder().encode(archive);
    return FilePicker.saveFile(
      fileName: archiveName,
      bytes: Uint8List.fromList(zipBytes),
    );
  }
}
