import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/ui/design.dart';

import 'talk_first.dart';

void main() {
  testWidgets('compact header and bottom talk surface fit a small phone', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(360, 740));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(
      MaterialApp(
        theme: studioTheme(Brightness.dark),
        home: const TalkFirstPreview(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('portrait-0')));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(
      tester.getBottomLeft(find.byKey(const ValueKey('talk-0'))).dy,
      lessThan(tester.getTopLeft(find.byType(NavigationBar)).dy),
    );
  });

  for (final auto in [false, true]) {
    testWidgets(
      'portrait position stays fixed during and after hold (Auto: $auto)',
      (tester) async {
        await tester.pumpWidget(
          MaterialApp(
            theme: studioTheme(Brightness.dark),
            home: TalkFirstPreview(initialAuto: auto),
          ),
        );
        await tester.pumpAndSettle();
        final portrait = find.byKey(const ValueKey('portrait-0'));
        final before = tester.getRect(portrait);
        final gesture = await tester.startGesture(tester.getCenter(portrait));
        await tester.pump(const Duration(milliseconds: 600));
        expect(tester.getRect(portrait), before);
        expect(find.text('Recording…'), findsOneWidget);
        expect(find.textContaining('drag away to cancel'), findsNothing);
        await gesture.up();
        await tester.pumpAndSettle();
        expect(tester.getRect(portrait), before);
        final cancelled = await tester.startGesture(tester.getCenter(portrait));
        await tester.pump(const Duration(milliseconds: 600));
        await cancelled.moveBy(const Offset(80, 0));
        await cancelled.up();
        await tester.pumpAndSettle();
        expect(tester.getRect(portrait), before);
      },
    );
  }

  testWidgets(
    'a portrait hold sends without opening detail; dragging cancels',
    (tester) async {
      var taps = 0;
      final outcomes = <bool>[];
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PreviewHold(
              label: 'Hold',
              onTap: () => taps++,
              onStart: () {},
              onFinish: outcomes.add,
              child: const SizedBox(width: 200, height: 200),
            ),
          ),
        ),
      );
      final target = find.byType(PreviewHold);
      await tester.longPress(target);
      await tester.pump();
      final gesture = await tester.startGesture(tester.getCenter(target));
      await tester.pump(const Duration(milliseconds: 600));
      await gesture.moveBy(const Offset(80, 0));
      await gesture.up();
      await tester.pump();
      expect(taps, 0);
      expect(outcomes, [false, true]);
    },
  );

  testWidgets('scrolling across a portrait neither opens detail nor records', (
    tester,
  ) async {
    final actions = <String>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ListView(
            children: [
              PreviewHold(
                label: 'Hold',
                onTap: () => actions.add('tap'),
                onStart: () => actions.add('record'),
                onFinish: (_) {},
                child: const SizedBox(height: 250),
              ),
              const SizedBox(height: 1000),
            ],
          ),
        ),
      ),
    );
    await tester.drag(find.byType(PreviewHold), const Offset(0, -150));
    await tester.pumpAndSettle();
    expect(actions, isEmpty);
  });

  testWidgets(
    'Recent reply holds target the message author rather than selected Auto recipient',
    (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: studioTheme(Brightness.dark),
          home: const TalkFirstPreview(initialTab: 1, initialAuto: true),
        ),
      );
      await tester.pumpAndSettle();
      final reply = find.byKey(const ValueKey('reply-6'));
      final gesture = await tester.startGesture(tester.getCenter(reply));
      await tester.pump(const Duration(milliseconds: 600));
      expect(
        find.text('Recording → Iris · drag away to cancel'),
        findsOneWidget,
      );
      await gesture.up();
      await tester.pumpAndSettle();
      expect(find.text('Auto listening → Lux'), findsOneWidget);
    },
  );
}
