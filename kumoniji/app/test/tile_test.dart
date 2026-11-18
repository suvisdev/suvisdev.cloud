import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kumoniji/tile.dart';

void main() {
  testWidgets('tap calls onTap', (t) async {
    var taps = 0;
    await t.pumpWidget(
      MaterialApp(
        home: Center(
          child: TileView(code: 's3', onTap: () => taps++),
        ),
      ),
    );
    await t.tap(find.byType(TileView));
    expect(taps, 1);
  });
}
