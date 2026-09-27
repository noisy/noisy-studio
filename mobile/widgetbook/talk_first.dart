import 'package:flutter/material.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/screens.dart' show MessageCard;
import 'package:noisy_studio_mobile/ui/voice_avatar.dart';

const _crew = [
  (name: 'Lux', topic: 'Release review', voice: 'lux'),
  (name: 'Atlas', topic: 'Mobile companion', voice: 'atlas'),
  (name: 'Iris', topic: 'Design exploration', voice: 'iris'),
  (name: 'Orion', topic: 'Audio checks', voice: 'orion'),
];
const _messages = [
  Message(
    'a1',
    'You → Lux',
    'Could you review the latest changes?',
    id: 1,
    role: 'user',
    status: 'delivered',
    time: '14:30',
  ),
  Message(
    'a3',
    'Iris',
    'The portrait layout is ready. I kept the screen focused on your crew.',
    id: 2,
    voice: 'iris',
    status: 'played',
    time: '14:31',
  ),
  Message(
    'a1',
    'Lux',
    'The checks look good. I’m reviewing the small-screen layout next.',
    id: 3,
    voice: 'lux',
    status: 'played',
    time: '14:32',
  ),
  Message(
    'a2',
    'Atlas',
    'Hold an agent to talk directly. A quick tap opens the conversation.',
    id: 4,
    voice: 'atlas',
    status: 'played',
    time: '14:33',
  ),
  Message(
    'a3',
    'You → Iris',
    'Great, let’s try it with the whole crew.',
    id: 5,
    role: 'user',
    status: 'delivered',
    time: '14:34',
  ),
  Message(
    'a3',
    'Iris',
    'Ready when you are.',
    id: 6,
    voice: 'iris',
    status: 'played',
    time: '14:35',
  ),
];

/// Synthetic local interactions; no microphone, transport or persistent state.
class TalkFirstPreview extends StatefulWidget {
  const TalkFirstPreview({
    super.key,
    this.initialTab = 0,
    this.initialDetail,
    this.initialAuto = false,
  });
  final int initialTab;
  final int? initialDetail;
  final bool initialAuto;
  @override
  State<TalkFirstPreview> createState() => _TalkFirstPreviewState();
}

class _TalkFirstPreviewState extends State<TalkFirstPreview> {
  late bool auto = widget.initialAuto;
  late int tab = widget.initialTab;
  late int selected = widget.initialDetail ?? 0;
  late int? detail = widget.initialDetail;
  int? held;
  bool paused = false;
  String? feedback;

