import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

import 'models.dart';

abstract interface class DaemonCommands {
  Future<void> post(String path, Map<String, Object> body);
}

class DaemonClient implements DaemonCommands {
  DaemonClient(String address, {http.Client? client})
    : base = validateAddress(address),
      _http = client ?? http.Client();
  final Uri base;
  final http.Client _http;
  WebSocketChannel? _socket;
  static Uri validateAddress(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.path.isNotEmpty && uri.path != '/') ||
        uri.port >= 65535) {
      throw const FormatException(
        'Enter an HTTP or HTTPS address and port, without a path.',
      );
    }
    return uri;
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await _http
        .get(base.replace(path: path))
        .timeout(const Duration(seconds: 4));
    if (response.statusCode != 200) {
      throw StateError('Desktop returned HTTP ${response.statusCode}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Snapshot> initial() async {
    final results = await Future.wait([_get('/status'), _get('/utterances')]);
    return Snapshot.fromJson({
      'status': results[0],
      'utterances': results[1]['utterances'],
    });
  }

  Stream<Snapshot> watch() async* {
    final socket = WebSocketChannel.connect(
      base.replace(
        scheme: base.scheme == 'https' ? 'wss' : 'ws',
        port: base.port + 1,
        path: '/state',
      ),
    );
    _socket = socket;
    await socket.ready.timeout(const Duration(seconds: 4));
    await for (final data in socket.stream.timeout(
      const Duration(seconds: 6),
    )) {
      final json = jsonDecode(data as String) as Map<String, dynamic>;
      if (json['type'] == 'snapshot') yield Snapshot.fromJson(json);
    }
  }

  @override
  Future<void> post(String path, Map<String, Object> body) async {
    final response = await _http
        .post(
          base.replace(path: path),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 2));
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw StateError('Desktop returned HTTP ${response.statusCode}');
    }
  }

  Future<void> close() async {
    await _socket?.sink.close();
    _http.close();
  }
}
