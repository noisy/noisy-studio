import 'package:flutter/foundation.dart';

import 'models.dart';

enum MessageAction { replay, cancel }

class MessageActions extends ChangeNotifier {
  MessageActions({required this.request, required this.onError});
  final Future<Map<String, dynamic>> Function(String, Map<String, Object>)
  request;
  final ValueChanged<String> onError;
  bool busy = false, paused = false, _disposed = false;
  int _playingId = 0;
  int get pausedId => paused ? _playingId : 0;
  set playingId(int value) {
    if (value != _playingId) {
      _playingId = value;
      paused = false;
    }
  }

  Future<void> _run(String name, Future<void> Function() operation) async {
    if (_disposed || busy) return;
    busy = true;
    notifyListeners();
    try {
      await operation();
    } catch (_) {
      if (!_disposed)
        onError('Could not $name. The desktop state may have changed.');
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  /// These endpoints act on whatever is playing now, never on a named card.
  Future<void> playback({required bool togglePause}) => _run(
    togglePause ? 'pause or resume speech' : 'stop speech',
    () async {
      final result = await request(
        togglePause ? '/playback-pause' : '/interrupt',
        {},
      );
      if (togglePause ? result['paused'] is! bool : result['stopped'] != true) {
        throw StateError('Playback was not confirmed.');
      }
      if (!_disposed) paused = togglePause ? result['paused'] as bool : false;
    },
  );

  Future<void> perform(MessageAction action, Message message) async {
    if (message.id <= 0) return;
    await _run('${action.name} this message', () async {
      if (action == MessageAction.replay) {
        final text = message.text
            .replaceFirst(RegExp(r'^\[[^\]]+\]\s*'), '')
            .replaceFirst(RegExp(r'^[„"]'), '')
            .replaceFirst(RegExp(r'[”"]$'), '');
        final result = await request('/speak', {
          'text': text,
          'source_id': message.id,
          'agent': message.agentId,
          'wait': false,
          'card': false,
          'interrupt': true,
        });
        if (result['queued'] != true && result['skipped'] != true) {
          throw StateError('Replay was not accepted.');
        }
      } else {
        final result = await request('/cancel', {'utterance_id': message.id});
        if (result['cancelled'] != true) {
          throw StateError('This message can no longer be recalled.');
        }
      }
    });
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
