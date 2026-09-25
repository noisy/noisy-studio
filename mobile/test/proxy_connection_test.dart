import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:noisy_studio_mobile/core/daemon_client.dart';
import 'package:noisy_studio_mobile/core/ptt_lease.dart';

class RealHttpOverrides extends HttpOverrides {}

class ProxyFixture {
  late HttpServer backend, proxy;
  final forwarder = http.Client();
  final paths = <String>[];
  final holds = <bool>[];
  String active = 'a1';
  int denied = 0;
  bool failRenewal = false;
  String get address => 'http://127.0.0.1:${proxy.port}';
  Future<void> start() async {
    backend = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    backend.listen((request) async {
      final body = request.method == 'POST'
          ? jsonDecode(await utf8.decoder.bind(request).join())
                as Map<String, dynamic>
          : <String, dynamic>{};
      var result = <String, dynamic>{};
      if (request.uri.path == '/status') {
        result = {
          'agents': {active: 1},
          'active_agent': active,
        };
      }
      if (request.uri.path == '/utterances') {
        result = {'utterances': []};
      }
      if (request.uri.path == '/active-agent') {
        active = body['name'] as String;
        result = {'active_agent': active};
      }
      if (request.uri.path == '/ptt') {
        holds.add(body['held'] as bool);
        if (failRenewal && body['held'] == true) {
          request.response.statusCode = 503;
        }
        result = {'held': body['held']};
      }
      request.response.headers.contentType = ContentType.json;
      request.response.write(jsonEncode(result));
      await request.response.close();
    });
    proxy = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    proxy.listen((request) async {
      paths.add(request.uri.path);
      if (denied != 0) {
        request.response.statusCode = denied;
        await request.response.close();
        return;
      }
      final target = Uri.parse(
        'http://127.0.0.1:${backend.port}${request.uri.path}',
      );
      final outgoing = http.Request(request.method, target)
        ..body = await utf8.decoder.bind(request).join();
      outgoing.headers['Content-Type'] = 'application/json';
      final response = await forwarder.send(outgoing);
      request.response.statusCode = response.statusCode;
      await request.response.addStream(response.stream);
      await request.response.close();
    });
  }

  Future<void> close() async {
    forwarder.close();
    await proxy.close(force: true);
    await backend.close(force: true);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
    'one proxy origin supports state commands cancellation and explicit reconnect',
    () => HttpOverrides.runWithHttpOverrides(() async {
      final fixture = ProxyFixture();
      await fixture.start();
      final remote = DaemonClient(
        fixture.address,
        pollInterval: const Duration(milliseconds: 20),
      );
      try {
        expect((await remote.initial()).activeId, 'a1');
        expect(await remote.selectAgent('a2'), 'a2');
        expect((await remote.watch().first).activeId, 'a2');
        final before = fixture.paths.length;
        await Future<void>.delayed(const Duration(milliseconds: 70));
        expect(fixture.paths.length, before);
        await remote.close();
        final reconnected = DaemonClient(fixture.address);
        expect((await reconnected.initial()).activeId, 'a2');
        expect(fixture.holds, isEmpty);
        expect(
          fixture.paths.every(
            (path) =>
                ['/status', '/utterances', '/active-agent'].contains(path),
          ),
          isTrue,
        );
        await reconnected.close();
      } finally {
        await remote.close();
        await fixture.close();
      }
    }, RealHttpOverrides()),
  );
  test(
    'proxy renewal failure releases PTT and never silently resumes',
    () => HttpOverrides.runWithHttpOverrides(() async {
      final fixture = ProxyFixture();
      await fixture.start();
      final remote = DaemonClient(fixture.address);
      final failed = Completer<void>();
      final lease = PttLease(
        remote,
        interval: const Duration(milliseconds: 20),
        onFailure: () => failed.complete(),
      );
      try {
        await lease.start();
        fixture.failRenewal = true;
        await failed.future.timeout(const Duration(seconds: 3));
        await Future<void>.delayed(const Duration(milliseconds: 80));
        expect(
          [lease.held, fixture.holds],
          [
            false,
            [true, true, false],
          ],
        );
      } finally {
        lease.dispose();
        await remote.close();
        await fixture.close();
      }
    }, RealHttpOverrides()),
  );
  test(
    'proxy authentication denial stays distinguishable for initial and streamed state',
    () => HttpOverrides.runWithHttpOverrides(() async {
      final fixture = ProxyFixture();
      await fixture.start();
      fixture.denied = 401;
      final remote = DaemonClient(fixture.address);
      try {
        await expectLater(
          remote.initial(),
          throwsA(isA<DaemonAccessException>()),
        );
        fixture.denied = 403;
        await expectLater(
          remote.watch().first,
          throwsA(
            isA<DaemonAccessException>().having(
              (error) => error.status,
              'status',
              403,
            ),
          ),
        );
      } finally {
        await remote.close();
        await fixture.close();
      }
    }, RealHttpOverrides()),
  );
  test('HTTPS requests retain exactly the supplied origin and never invent port444', () async {
    final origins = <String>[];
    final client = DaemonClient(
      'https://desktop.example',
      client: MockClient((request) async {
        origins.add(request.url.origin);
        return http.Response(
          jsonEncode(
            request.url.path == '/status'
                ? {'agents': <String, int>{}}
                : {'utterances': []},
          ),
          200,
        );
      }),
    );
    await client.initial();
    await client.watch().first;
    await client.close();
    expect(origins, List.filled(4, 'https://desktop.example'));
  });
}
