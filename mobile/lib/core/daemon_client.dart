import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

abstract interface class DaemonCommands {
  Future<void> post(String path, Map<String, Object> body);
}

class DaemonAccessException implements Exception {
  const DaemonAccessException(this.status);
  final int status;
  @override
  String toString() =>
      'Access denied (HTTP $status). This address requires authentication for this client before reconnecting.';
}

class DaemonClient implements DaemonCommands {
  DaemonClient(
    String address, {
    http.Client? client,
    this.pollInterval = const Duration(seconds: 1),
  }) : base = validateAddress(address),
       _http = client ?? http.Client();
  final Uri base;
  final http.Client _http;
  final Duration pollInterval;
  bool _closed = false;
  StreamController<Snapshot>? _updates;
  Timer? _pollTimer;
  static Uri validateAddress(String value) {
    final uri = Uri.tryParse(value.trim());
    if (uri == null ||
        !['http', 'https'].contains(uri.scheme) ||
        uri.host.isEmpty ||
        uri.userInfo.isNotEmpty ||
        uri.hasQuery ||
        uri.hasFragment ||
        (uri.path.isNotEmpty && uri.path != '/') ||
        uri.port > 65535) {
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
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw DaemonAccessException(response.statusCode);
    }
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

  /// Polls only the supplied origin. No guessed WS port or tunnel configuration.
  /// Each cycle completes before the next is scheduled; cancellation stops scheduling.
  Stream<Snapshot> watch() {
    if (_closed) throw StateError('Connection closed');
    if (_updates != null) throw StateError('Already watching this connection');
    var cancelled = false;
    late final StreamController<Snapshot> controller;
    Future<void> poll() async {
      if (_closed || cancelled) return;
      try {
        final snapshot = await initial();
        if (_closed || cancelled) return;
        controller.add(snapshot);
        _pollTimer = Timer(pollInterval, poll);
      } catch (error, stack) {
        if (!_closed && !cancelled) {
          controller.addError(error, stack);
          unawaited(controller.close());
        }
      }
    }

    controller = StreamController<Snapshot>(
      onListen: poll,
      onCancel: () {
        cancelled = true;
        _pollTimer?.cancel();
      },
    );
    _updates = controller;
    return controller.stream;
  }

  Future<String?> selectAgent(String id) async {
    final result = await request('/active-agent', {'name': id});
    if (!result.containsKey('active_agent') ||
        (result['active_agent'] != null && result['active_agent'] is! String)) {
      throw const FormatException('Missing active-agent confirmation');
    }
    return result['active_agent'] as String?;
  }

  @override
  Future<void> post(String path, Map<String, Object> body) async {
    await request(path, body);
  }

  Future<Map<String, dynamic>> request(
    String path,
    Map<String, Object> body,
  ) async {
    final response = await _http
        .post(
          base.replace(path: path),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(const Duration(seconds: 2));
    if (response.statusCode == 401 || response.statusCode == 403) {
      throw DaemonAccessException(response.statusCode);
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw StateError('Desktop returned HTTP ${response.statusCode}');
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<void> close() async {
    _closed = true;
    _pollTimer?.cancel();
    _http.close();
    unawaited(_updates?.close());
  }
}
