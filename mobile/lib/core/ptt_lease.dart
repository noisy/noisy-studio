import 'dart:async';

import 'package:flutter/widgets.dart';

import 'daemon_client.dart';

/// Owns one local hold. Serializes renewal/release so a late start cannot outlive cancellation.
class PttLease extends ChangeNotifier with WidgetsBindingObserver {
  PttLease(
    this.commands, {
    this.interval = const Duration(milliseconds: 500),
    this.onFailure,
  }) {
    WidgetsBinding.instance.addObserver(this);
  }
  final DaemonCommands commands;
  final Duration interval;
  final VoidCallback? onFailure;
  Timer? _timer;
  Future<void> _pending = Future.value();
  Future<void>? _stopping;
  bool held = false;
  bool _disposed = false;
  Future<void> start() async {
    if (_stopping != null || held || _disposed) return;
    held = true;
    notifyListeners();
    await _renew();
  }

  Future<void> _renew() async {
    if (!held || _disposed) return;
    _pending = commands.post('/ptt', {'held': true});
    try {
      await _pending;
    } catch (_) {
      if (held) {
        held = false;
        if (!_disposed) notifyListeners();
        onFailure?.call();
        try {
          await commands.post('/ptt', {'held': false});
        } catch (_) {
          /* Server lease expires if unreachable. */
        }
      }
      return;
    }
    if (held && !_disposed) _timer = Timer(interval, _renew);
  }

  Future<void> stop() {
    return _stopping ??= _stop().whenComplete(() => _stopping = null);
  }

  Future<void> _stop() async {
    final wasHeld = held;
    held = false;
    _timer?.cancel();
    if (wasHeld && !_disposed) notifyListeners();
    if (!wasHeld) return;
    try {
      await _pending;
    } catch (_) {
      /* Release even after a failed renewal. */
    }
    try {
      await commands.post('/ptt', {'held': false});
    } catch (_) {
      /* Server lease expires if unreachable. */
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) unawaited(stop());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _disposed = true;
    unawaited(stop());
    super.dispose();
  }
}
