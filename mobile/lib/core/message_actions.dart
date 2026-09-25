import 'package:flutter/foundation.dart';

import 'models.dart';

enum MessageAction { replay, pause, skip, cancel }

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

  Future<void> perform(MessageAction action, Message message) async {
    if (_disposed || busy || message.id <= 0) return;
    if ((action == MessageAction.pause || action == MessageAction.skip) &&
        message.id != _playingId) {
      onError('This message is no longer playing.');
      return;
    }
    busy = true;
    notifyListeners();
    try {
      switch (action) {
        case MessageAction.replay:
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
          if (result['queued'] != true && result['skipped'] != true)
            throw StateError('Replay was not accepted.');
        case MessageAction.pause:
          final result = await request('/playback-pause', {});
          if (result['paused'] is! bool)
            throw StateError('Playback state was not confirmed.');
          if (!_disposed && _playingId == message.id)
            paused = result['paused'] as bool;
        case MessageAction.skip:
          final result = await request('/interrupt', {});
          if (result['stopped'] != true)
            throw StateError('Stop was not confirmed.');
          if (!_disposed && _playingId == message.id) paused = false;
        case MessageAction.cancel:
          final result = await request('/cancel', {'utterance_id': message.id});
          if (result['cancelled'] != true)
            throw StateError('This message can no longer be recalled.');
      }
    } catch (_) {
      if (!_disposed)
        onError(
          'Could not ${action.name} this message. Refreshing state may show that it has already changed.',
        );
    } finally {
      if (!_disposed) {
        busy = false;
        notifyListeners();
      }
    }
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
