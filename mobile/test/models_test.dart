import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/core/daemon_client.dart';

void main() {
  test('snapshot keeps identity internal and placeholder cards', () {
    final s = Snapshot.fromJson({
      'status': {
        'agents': {'a1': 1},
        'active_agent': 'a1',
        'muted': true,
        'detection_mode': 'auto',
      },
      'utterances': [
        {'agent': 'a1', 'role': 'user', 'text': '', 'status': 'transcribing'},
      ],
    });
    expect(
      [
        s.agents.single.name,
        s.messages.single.text,
        s.activeId,
        s.muted,
        s.auto,
      ],
      ['New conversation', 'transcribing', 'a1', true, true],
    );
  });
  test('addresses require an origin without credentials', () {
    for (final v in [
      'file:///tmp/socket',
      'http://user:pass@localhost',
      'http://host/path',
      'http://host:65536',
    ]) {
      expect(() => DaemonClient.validateAddress(v), throwsFormatException);
    }
    expect(DaemonClient.validateAddress('http://localhost:7765').port, 7765);
  });
}
