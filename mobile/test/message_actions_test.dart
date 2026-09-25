import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/message_actions.dart';
import 'package:noisy_studio_mobile/core/models.dart';

void main() {
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
      final pending = actions.perform(MessageAction.pause, message);
      await actions.perform(MessageAction.pause, message);
      expect([calls, actions.pausedId, actions.busy], [1, 0, true]);
      response.complete({'paused': true});
      await pending;
      expect(actions.pausedId, 91);
      actions.playingId = 92;
      expect(actions.pausedId, 0);
      actions.dispose();
    },
  );
  test(
    'recall rejection and stale playback are reported without success state',
    () async {
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
      await actions.perform(MessageAction.skip, message);
      expect([calls, errors.length, actions.pausedId], [1, 2, 0]);
      actions.dispose();
    },
  );
  test('old session responses cannot publish pause state or errors', () async {
    final response = Completer<Map<String, dynamic>>();
    final errors = <String>[];
    final actions = MessageActions(
      request: (_, _) => response.future,
      onError: errors.add,
    )..playingId = 91;
    final pending = actions.perform(MessageAction.pause, message);
    actions.dispose();
    response.completeError(StateError('offline'));
    await pending;
    expect(errors, isEmpty);
  });
}
