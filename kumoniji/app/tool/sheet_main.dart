// 확인용(배포 안 함): 앱의 SVG 엔진으로 패 53장을 그대로 늘어놓는다. flutter run -t tool/sheet_main.dart
import 'package:flutter/material.dart';
import 'package:kumoniji/tile.dart';

void main() => runApp(
  MaterialApp(
    home: Scaffold(
      backgroundColor: const Color(0xFFFFF9EC),
      body: Wrap(
        children: [
          for (final s in 'mslc'.split(''))
            for (var n = 1; n <= 13; n++)
              Padding(
                padding: const EdgeInsets.all(2),
                child: TileView(code: '$s$n', width: 70),
              ),
          const TileView(code: 'back', width: 70),
        ],
      ),
    ),
  ),
);
