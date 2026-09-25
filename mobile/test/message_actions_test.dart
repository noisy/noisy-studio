import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';
import 'package:noisy_studio_mobile/ui/screens.dart';
import 'package:noisy_studio_mobile/core/message_actions.dart';
import 'package:noisy_studio_mobile/core/models.dart';

void main() {
  testWidgets('shared feed forwards replay identity into the live callback', (
    tester,
  ) async {
    final ids = <int>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: MessagesView(
            messages: const [
              Message('a1', 'Lux', 'Hello', id: 91, status: 'played'),
            ],
            onReplay: (message) => ids.add(message.id),
          ),
        ),
      ),
    );
    await tester.tap(find.byTooltip('Play this message again'));
    expect(ids, [91]);
  });
  const message = Message('a1', 'Lux', '[voice] „Hello”', id: 91);
  test('replay carries original card and conversation identity', () async {
    final calls = <Object>[];
    final actions = MessageActions(
      request: (path, body) async {
        calls.add([path, body]);
        return {'queued': true};
      },
      onError: (_) => fail('unexpected error'),
    );
    await actions.perform(MessageAction.replay, message);
    expect(calls, [
      [
        '/speak',
        {
          'text': 'Hello',
          'source_id': 91,
          'agent': 'a1',
          'wait': false,
          'card': false,
          'interrupt': true,
        },
      ],
    ]);
    actions.dispose();
  });
  test(
    'pause changes only on confirmation and double presses do not toggle twice',
    () async {
      final response = Completer<Map<String, dynamic>>();
      var calls = 0;
      final actions = MessageActions(
        request: (_, _) {
          calls++;
          return response.future;
        },
        onError: (_) => fail('unexpected error'),
      )..playingId = 91;
      final pending = actions.playback(togglePause: true);
      await actions.playback(togglePause: true);
      expect([calls, actions.pausedId, actions.busy], [1, 0, true]);
      response.complete({'paused': true});
      await pending;
      expect(actions.pausedId, 91);
      actions.playingId = 92;
      expect(actions.pausedId, 0);
      actions.dispose();
    },
  );
  test('recall rejection is reported without success state', () async {
    var calls = 0;
    final errors = <String>[];
    final actions = MessageActions(
      request: (_, _) async {
        calls++;
        return {'cancelled': false};
      },
      onError: errors.add,
    )..playingId = 92;
    await actions.perform(MessageAction.cancel, message);

    expect([calls, errors.length, actions.pausedId], [1, 1, 0]);
    actions.dispose();
  });
  test('old session responses cannot publish pause state or errors', () async {
    final response = Completer<Map<String, dynamic>>();
    final errors = <String>[];
    final actions = MessageActions(
      request: (_, _) => response.future,
      onError: errors.add,
    )..playingId = 91;
    final pending = actions.playback(togglePause: true);
    actions.dispose();
    response.completeError(StateError('offline'));
    await pending;
    expect(errors, isEmpty);
  });
}
