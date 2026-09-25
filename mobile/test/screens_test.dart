import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/screens.dart';

void main() {
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
              home: Scaffold(body: page),
            ),
          );
          expect(tester.takeException(), isNull);
        }
      });
    }
  }
}
