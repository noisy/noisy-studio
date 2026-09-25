import 'dart:async';

import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'core/daemon_client.dart';
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
    await lease?.stop();
    lease?.dispose();
    lease = null;
    await subscription?.cancel();
    subscription = null;
    await client?.close();
    client = null;
  }

  Future<void> connect() async {
    if (busy) return;
    setState(() {
      busy = true;
      connected = false;
      error = null;
    });
    await disconnect();
    final current = generation;
    try {
      final remote = DaemonClient(address.text);
      client = remote;
      final initial = await remote.initial();
      if (!mounted || current != generation) return;
      snapshot = initial;
      demo = false;
      connected = true;
      lease = PttLease(remote, onFailure: lost)..addListener(refresh);
      subscription = remote.watch().listen(
        (next) {
          if (next.activeId != snapshot.activeId || next.auto || next.muted) {
            unawaited(lease?.stop());
          }
          snapshot = next;
          refresh();
        },
        onError: (Object _) => lost(),
        onDone: lost,
      );
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('daemonAddress', address.text.trim());
    } catch (_) {
      error = 'Could not connect. Check the address and that your desktop is reachable.';
      connected = false;
    } finally {
      if (mounted && current == generation) setState(() => busy = false);
    }
  }

  void lost() {
    unawaited(lease?.stop());
    connected = false;
    error = 'Connection lost. Recording stopped. Reconnect in Settings.';
    refresh();
  }

  Future<void> command(String path, Map<String, Object> body) async {
    if (demo) return;
    try {
      await client?.post(path, body);
    } catch (_) {
      lost();
    }
  }

  Future<void> select(Agent agent) async {
    await lease?.stop();
    if (!demo) await command('/active-agent', {'name': agent.id});
    if (!mounted) return;
    setState(() {
      snapshot = Snapshot(
        agents: snapshot.agents,
        messages: snapshot.messages,
        activeId: agent.id,
        muted: snapshot.muted,
        auto: snapshot.auto,
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
        connected: connected,
        held: demo ? demoHeld : lease?.held == true,
        onHold: hold,
        onRelease: release,
        onToggle: () =>
            (demo ? demoHeld : lease?.held == true) ? release() : hold(),
        onAuto: (value) async {
          release();
          await command('/settings', {
            'detection_mode': value ? 'auto' : 'ptt',
          });
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
          await command('/mute', {'muted': !snapshot.muted});
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
          await disconnect();
          if (!mounted) return;
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
