import 'dart:convert';
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:noisy_studio_mobile/core/daemon_client.dart';

void main() {
  test(
    'poll started before a command cannot publish stale recipient afterwards',
    () async {
      final pending = Completer<http.Response>();
      var polls = 0;
      final remote = DaemonClient(
        'http://localhost:7765',
        pollInterval: const Duration(milliseconds: 1),
        client: MockClient((request) async {
          if (request.url.path == '/active-agent') {
            return http.Response('{"active_agent":"a2"}', 200);
          }
          if (request.url.path == '/utterances') {
            return http.Response('{"utterances":[]}', 200);
          }
          polls++;
          if (polls == 1) return pending.future;
          return http.Response('{"active_agent":"a2"}', 200);
        }),
      );
      final next = remote.watch().first;
      await Future<void>.delayed(Duration.zero);
      await remote.selectAgent('a2');
      pending.complete(http.Response('{"active_agent":"a1"}', 200));
      expect((await next).activeId, 'a2');
      await remote.close();
    },
  );
  test(
    'discard waits for abort consumption and rejects an older daemon',
    () async {
      var count = 0;
      var old = false;
      final remote = DaemonClient(
        'http://localhost:7765',
        client: MockClient((_) async {
          count++;
          return http.Response(
            jsonEncode({
              'recording': false,
              if (!old) 'recording_abort_pending': count == 1,
            }),
            200,
          );
        }),
      );
      await remote.waitForRecordingIdle(discarded: true);
      expect(count, 2);
      old = true;
      await expectLater(
        remote.waitForRecordingIdle(discarded: true),
        throwsA(isA<RecordingCompatibilityException>()),
      );
      await remote.close();
    },
  );

  test(
    'selection honors server alias resolution and rejects absent confirmation',
    () async {
      var valid = true;
      final remote = DaemonClient(
        'http://localhost:7765',
        client: MockClient(
          (_) async => http.Response(
            valid ? '{"active_agent":"canonical-a1"}' : '{}',
            200,
          ),
        ),
      );
      expect(await remote.selectAgent('alias-a1'), 'canonical-a1');
      valid = false;
      await expectLater(remote.selectAgent('alias-a1'), throwsFormatException);
      await remote.close();
    },
  );

  test(
    'reads actual HTTP schemas and posts held boolean without identity leakage',
    () async {
      final calls = <String>[];
      final remote = DaemonClient(
        'http://localhost:7765',
        client: MockClient((request) async {
          calls.add('${request.method} ${request.url.path} ${request.body}');
          return http.Response(
            jsonEncode(
              request.url.path == '/status'
                  ? {
                      'agents': {'a1': 1},
                      'agent_labels': {'a1': 'Lux'},
                      'active_agent': 'a1',
                    }
                  : request.url.path == '/utterances'
                  ? {
                      'utterances': [
                        {'agent': 'a1', 'role': 'user', 'text': 'Hello'},
                      ],
                    }
                  : {'held': true},
            ),
            200,
          );
        }),
      );
      final snapshot = await remote.initial();
      await remote.post('/ptt', {'held': true});
      await remote.post('/active-agent', {'name': 'a1'});
      expect(
        [snapshot.agents.single.name, snapshot.messages.single.text, calls],
        [
          'Lux',
          'Hello',
          [
            'GET /status ',
            'GET /utterances ',
            'POST /ptt {"held":true}',
            'POST /active-agent {"name":"a1"}',
          ],
        ],
      );
      await remote.close();
    },
  );
  test('HTTP command rejection is surfaced', () async {
    final remote = DaemonClient(
      'http://localhost:7765',
      client: MockClient((_) async => http.Response('{}', 409)),
    );
    await expectLater(remote.post('/ptt', {'held': true}), throwsStateError);
    await remote.close();
  });
}