  void openDetail(int index) => setState(() {
    detail = index;
    selected = index;
    feedback = null;
  });
  void startHold(int index) => setState(() {
    held = index;
    feedback = null;
  });
  void finishHold(bool cancelled) {
    if (held == null) return;
    setState(() {
      feedback = cancelled
          ? 'Recording preview cancelled'
          : 'Preview sent to ${_crew[held!].name}';
      held = null;
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      leading: detail == null
          ? null
          : IconButton(
              onPressed: () => setState(() => detail = null),
              icon: const Icon(Icons.arrow_back),
              tooltip: 'Back',
            ),
      title: Text(detail == null ? 'Noisy Studio' : _crew[detail!].name),
      actions: [_mode(), const SizedBox(width: 12)],
    ),
    body: detail != null
        ? _detail(detail!)
        : tab == 1
        ? _recent()
        : tab == 2
        ? const Center(child: Text('Connection and preferences'))
        : _agents(),
    bottomNavigationBar: NavigationBar(
      selectedIndex: tab,
      onDestinationSelected: (value) => setState(() {
        tab = value;
        detail = null;
        held = null;
      }),
      destinations: const [
        NavigationDestination(
          icon: Icon(Icons.people_outline),
          label: 'Agents',
        ),
        NavigationDestination(
          icon: Icon(Icons.forum_outlined),
          label: 'Recent',
        ),
        NavigationDestination(icon: Icon(Icons.tune), label: 'Settings'),
      ],
    ),
  );

  Widget _mode() => SegmentedButton<bool>(
    showSelectedIcon: false,
    style: ButtonStyle(
      visualDensity: VisualDensity.compact,
      padding: const WidgetStatePropertyAll(
        EdgeInsets.symmetric(horizontal: 9),
      ),
      minimumSize: const WidgetStatePropertyAll(Size(40, 32)),
      textStyle: const WidgetStatePropertyAll(
        TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
      ),
    ),
    segments: const [
      ButtonSegment(
        value: false,
        label: Text('Push to talk'),
        tooltip: 'Push to talk',
      ),
      ButtonSegment(
        value: true,
        label: Text('Auto'),
        tooltip: 'Automatic turn detection',
      ),
    ],
    selected: {auto},
    onSelectionChanged: (values) => setState(() {
      auto = values.first;
      held = null;
      feedback = null;
    }),
  );

  Widget _status({bool crew = false}) {
    if (crew && !auto) return const SizedBox.shrink();
    if (held == null && !auto && feedback == null) {
      return const SizedBox.shrink();
    }
    final text = !crew && held != null
        ? 'Recording → ${_crew[held!].name} · drag away to cancel'
        : auto
        ? '${paused ? 'Auto paused' : 'Auto listening'} → ${_crew[selected].name}'
        : feedback ?? '';
    return Container(
      margin: const EdgeInsets.symmetric(vertical: 12),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primary.withValues(alpha: .08),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          const Icon(Icons.mic_none, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(text, style: const TextStyle(fontSize: 12))),
          if (auto && (held == null || crew))
            IconButton(
              visualDensity: VisualDensity.compact,
              tooltip: paused ? 'Resume Auto' : 'Pause Auto',
              onPressed: () => setState(() => paused = !paused),
              icon: Icon(paused ? Icons.play_arrow : Icons.pause),
            ),
        ],
      ),
    );
  }

  Widget _agents() => ListView(
    padding: const EdgeInsets.fromLTRB(16, 4, 16, 20),
    children: [
      _status(crew: true),
      GridView.count(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        crossAxisCount: 2,
        crossAxisSpacing: 10,
        mainAxisSpacing: 10,
        childAspectRatio: .92,
        children: [for (var i = 0; i < _crew.length; i++) _portrait(i)],
      ),
    ],
  );

  Widget _portrait(int index) {
    final agent = _crew[index];
    final colors = Theme.of(context).colorScheme;
    final active = held == index || auto && selected == index;
    return PreviewHold(
      key: ValueKey('portrait-$index'),
      onTap: () => openDetail(index),
      onStart: () => startHold(index),
      onFinish: finishHold,
      label: 'Open ${agent.name}; hold to talk',
      child: Container(
        decoration: BoxDecoration(
          color: active ? colors.primary.withValues(alpha: .1) : colors.surface,
          border: Border.all(
            color: active ? colors.primary : colors.outline,
            width: active ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        padding: const EdgeInsets.all(10),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            VoiceAvatar(voice: agent.voice, size: 66),
            const SizedBox(height: 8),
            Text(
              agent.name,
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
            ),
            Text(
              agent.topic,
              style: const TextStyle(fontSize: 11),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 5),
            Text(
              held == index
                  ? 'Recording…'
                  : auto && selected == index
                  ? 'Auto recipient'
                  : 'Hold to talk',
              style: TextStyle(fontSize: 11, color: colors.primary),
            ),
          ],
        ),
      ),
    );
  }

  Widget _talkSurface(int index) => PreviewHold(
    key: ValueKey('talk-$index'),
    onStart: () => startHold(index),
    onFinish: finishHold,
    label: 'Hold to talk to ${_crew[index].name}',
    child: Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 22),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primary
            .withValues(alpha: held == index ? .25 : .1),
        border: Border.all(color: Theme.of(context).colorScheme.primary),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          Icon(held == index ? Icons.graphic_eq : Icons.mic, size: 38),
          const SizedBox(height: 8),
          Text(
            held == index
                ? 'Release to send to ${_crew[index].name}'
                : 'Hold to talk to ${_crew[index].name}',
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          const Text('Drag away to cancel', style: TextStyle(fontSize: 11)),
        ],
      ),
    ),
  );

  Widget _detail(int index) {
    final agent = _crew[index];
    final header = Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            VoiceAvatar(voice: agent.voice, size: 44),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    agent.topic,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  Text(
                    'Recipient: ${agent.name}',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
        _status(),
        const SizedBox(height: 12),
      ],
    );
    final feed = _messages.where((m) => m.agentId == 'a${index + 1}').toList();
    if (feed.isEmpty) {
      feed.add(
        Message(
          'a${index + 1}',
          agent.name,
          'Ready when you are.',
          voice: agent.voice,
          time: '14:35',
        ),
      );
    }
    final bubbles = [
      for (final message in feed)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: MessageCard(message: message),
        ),
    ];
    return Column(
      children: [
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [header, ...bubbles],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: _talkSurface(index),
        ),
      ],
    );
  }

  Widget _recent() => Column(
    children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Recent',
              style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
            ),
            const Text(
              'All messages · in time order',
              style: TextStyle(fontSize: 12),
            ),
            _status(),
          ],
        ),
      ),
      Expanded(
        child: ListView.builder(
          reverse: true,
          padding: const EdgeInsets.all(16),
          itemCount: _messages.length,
          itemBuilder: (context, offset) {
            final message = _messages[_messages.length - 1 - offset];
            final index = int.parse(message.agentId.substring(1)) - 1;
            return Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Stack(
                children: [
                  MessageCard(message: message),
                  if (message.role != 'user')
                    Positioned(
                      bottom: 4,
                      right: 8,
                      child: PreviewHold(
                        key: ValueKey('reply-${message.id}'),
                        onStart: () => startHold(index),
                        onFinish: finishHold,
                        label: 'Hold to reply to ${_crew[index].name}',
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 6,
                          ),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                held == index
                                    ? Icons.graphic_eq
                                    : Icons.mic_none,
                                size: 16,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                'Reply',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: Theme.of(context).colorScheme.primary,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            );
          },
        ),
      ),
    ],
  );
}

/// Flutter's gesture arena separates tap from long press and scrolling.
/// Once a hold starts, dragging beyond the cancellation distance is irreversible.
class PreviewHold extends StatefulWidget {
  const PreviewHold({
    super.key,
    required this.child,
    required this.label,
    required this.onStart,
    required this.onFinish,
    this.onTap,
  });
  final Widget child;
  final String label;
  final VoidCallback onStart;
  final ValueChanged<bool> onFinish;
  final VoidCallback? onTap;
  @override
  State<PreviewHold> createState() => _PreviewHoldState();
}

class _PreviewHoldState extends State<PreviewHold> {
  static const cancelDistance = 48.0;
  bool cancelled = false;
  @override
  Widget build(BuildContext context) => Semantics(
    button: true,
    label: widget.label,
    child: GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: widget.onTap,
      onLongPressStart: (_) {
        cancelled = false;
        widget.onStart();
      },
      onLongPressMoveUpdate: (details) {
        if (!cancelled && details.offsetFromOrigin.distance > cancelDistance) {
          cancelled = true;
          widget.onFinish(true);
        }
      },
      onLongPressEnd: (_) {
        if (!cancelled) widget.onFinish(false);
      },
      onLongPressCancel: () => widget.onFinish(true),
      child: widget.child,
    ),
  );
}
