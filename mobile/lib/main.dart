import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/daemon_client.dart';
import 'core/agent_selection.dart';
import 'core/models.dart';
import 'core/ptt_lease.dart';
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
  Snapshot snapshot = fixture();
  final address = TextEditingController();
  DaemonClient? client;
  PttLease? lease;
  AgentSelection? selection;
  StreamSubscription<Snapshot>? subscription;
  bool demo = true, connected = true, busy = false, demoHeld = false;
  String? error;
  int tab = 0, generation = 0;
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
    selection?.dispose();
    selection = null;
    final previousLease = lease;
    final previousSubscription = subscription;
    final previousClient = client;
    lease = null;
    subscription = null;
    client = null;
    await previousLease?.stop();
    previousLease?.dispose();
    await previousSubscription?.cancel();
    await previousClient?.close();
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
      demo = false;
      connected = true;
      void connectionLost() {
        if (mounted && current == generation) lost();
      }

      final connectionLease = PttLease(remote, onFailure: connectionLost)
        ..addListener(refresh);
      lease = connectionLease;
      selection = AgentSelection(
        stopRecording: connectionLease.stop,
        request: remote.selectAgent,
        onConfirmed: (id) {
          if (mounted && current == generation) applySelection(id);
        },
        onFailure: connectionLost,
      )..addListener(refresh);
      subscription = remote.watch().listen(
        (next) {
          if (!mounted || current != generation) return;
          if (next.activeId != snapshot.activeId || next.auto || next.muted) {
            unawaited(lease?.stop());
          }
          snapshot = next;
          refresh();
        },
        onError: (Object _) => connectionLost(),
        onDone: connectionLost,
      );
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('daemonAddress', address.text.trim());
    } catch (_) {
      if (!mounted || current != generation) return;
      error = 'Could not connect. Check the address and that your desktop is reachable.';
      connected = false;
    } finally {
      if (mounted && current == generation) setState(() => busy = false);
    }
  }

  void lost() {
    selection?.dispose();
    selection = null;
    unawaited(lease?.stop());
    connected = false;
    error = 'Connection lost. Recording stopped. Reconnect in Settings.';
    refresh();
  }

  Future<bool> command(String path, Map<String, Object> body) async {
    if (demo) return true;
    final current = generation;
    try {
      await client?.post(path, body);
      return mounted && current == generation;
    } catch (_) {
      if (mounted && current == generation) lost();
      return false;
    }
  }

  Future<void> select(Agent agent) async {
    if (!connected) return;
    if (demo) {
      release();
      applySelection(agent.id);
    } else {
      await selection?.select(agent.id);
    }
  }

  void applySelection(String? confirmedId) {
    setState(() {
      snapshot = Snapshot(
        agents: snapshot.agents,
        messages: snapshot.messages,
        activeId: confirmedId,
        muted: snapshot.muted,
        auto: snapshot.auto,
        recording: snapshot.recording,
      );
      tab = 1;
    });
  }

  void release() {
    demoHeld = false;
    unawaited(lease?.stop());
    refresh();
  }

  void hold() {
    if (!connected || selection?.pending == true) return;
    if (demo) {
      demoHeld = true;
      refresh();
    } else {
      unawaited(lease?.start());
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) release();
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
    final agent = snapshot.agents
        .where((a) => a.id == snapshot.activeId)
        .firstOrNull;
    final pages = [
      AgentsView(snapshot: snapshot, onSelect: select),
      TalkView(
        snapshot: snapshot,
        agent: agent,
        connected: connected && selection?.pending != true,
        held: demo ? demoHeld : lease?.held == true,
        onHold: hold,
        onRelease: release,
        onToggle: () =>
            (demo ? demoHeld : lease?.held == true) ? release() : hold(),
        onAuto: (value) async {
          release();
          if (!await command('/settings', {
            'detection_mode': value ? 'auto' : 'ptt',
          })) {
            return;
          }
          if (demo) {
            snapshot = Snapshot(
              agents: snapshot.agents,
              messages: snapshot.messages,
              activeId: snapshot.activeId,
              muted: snapshot.muted,
              auto: value,
            );
            refresh();
          }
        },
        onMute: () async {
          release();
          if (!await command('/mute', {'muted': !snapshot.muted})) return;
          if (demo) {
            snapshot = Snapshot(
              agents: snapshot.agents,
              messages: snapshot.messages,
              activeId: snapshot.activeId,
              auto: snapshot.auto,
              muted: !snapshot.muted,
            );
            refresh();
          }
        },
        onStop: () => command('/interrupt', {}),
      ),
      MessagesView(messages: snapshot.messages),
      ConnectionSettings(
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
    ];
    return Scaffold(
      appBar: AppBar(
        title: const Text('Noisy Studio'),
        actions: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Chip(
              label: Text(
                demo
                    ? 'DEMO'
                    : connected
                    ? 'CONNECTED'
                    : 'OFFLINE',
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            if (error != null && tab != 3)
              MaterialBanner(
                content: Text(error!),
                actions: [
                  TextButton(
                    onPressed: () => setState(() => tab = 3),
                    child: const Text('Reconnect'),
                  ),
                ],
              ),
            Expanded(child: pages[tab]),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: tab,
        onDestinationSelected: (value) {
          release();
          setState(() => tab = value);
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.grid_view), label: 'Agents'),
          NavigationDestination(icon: Icon(Icons.mic), label: 'Talk'),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            label: 'Recent',
          ),
          NavigationDestination(icon: Icon(Icons.tune), label: 'Settings'),
        ],
      ),
    );
  }
}
