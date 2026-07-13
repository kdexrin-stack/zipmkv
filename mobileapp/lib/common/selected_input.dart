import 'dart:typed_data';

class SelectedInput {
  const SelectedInput({required this.name, required this.bytes});
  final String name;
  final Uint8List bytes;
}
