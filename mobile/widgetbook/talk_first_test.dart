import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/ui/design.dart';

import 'talk_first.dart';

void main() {
  testWidgets(
    'detail cancel sheet covers navigation and release cancels without navigating',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 740));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        MaterialApp(
          theme: studioTheme(Brightness.dark),
          home: const TalkFirstPreview(initialDetail: 0),
        ),
      );
      await tester.pumpAndSettle();
      final talk = find.byKey(const ValueKey('talk-0'));
      final before = tester.getRect(talk);
      final hold = await tester.startGesture(tester.getCenter(talk));
      await tester.pump(const Duration(milliseconds: 600));
      final cancel = tester.getCenter(find.text('Cancel'));
      expect(
        cancel.dy,
        greaterThan(tester.getTopLeft(find.byType(NavigationBar)).dy),
      );
      expect(cancel.dy, lessThan(740));
      await hold.moveTo(cancel);
      await tester.pump();
      expect(tester.getRect(talk), before);
      await hold.up();
      await tester.pumpAndSettle();
      expect(find.text('Recording preview cancelled'), findsOneWidget);
      expect(find.byKey(const ValueKey('talk-0')), findsOneWidget);
    },
  );

  testWidgets(
    'Recent cancel preview follows Reply after the reversed list settles',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 740));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        MaterialApp(
          theme: studioTheme(Brightness.dark),
          home: const TalkFirstPreview(initialTab: 1, showRecentCancel: true),
        ),
      );
      await tester.pumpAndSettle();
      final reply = tester.getRect(find.byKey(const ValueKey('reply-6')));
      final cancel = tester.getRect(find.text('Cancel'));
      expect(cancel.center.dy, closeTo(reply.center.dy, 1));
      expect(cancel.right, lessThanOrEqualTo(reply.left));
    },
  );

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
        expect(find.text('Recording…'), findsWidgets);
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

  for (final left in [false, true]) {
    testWidgets(
      'visible ${left ? 'left' : 'below'} target cancels only on release and moving back sends',
      (tester) async {
        final outcomes = <bool>[];
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: Center(
                child: PreviewHold(
                  cancelBelow: !left,
                  cancelLeft: left,
                  label: 'Target',
                  onStart: () {},
                  onFinish: outcomes.add,
                  child: const SizedBox(width: 200, height: 150),
                ),
              ),
            ),
          ),
        );
        final target = find.byType(PreviewHold);
        final origin = tester.getCenter(target);
        final gesture = await tester.startGesture(origin);
        await tester.pump(const Duration(milliseconds: 600));
        await gesture.moveBy(Offset(left ? -60 : 0, left ? 0 : 60));
        expect(outcomes, isEmpty);
        final cancel = find.text('Cancel');
        await gesture.moveTo(tester.getCenter(cancel));
        await tester.pump();
        await gesture.moveTo(origin);
        await gesture.up();
        expect(outcomes, [false]);
        final outside = await tester.startGesture(origin);
        await tester.pump(const Duration(milliseconds: 600));
        await outside.moveBy(const Offset(220, 0));
        await outside.up();
        expect(outcomes, [false, false]);
        final releaseCancel = await tester.startGesture(origin);
        await tester.pump(const Duration(milliseconds: 600));
        await releaseCancel.moveTo(tester.getCenter(find.text('Cancel')));
        expect(outcomes, [false, false]);
        await releaseCancel.up();
        expect(outcomes, [false, false, true]);
      },
    );
  }
  testWidgets(
    'bottom row cancel target remains above navigation on small phone',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(360, 740));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(
        MaterialApp(
          theme: studioTheme(Brightness.dark),
          home: const TalkFirstPreview(initialAuto: true),
        ),
      );
      await tester.pumpAndSettle();
      final portrait = find.byKey(const ValueKey('portrait-2'));
      final before = tester.getRect(portrait);
      final gesture = await tester.startGesture(tester.getCenter(portrait));
      await tester.pump(const Duration(milliseconds: 600));
      expect(tester.getRect(portrait), before);
      expect(
        tester.getBottomLeft(find.text('Cancel')).dy,
        lessThan(tester.getTopLeft(find.byType(NavigationBar)).dy),
      );
      await gesture.up();
    },
  );

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

  testWidgets('Auto Recent changes recipient only when a bubble is tapped', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        theme: studioTheme(Brightness.dark),
        home: const TalkFirstPreview(initialTab: 1, initialAuto: true),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Auto listening → Lux'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('message-6')));
    await tester.pumpAndSettle();
    expect(find.text('Auto listening → Iris'), findsOneWidget);
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
      final before = tester.getRect(reply);
      final gesture = await tester.startGesture(tester.getCenter(reply));
      await tester.pump(const Duration(milliseconds: 600));
      expect(find.text('Cancel'), findsOneWidget);
      expect(tester.getRect(reply), before);
      expect(find.text('Auto listening → Lux'), findsOneWidget);
      await gesture.up();
      await tester.pumpAndSettle();
      expect(find.text('Auto listening → Lux'), findsOneWidget);
    },
  );
}
