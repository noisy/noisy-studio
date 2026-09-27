import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/daemon_client.dart';
import 'package:noisy_studio_mobile/core/direct_hold.dart';
import 'package:noisy_studio_mobile/core/models.dart';

class Harness implements DaemonCommands {
  final calls = <String>[];
  Completer<void>? selection, idle;
  bool reject = false;
  late final DirectHold control;
  Harness({bool auto = true, String? initial = 'a1'}) {
    control = DirectHold(
      commands: this,
      initial: Snapshot(activeId: initial, auto: auto),
      selectAgent: (id) async {
        calls.add('select $id');
        await selection?.future;
        return reject ? null : id;
      },
      setAuto: (value) async {
        calls.add('auto $value');
      },
      waitForIdle: ({required discarded}) async {
        calls.add('idle $discarded');
        await idle?.future;
      },
      onError: (_) => calls.add('error'),
    );
  }
  @override
  Future<void> post(String path, Map<String, Object> body) async {
    calls.add(path == '/ptt' ? 'held ${body['held']}' : 'abort');
  }
}

void main() {
  testWidgets(
    'direct reply discards before release and restores Auto only after idle',
    (tester) async {
      final h = Harness();
      await h.control.start('a2');
      h.idle = Completer<void>();
      final ending = h.control.finish(discard: true);
      await tester.pump();
      expect(h.calls, [
        'auto false',
        'abort',
        'idle true',
        'select a2',
        'held true',
        'abort',
        'held false',
        'idle true',
      ]);
      h.idle!.complete();
      await ending;
      expect(h.calls.sublist(8), ['select a1', 'auto true']);
      h.control.dispose();
    },
  );
  testWidgets(
    'release during recipient confirmation never starts late recording',
    (tester) async {
      final h = Harness(auto: false)..selection = Completer<void>();
      final starting = h.control.start('a2');
      await tester.pump();
      final ending = h.control.finish(discard: false);
      h.selection!.complete();
      await starting;
      await ending;
      expect(h.calls, ['select a2']);
      h.control.dispose();
    },
  );
  testWidgets('backgrounding cancels without restoring Auto', (tester) async {
    final h = Harness();
    await h.control.start('a2');
    h.control.didChangeAppLifecycleState(AppLifecycleState.inactive);
    await tester.pump();
    expect(h.calls, [
      'auto false',
      'abort',
      'idle true',
      'select a2',
      'held true',
      'abort',
      'held false',
      'idle true',
    ]);
    h.control.dispose();
  });
  testWidgets('new selection while finishing prevents prior Auto restoration', (
    tester,
  ) async {
    final h = Harness();
    await h.control.start('a2');
    h.idle = Completer<void>();
    final ending = h.control.finish(discard: false);
    await tester.pump();
    final selecting = h.control.select('a3');
    h.idle!.complete();
    await ending;
    await selecting;
    expect(h.calls.sublist(5), ['held false', 'idle false', 'select a3']);
    h.control.dispose();
  });
  testWidgets(
    'Auto without an original recipient is not resumed on direct target',
    (tester) async {
      final h = Harness(initial: null);
      await h.control.start('a2');
      await h.control.finish(discard: false);
      expect(h.control.auto, false);
      expect(h.calls.last, 'idle false');
      h.control.dispose();
    },
  );
  testWidgets('unconfirmed target fails closed without acquiring a lease', (
    tester,
  ) async {
    final h = Harness(auto: false)..reject = true;
    await h.control.start('a2');
    expect(h.calls, ['select a2', 'error']);
    expect(h.control.connected, false);
    h.control.dispose();
  });
}
