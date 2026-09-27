import 'package:flutter/material.dart';
import 'package:noisy_studio_mobile/ui/voice_avatar.dart';

const _crew = [
  (name: 'Lux', topic: 'Release review', voice: 'lux', status: 'Ready'),
  (name: 'Atlas', topic: 'Mobile companion', voice: 'atlas', status: 'Working'),
  (name: 'Iris', topic: 'Design exploration', voice: 'iris', status: 'Ready'),
  (name: 'Orion', topic: 'Audio checks', voice: 'orion', status: 'Ready'),
];

/// Design fixture only: deliberately has no microphone or daemon dependency.
class TalkFirstPreview extends StatefulWidget {
  const TalkFirstPreview({
    super.key,
    this.initialAuto = false,
    this.initialTab = 0,
    this.compact = false,
  });
  final bool initialAuto;
  final int initialTab;
  final bool compact;
  @override
  State<TalkFirstPreview> createState() => _TalkFirstPreviewState();
}

class _TalkFirstPreviewState extends State<TalkFirstPreview> {
  late bool auto = widget.initialAuto;
  late int tab = widget.initialTab;
  int selected = 0;
  int? held;
  int? detail;
  bool paused = false;
  String? feedback;

  void finishHold({bool cancelled = false}) {
    if (held == null) return;
    setState(() {
      feedback = cancelled
          ? 'Preview cancelled'
          : 'Voice message preview sent to ${_crew[held!].name}';
      held = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        leading: detail == null
            ? null
            : IconButton(
                onPressed: () => setState(() => detail = null),
                icon: const Icon(Icons.arrow_back),
                tooltip: 'Back to agents',
              ),
        title: Text(detail == null ? 'Noisy Studio' : _crew[detail!].name),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Text(
              'DESIGN',
              style: TextStyle(
                fontSize: 10,
                letterSpacing: 1.5,
                color: colors.primary,
              ),
            ),
          ),
        ],
      ),
      body: detail != null
          ? _detail(context, detail!)
          : tab == 1
          ? _recent(context)
          : tab == 2
          ? const Center(
              child: Text(
                'Connection and preferences live here.\nThis prototype only explores talking.',
                textAlign: TextAlign.center,
              ),
            )
          : _agents(context),
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
            selectedIcon: Icon(Icons.people),
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
  }

  Widget _agents(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 6, 16, 20),
      children: [
        const Text(
          'Your crew',
          style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 4),
        Text(
          '4 agents · Desktop connected',
          style: TextStyle(color: colors.onSurfaceVariant, fontSize: 12),
        ),
        const SizedBox(height: 18),
        SegmentedButton<bool>(
          segments: const [
            ButtonSegment(
              value: false,
              label: Text('Push to talk'),
              icon: Icon(Icons.touch_app_outlined),
            ),
            ButtonSegment(
              value: true,
              label: Text('Auto'),
              icon: Icon(Icons.graphic_eq),
            ),
          ],
          selected: {auto},
          onSelectionChanged: (value) => setState(() {
            auto = value.first;
            held = null;
            feedback = null;
          }),
        ),
        const SizedBox(height: 12),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
            color: colors.primary.withValues(alpha: .08),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(
            children: [
              Icon(
                held != null || auto && !paused
                    ? Icons.graphic_eq
                    : Icons.mic_none,
                size: 20,
                color: colors.primary,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  held != null
                      ? 'Listening to you → ${_crew[held!].name}'
                      : auto
                      ? paused
                            ? 'Auto paused · ${_crew[selected].name} selected'
                            : 'Listening → ${_crew[selected].name}'
                      : 'Hold an agent to talk. Release to send.',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
              if (auto)
                IconButton(
                  visualDensity: VisualDensity.compact,
                  onPressed: () => setState(() => paused = !paused),
                  icon: Icon(paused ? Icons.play_arrow : Icons.pause),
                  tooltip: paused ? 'Resume auto' : 'Pause auto',
                ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        if (widget.compact) ...[
          for (var i = 0; i < _crew.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: _agentCard(context, i, true),
            ),
        ] else
          GridView.count(
            crossAxisCount: 2,
            childAspectRatio: .80,
            crossAxisSpacing: 10,
            mainAxisSpacing: 10,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            children: [
              for (var i = 0; i < _crew.length; i++)
                _agentCard(context, i, false),
            ],
          ),
        const SizedBox(height: 12),
        Text(
          feedback ?? 'Interactive preview · microphone is not used',
          style: TextStyle(fontSize: 11, color: colors.onSurfaceVariant),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _agentCard(BuildContext context, int index, bool compact) {
    final agent = _crew[index];
    final colors = Theme.of(context).colorScheme;
    final active = held == index || auto && selected == index;
    final face = VoiceAvatar(voice: agent.voice, size: compact ? 48 : 64);
    final words = Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: compact
          ? CrossAxisAlignment.start
          : CrossAxisAlignment.center,
      children: [
        Text(
          agent.name,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        ),
        Text(
          agent.topic,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 11, color: colors.onSurfaceVariant),
        ),
        const SizedBox(height: 4),
        Text(
          held == index
              ? 'Release to send'
              : auto && selected == index
              ? 'Selected recipient'
              : auto
              ? 'Tap to select'
              : 'Hold to talk',
          style: TextStyle(
            fontSize: 11,
            color: active ? colors.primary : colors.onSurfaceVariant,
          ),
        ),
      ],
    );
    return DecoratedBox(
      decoration: BoxDecoration(
        color: active ? colors.primary.withValues(alpha: .08) : colors.surface,
        border: Border.all(
          color: active ? colors.primary : colors.outline,
          width: active ? 2 : 1,
        ),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Expanded(
            flex: compact ? 0 : 1,
            child: Semantics(
              button: true,
              label: auto
                  ? 'Select ${agent.name} as recipient'
                  : 'Hold to talk to ${agent.name}',
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTap: auto
                    ? () => setState(() => selected = index)
                    : () => setState(
                        () => feedback = 'Press and hold ${agent.name} to talk',
                      ),
                onLongPressStart: auto
                    ? null
                    : (_) => setState(() {
                        held = index;
                        feedback = null;
                      }),
                onLongPressEnd: auto ? null : (_) => finishHold(),
                onLongPressCancel: auto
                    ? null
                    : () => finishHold(cancelled: true),
                child: Padding(
                  padding: EdgeInsets.all(compact ? 12 : 10),
                  child: compact
                      ? Row(
                          children: [
                            face,
                            const SizedBox(width: 12),
                            Expanded(child: words),
                          ],
                        )
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [face, const SizedBox(height: 8), words],
                        ),
                ),
              ),
            ),
          ),
          SizedBox(
            height: 40,
            width: double.infinity,
            child: TextButton(
              onPressed: () => setState(() => detail = index),
              child: const Text('Details ↗', style: TextStyle(fontSize: 11)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _detail(BuildContext context, int index) {
    final agent = _crew[index];
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            VoiceAvatar(voice: agent.voice, size: 56),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    agent.topic,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    '${agent.status} · Claude',
                    style: const TextStyle(fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 22),
        const Text(
          'Conversation',
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
        const SizedBox(height: 12),
        _bubble('You', 'Could you review the latest changes?', false),
        _bubble(
          agent.name,
          'The checks look good. I’m taking one more look at the small-screen layout.',
          true,
        ),
        _bubble(
          'You',
          'Great, focus on making it easy to start talking.',
          false,
        ),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          onPressed: () => setState(() {
            selected = index;
            detail = null;
            tab = 0;
          }),
          icon: const Icon(Icons.mic_none),
          label: Text('Talk to ${agent.name}'),
        ),
        const SizedBox(height: 10),
        const Text(
          'Voice and advanced controls can live in a secondary menu.',
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 11),
        ),
      ],
    );
  }

  Widget _bubble(String name, String message, bool agent) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              name,
              style: TextStyle(
                fontSize: 11,
                color: agent
                    ? Theme.of(context).colorScheme.secondary
                    : Theme.of(context).colorScheme.primary,
              ),
            ),
            const SizedBox(height: 6),
            Text(message, style: const TextStyle(fontSize: 13, height: 1.5)),
          ],
        ),
      ),
    ),
  );

  Widget _recent(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      const Text(
        'Recent',
        style: TextStyle(fontSize: 28, fontWeight: FontWeight.w700),
      ),
      const Text('All conversations, together', style: TextStyle(fontSize: 12)),
      const SizedBox(height: 20),
      for (final entry in [
        (0, 'Ready for your review', 'Just now'),
        (2, 'Two new directions are ready.', '2 min'),
        (1, 'I’m checking the recording flow.', '4 min'),
        (3, 'Playback checks passed.', '8 min'),
      ])
        Card(
          margin: const EdgeInsets.only(bottom: 10),
          child: ListTile(
            onTap: () => setState(() => detail = entry.$1),
            leading: VoiceAvatar(voice: _crew[entry.$1].voice, size: 40),
            title: Text(
              _crew[entry.$1].name,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
            ),
            subtitle: Text(entry.$2, style: const TextStyle(fontSize: 12)),
            trailing: Text(entry.$3, style: const TextStyle(fontSize: 10)),
          ),
        ),
    ],
  );
}
