import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:noisy_studio_mobile/core/daemon_client.dart';

void main() {
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
