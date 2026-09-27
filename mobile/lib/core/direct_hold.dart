import 'dart:async';

import 'package:flutter/widgets.dart';

import 'daemon_client.dart';
import 'models.dart';
import 'ptt_lease.dart';

class _Hold {
  _Hold(this.agent, this.priorAgent, this.priorAuto, this.revision);
  final String agent;
  final String? priorAgent;
  final bool priorAuto;
  final int revision;
  bool wanted = true, discard = false, suspendedAuto = false, acquired = false;
}

/// Serializes routing, mode changes and recording. UI never issues these commands separately.
class DirectHold extends ChangeNotifier with WidgetsBindingObserver {
  DirectHold({
    required this.commands,
    required this.selectAgent,
    required this.setAuto,
    required this.waitForIdle,
    required this.onError,
    required Snapshot initial,
  }) : selectedId = initial.activeId,
       auto = initial.auto {
    lease = PttLease(
      commands,
      observeLifecycle: false,
      onFailure: () => interrupt(
        'Connection lost while recording. Discard could not be confirmed.',
      ),
    );
    WidgetsBinding.instance.addObserver(this);
  }
  final DaemonCommands commands;
  final Future<String?> Function(String) selectAgent;
  final Future<void> Function(bool) setAuto;
  final Future<void> Function({required bool discarded}) waitForIdle;
  final ValueChanged<String> onError;
  late final PttLease lease;
  String? selectedId;
  bool auto, connected = true;
  int _queued = 0;
  bool get busy => _queued > 0;
  String? get heldAgentId =>
      _hold?.wanted == true && _hold?.acquired == true ? _hold!.agent : null;
  String? get pendingAgentId => _hold?.wanted == true ? _hold!.agent : null;
  bool get holding => _hold != null;
  _Hold? _hold;
  int _revision = 0;
  bool _disposed = false;
  Future<void> _tail = Future.value();

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  Future<void> _queue(Future<void> Function() action) {
    _queued++;
    _notify();
    return _tail = _tail.then((_) async {
      try {
        await action();
      } catch (_) {
        connected = false;
        _hold?.wanted = false;
        onError(
          'Could not confirm the desktop command. Recording stopped; reconnect before trying again.',
        );
      } finally {
        _queued--;
        _notify();
      }
    });
  }

  Future<void> start(String agent) {
    if (!connected || _disposed || _hold != null || busy) return Future.value();
    final hold = _Hold(agent, selectedId, auto, _revision);
    _hold = hold;
    return _queue(() async {
      try {
        if (hold.priorAuto) {
          await setAuto(false);
          hold.suspendedAuto = true;
          auto = false;
          await commands.post('/abort-recording', {});
          await waitForIdle(discarded: true);
        }
        if (!_canStart(hold)) return;
        final confirmed = await selectAgent(agent);
        if (confirmed != agent) throw StateError('Recipient was not confirmed');
        selectedId = confirmed;
        if (!_canStart(hold)) return;
        hold.acquired = await lease.start();
        if (!hold.acquired) throw StateError('Recording was not started');
      } catch (_) {
        hold.wanted = false;
        hold.discard = true;
        await _cleanup(hold, restore: false);
        rethrow;
      }
    });
  }

  bool _canStart(_Hold hold) =>
      !_disposed &&
      connected &&
      hold.wanted &&
      _hold == hold &&
      hold.revision == _revision;

  Future<void> finish({required bool discard, bool restore = true}) {
    final hold = _hold;
    if (hold == null) return Future.value();
    hold.wanted = false;
    hold.discard |= discard;
    _notify();
    return _queue(() => _cleanup(hold, restore: restore));
  }

  Future<void> _cleanup(_Hold hold, {required bool restore}) async {
    if (_hold != hold) return;
    try {
      await lease.stop(discard: hold.discard);
      if (hold.acquired) await waitForIdle(discarded: hold.discard);
      if (restore &&
          connected &&
          !_disposed &&
          hold.revision == _revision &&
          hold.priorAuto &&
          hold.priorAgent != null &&
          hold.suspendedAuto) {
        if (hold.priorAgent != null) {
          final confirmed = await selectAgent(hold.priorAgent!);
          if (confirmed != hold.priorAgent)
            throw StateError('Original recipient was not restored');
          selectedId = confirmed;
        }
        if (connected && !_disposed && hold.revision == _revision) {
          await setAuto(true);
          auto = true;
        }
      }
    } finally {
      if (_hold == hold) _hold = null;
    }
  }

  Future<void> select(String id) {
    if (!connected || _disposed) return Future.value();
    _revision++;
    final hold = _hold;
    if (hold != null) {
      hold.wanted = false;
      hold.discard = true;
    }
    return _queue(() async {
      if (hold != null) await _cleanup(hold, restore: false);
      if (!connected || _disposed) return;
      final confirmed = await selectAgent(id);
      if (confirmed != id) throw StateError('Recipient was not confirmed');
      selectedId = id;
    });
  }

  Future<void> changeMode(bool value) {
    if (!connected || _disposed) return Future.value();
    _revision++;
    final hold = _hold;
    if (hold != null) {
      hold.wanted = false;
      hold.discard = true;
    }
    return _queue(() async {
      if (hold != null) await _cleanup(hold, restore: false);
      if (!connected || _disposed) return;
      await setAuto(value);
      auto = value;
    });
  }

  void observe(Snapshot snapshot) {
    if (!connected || _disposed || busy) return;
    if (_hold != null) {
      if (snapshot.activeId != _hold!.agent ||
          snapshot.auto ||
          snapshot.muted) {
        _revision++;
        unawaited(finish(discard: true, restore: false));
      }
      return;
    }
    selectedId = snapshot.activeId;
    auto = snapshot.auto;
    _notify();
  }

  void interrupt(String message) {
    connected = false;
    _revision++;
    unawaited(finish(discard: true, restore: false));
    if (!_disposed) onError(message);
    _notify();
  }

  Future<void> close() async {
    connected = false;
    _revision++;
    await finish(discard: true, restore: false);
    await _tail;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      _revision++;
      unawaited(finish(discard: true, restore: false));
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _disposed = true;
    unawaited(close().whenComplete(lease.dispose));
    super.dispose();
  }
}
