import 'package:flutter/foundation.dart';

/// Serializes routing changes and publishes only the latest server confirmation.
/// Each instance belongs to one connection; disposal invalidates pending work.
class AgentSelection extends ChangeNotifier {
  AgentSelection({
    required this.stopRecording,
    required this.request,
    required this.onConfirmed,
    required this.onFailure,
  });
  final Future<void> Function() stopRecording;
  final Future<String?> Function(String) request;
  final ValueChanged<String?> onConfirmed;
  final VoidCallback onFailure;
  Future<void> _tail = Future.value();
  int _revision = 0;
  bool _disposed = false;
  bool pending = false;

  Future<void> select(String id) {
    if (_disposed) return Future.value();
    final revision = ++_revision;
    pending = true;
    notifyListeners();
    // Capture the queue before replacing it. A newer request cannot overtake an
    // in-flight HTTP command and change the daemon back to an older selection.
    return _tail = _tail.then((_) async {
      if (!_current(revision)) return;
      try {
        await stopRecording();
        if (!_current(revision)) return;
        final confirmed = await request(id);
        if (_current(revision)) onConfirmed(confirmed);
      } catch (_) {
        if (_current(revision)) onFailure();
      } finally {
        if (_current(revision)) {
          pending = false;
          notifyListeners();
        }
      }
    });
  }

  bool _current(int revision) => !_disposed && revision == _revision;

  @override
  void dispose() {
    _disposed = true;
    _revision++;
    super.dispose();
  }
}
