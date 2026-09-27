import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/daemon_client.dart';
import 'core/direct_hold.dart';
import 'core/message_actions.dart';
import 'core/models.dart';
import 'ui/talk_first.dart';
import 'ui/screens.dart';
import 'l10n/app_localizations.dart';

void main() => runApp(const StudioApp());

class StudioApp extends StatelessWidget {
  const StudioApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'Noisy Studio',
    debugShowCheckedModeBanner: false,
    theme: studioTheme(Brightness.light),
    darkTheme: studioTheme(Brightness.dark),
    themeMode: ThemeMode.dark,
    localizationsDelegates: AppLocalizations.localizationsDelegates,
    supportedLocales: AppLocalizations.supportedLocales,
    home: const Companion(),
  );
}

class Companion extends StatefulWidget {
  const Companion({super.key});
  @override
  State<Companion> createState() => _CompanionState();
}

class _CompanionState extends State<Companion> with WidgetsBindingObserver {
  Snapshot snapshot = const Snapshot();
  final address = TextEditingController();
  DaemonClient? client;
  DirectHold? recording;
  MessageActions? actions;
  StreamSubscription<Snapshot>? subscription;
  bool demo = false, connected = false, busy = false;
  String? demoHeld, error;
  int generation = 0, resetToken = 0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    SharedPreferences.getInstance().then((prefs) {
      if (mounted) address.text = prefs.getString('daemonAddress') ?? '';
    });
  }

  void refresh() {
    if (mounted) setState(() {});
  }

  Future<void> disconnect() async {
    generation++;
    resetToken++;
    actions?.dispose();
    actions = null;
    final previous = recording;
    final previousSubscription = subscription;
    final previousClient = client;
    recording = null;
    subscription = null;
    client = null;
    previous?.removeListener(refresh);
    await previousSubscription?.cancel();
    await previous?.close();
    previous?.dispose();
    await previousClient?.close();
  }

  void showError(String message) {
    if (!mounted) return;
    error = message;
    connected = false;
    resetToken++;
    refresh();
  }

  Future<void> connect() async {
    if (busy) return;
    setState(() {
      busy = true;
      connected = false;
      error = null;
    });
    final closing = disconnect();
    final current = generation;
    await closing;
    if (!mounted || current != generation) return;
    try {
      final remote = DaemonClient(address.text);
      client = remote;
      final initial = await remote.initial();
      if (!mounted || current != generation) return;
      snapshot = initial;
      actions = MessageActions(
        request: remote.request,
        onError: (message) {
          if (mounted && current == generation) {
            ScaffoldMessenger.of(context)
                .showSnackBar(SnackBar(content: Text(message)));
          }
        },
      )..playingId = initial.playingId;
      actions!.addListener(refresh);
      recording = DirectHold(
        commands: remote,
        selectAgent: remote.selectAgent,
        setAuto: remote.setAuto,
        waitForIdle: remote.waitForRecordingIdle,
        initial: initial,
        onError: (message) {
          if (current == generation) showError(message);
        },
      )..addListener(refresh);
      demo = false;
      connected = true;
      subscription = remote.watch().listen(
        (next) {
          if (!mounted || current != generation) return;
          actions?.playingId = next.playingId;
          recording?.observe(next);
          snapshot = next;
          refresh();
        },
        onError: (Object cause) {
          if (mounted && current == generation) lost(cause);
        },
        onDone: () {
          if (mounted && current == generation && connected) lost();
        },
      );
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('daemonAddress', address.text.trim());
    } catch (cause) {
      if (!mounted || current != generation) return;
      showError(
        cause is DaemonAccessException ? cause.toString() : 'Could not connect. Check the address and that your desktop is reachable.',
      );
    } finally {
      if (mounted && current == generation) setState(() => busy = false);
    }
  }

  void lost([Object? cause]) {
    final message = cause is DaemonAccessException
        ? cause.toString()
        : 'Connection lost. Recording stopped. Reconnect in Settings.';
    recording?.interrupt(message);
    showError(message);
  }

  void updateDemo({String? selected, bool? auto, bool? muted}) {
    snapshot = Snapshot(
      agents: snapshot.agents,
      messages: snapshot.messages,
      activeId: selected ?? snapshot.activeId,
      auto: auto ?? snapshot.auto,
      muted: muted ?? snapshot.muted,
    );
    refresh();
  }

  Future<void> pauseAuto() async {
    if (demo) {
      updateDemo(muted: !snapshot.muted);
      return;
    }
    if (!connected || client == null || recording == null) return;
    final current = generation;
    try {
      await recording!.finish(discard: true, restore: false);
      await client!.post('/mute', {'muted': !snapshot.muted});
    } catch (cause) {
      if (current == generation) lost(cause);
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      demoHeld = null;
      resetToken++;
      refresh();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    unawaited(disconnect());
    address.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    ValueChanged<Message>? handler(MessageAction action) =>
        !demo && connected && actions != null && !actions!.busy
        ? (message) => actions?.perform(action, message)
        : null;
    final ready = connected && (demo || recording?.connected == true);
    return TalkFirstView(
      agents: snapshot.agents.map(TalkAgent.fromAgent).toList(),
      messages: snapshot.messages,
      selectedId: demo ? snapshot.activeId : recording?.displaySelectedId,
      auto: demo ? snapshot.auto : recording?.displayAuto ?? snapshot.auto,
      enabled:
          ready &&
          (demo || recording?.busy != true && recording?.holding != true) &&
          !snapshot.muted,
      recordingId: demo ? demoHeld : recording?.heldAgentId,
      resetToken: (generation, resetToken, recording?.resetToken),
      paused: snapshot.muted,
      onPause: ready && recording?.busy != true && recording?.holding != true
          ? pauseAuto
          : null,
      notice:
          error ??
          (demo
              ? 'Demo · no audio is recorded'
              : connected
              ? 'Controls your desktop microphone and speakers'
              : 'Connect your desktop in Settings'),
      onSelect: (id) {
        if (demo) {
          updateDemo(selected: id);
        } else {
          unawaited(recording?.select(id));
        }
      },
      onMode: (value) {
        if (demo) {
          updateDemo(auto: value);
        } else {
          unawaited(recording?.changeMode(value));
        }
      },
      onHold: (id) {
        if (demo) {
          setState(() => demoHeld = id);
        } else {
          unawaited(recording?.start(id));
        }
      },
      onFinish: (discard) {
        if (demo) {
          setState(() => demoHeld = null);
        } else {
          unawaited(recording?.finish(discard: discard));
        }
      },
      onReplay: handler(MessageAction.replay),
      onRecall: handler(MessageAction.cancel),
      onPauseSpeech: ready && !demo && actions?.busy == false
          ? (_) => actions?.playback(togglePause: true)
          : null,
      onSkip: ready && !demo && actions?.busy == false
          ? (_) => actions?.playback(togglePause: false)
          : null,
      pausedMessageId: actions?.pausedId ?? 0,
      settings: ConnectionSettings(
        address: address,
        busy: busy,
        error: error,
        onConnect: connect,
        onDemo: () async {
          final closing = disconnect();
          final current = generation;
          await closing;
          if (!mounted || current != generation) return;
          setState(() {
            demo = true;
            connected = true;
            busy = false;
            error = null;
            snapshot = fixture();
          });
        },
      ),
    );
  }
}
