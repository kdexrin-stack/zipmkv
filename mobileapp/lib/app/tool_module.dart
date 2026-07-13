import 'package:flutter/material.dart';

abstract interface class ToolModule {
  String get id;
  String get category;
  String get title;
  String get description;
  IconData get icon;
  Widget buildPage();
}
