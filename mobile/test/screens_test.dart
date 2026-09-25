import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/screens.dart';

void main() {
  setUpAll(() async {
    final font = FontLoader('Studio Sans')
      ..addFont(rootBundle.load('assets/fonts/Roboto-Regular.ttf'));
    await font.load();
    final icons = FontLoader('MaterialIcons')
      ..addFont(rootBundle.load('fonts/MaterialIcons-Regular.otf'));
    await icons.load();
  });
  for (final brightness in Brightness.values) {
    for (final width in [360.0, 430.0]) {
      testWidgets('screens fit $width $brightness', (tester) async {
        tester.view.physicalSize = Size(width, 740);
        tester.view.devicePixelRatio = 1;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);
        final data = fixture(count: 7);
        final address = TextEditingController();
        addTearDown(address.dispose);
        var pageIndex = 0;
        for (final page in [
          AgentsView(snapshot: data, onSelect: (_) {}),
          TalkView(
            snapshot: data,
            agent: data.agents.first,
            onHold: () {},
            onRelease: () {},
            onToggle: () {},
            onAuto: (_) {},
            onMute: () {},
            onStop: () {},
          ),
          MessagesView(messages: data.messages),
          ConnectionSettings(address: address, onConnect: () {}, onDemo: () {}),
        ]) {
          await tester.pumpWidget(
            MaterialApp(
              theme: studioTheme(brightness),
              home: RepaintBoundary(
                key: const ValueKey('capture'),
                child: Scaffold(body: page),
              ),
            ),
          );
          await tester.runAsync(
            () => precacheImage(
              const AssetImage('assets/avatars/editorial.webp'),
              tester.element(find.byType(Scaffold)),
            ),
          );
          await tester.pumpAndSettle();
          expect(tester.takeException(), isNull);
          if (const bool.fromEnvironment('CAPTURE_SCREENSHOTS')) {
            await tester.pumpAndSettle();
            final boundary = tester.renderObject<RenderRepaintBoundary>(
              find.byKey(const ValueKey('capture')),
            );
            await tester.runAsync(() async {
              final image = await boundary.toImage();
              final bytes = await image.toByteData(
                format: ui.ImageByteFormat.png,
              );
              final file = File(
                'build/screenshots/${brightness.name}-${width.toInt()}-${pageIndex++}.png',
              );
              await file.parent.create(recursive: true);
              await file.writeAsBytes(bytes!.buffer.asUint8List());
            });
          }
        }
      });
    }
  }
}
