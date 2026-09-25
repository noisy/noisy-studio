import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/agent_selection.dart';

void main() {
  test(
    'routing commands serialize and only newest confirmed identity is applied',
    () async {
      final calls = <String>[];
      final confirmations = <String?>[];
      final first = Completer<String?>();
      final second = Completer<String?>();
      final routing = AgentSelection(
        stopRecording: () async {
          calls.add('stop');
        },
        request: (id) {
          calls.add(id);
          return id == 'a1' ? first.future : second.future;
        },
        onConfirmed: confirmations.add,
        onFailure: () => fail('unexpected failure'),
      );
      final one = routing.select('a1');
      await Future<void>.delayed(Duration.zero);
      final two = routing.select('a2');
      expect(
        [calls, routing.pending],
        [
          ['stop', 'a1'],
          true,
        ],
      );
      first.complete('canonical-a1');
      await one;
      await Future<void>.delayed(Duration.zero);
      expect(
        [calls, confirmations, routing.pending],
        [
          ['stop', 'a1', 'stop', 'a2'],
          [],
          true,
        ],
      );
      second.complete('canonical-a2');
      await two;
      expect(
        [confirmations, routing.pending],
        [
          ['canonical-a2'],
          false,
        ],
      );
      routing.dispose();
    },
  );

  test(
    'switching connection invalidates old completion and queued requests',
    () async {
      final pending = Completer<String?>();
      final calls = <String>[];
      final confirmations = <String?>[];
      final old = AgentSelection(
        stopRecording: () async {},
        request: (id) {
          calls.add(id);
          return pending.future;
        },
        onConfirmed: confirmations.add,
        onFailure: () => fail('stale failure'),
      );
      final one = old.select('a1');
      await Future<void>.delayed(Duration.zero);
      final two = old.select('a2');
      old.dispose();
      final current = AgentSelection(
        stopRecording: () async {},
        request: (id) async => 'new-session-a3',
        onConfirmed: confirmations.add,
        onFailure: () => fail('unexpected failure'),
      );
      await current.select('a3');
      pending.complete('old-session-a1');
      await Future.wait([one, two]);
      expect(
        [calls, confirmations],
        [
          ['a1'],
          ['new-session-a3'],
        ],
      );
      current.dispose();
    },
  );

  test('demo switch ignores an old request failure', () async {
    final pending = Completer<String?>();
    var failures = 0;
    final routing = AgentSelection(
      stopRecording: () async {},
      request: (_) => pending.future,
      onConfirmed: (_) => fail('stale confirmation'),
      onFailure: () => failures++,
    );
    final request = routing.select('a1');
    await Future<void>.delayed(Duration.zero);
    routing.dispose();
    pending.completeError(StateError('closed connection'));
    await request;
    expect(failures, 0);
  });

  test(
    'server may confirm no active agent rather than the requested id',
    () async {
      final confirmations = <String?>[];
      final routing = AgentSelection(
        stopRecording: () async {},
        request: (_) async => null,
        onConfirmed: confirmations.add,
        onFailure: () => fail('unexpected failure'),
      );
      await routing.select('missing-a1');
      expect(confirmations, [null]);
      routing.dispose();
    },
  );
}
