import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/daemon_client.dart';
import 'package:noisy_studio_mobile/core/ptt_lease.dart';

class Commands implements DaemonCommands {
  final calls = <bool>[];
  Completer<void>? pending;
  bool fail = false;
  @override
  Future<void> post(String path, Map<String, Object> body) async {
    calls.add(body['held'] as bool);
    if (body['held'] == true) {
      if (fail) throw StateError('offline');
      await pending?.future;
    }
  }
}

void main() {
  testWidgets('cancel in flight finishes with release and no more renewals', (
    tester,
  ) async {
    final commands = Commands()..pending = Completer<void>();
    final lease = PttLease(commands);
    unawaited(lease.start());
    unawaited(lease.stop());
    commands.pending!.complete();
    await tester.pump();
    await tester.pump(const Duration(seconds: 3));
    expect(commands.calls, [true, false]);
    lease.dispose();
  });
  testWidgets('network failure cancels without silently restarting', (
    tester,
  ) async {
    final commands = Commands();
    var failures = 0;
    final lease = PttLease(commands, onFailure: () => failures++);
    await lease.start();
    commands.fail = true;
    await tester.pump(const Duration(milliseconds: 500));
    await tester.pump(const Duration(seconds: 3));
    expect(
      [lease.held, failures, commands.calls],
      [
        false,
        1,
        [true, true, false],
      ],
    );
    lease.dispose();
  });
  testWidgets('dispose releases hold and cancels renewals', (tester) async {
    final commands = Commands();
    final lease = PttLease(commands);
    await lease.start();
    lease.dispose();
    await tester.pump(const Duration(seconds: 3));
    expect(commands.calls, [true, false]);
  });
}
