import 'dart:async';

import 'package:flutter/widgets.dart';

import 'daemon_client.dart';

/// Owns renewal and shutdown of one PTT lease. Discard always precedes release.
class PttLease extends ChangeNotifier with WidgetsBindingObserver {
  PttLease(
    this.commands, {
    this.interval = const Duration(milliseconds: 500),
    this.onFailure,
    this.observeLifecycle = true,
  }) {
    if (observeLifecycle) WidgetsBinding.instance.addObserver(this);
  }
  final DaemonCommands commands;
  final Duration interval;
  final VoidCallback? onFailure;
  final bool observeLifecycle;
  Timer? _timer;
  Future<void> _pending = Future.value();
  Future<void>? _stopping;
  bool held = false, _disposed = false, _discard = false;

  Future<bool> start() async {
    if (_stopping != null || held || _disposed) return false;
    _discard = false;
    held = true;
    notifyListeners();
    await _renew();
    return held && !_disposed;
  }

  Future<void> _renew() async {
    if (!held || _disposed) return;
    _pending = commands.post('/ptt', {'held': true});
    try {
      await _pending;
    } catch (_) {
      try {
        await stop(discard: true);
      } catch (_) {
        /* Surface failure below. */
      }
      onFailure?.call();
      return;
    }
    if (held && !_disposed) _timer = Timer(interval, _renew);
  }

  Future<void> stop({bool discard = false}) {
    _discard |= discard;
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
      /* Still attempt safe cleanup. */
    }
    // If abort cannot be confirmed, do not intentionally release/send or resume Auto.
    if (_discard) await commands.post('/abort-recording', {});
    await commands.post('/ptt', {'held': false});
  }

  Future<void> _cancelQuietly() async {
    try {
      await stop(discard: true);
    } catch (_) {
      onFailure?.call();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) unawaited(_cancelQuietly());
  }

  @override
  void dispose() {
    if (observeLifecycle) WidgetsBinding.instance.removeObserver(this);
    _disposed = true;
    unawaited(_cancelQuietly());
    super.dispose();
  }
}
