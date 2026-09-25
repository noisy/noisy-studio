import 'dart:io';

import 'package:noisy_studio_mobile/core/daemon_client.dart';

/// Read-only protocol smoke check. Never routes, records or plays audio.
Future<void> main(List<String> args) async {
  if (args.length != 1) {
    throw ArgumentError(
      'Usage: dart run tool/check_connection.dart http://host:port',
    );
  }
  final client = DaemonClient(args.single);
  try {
    final initial = await client.initial();
    final streamed = await client.watch().first;
    stdout.writeln(
      'HTTP and WebSocket snapshots decoded successfully. '
      '${initial.agents.length} HTTP / ${streamed.agents.length} streamed conversations.',
    );
  } finally {
    await client.close();
  }
}
