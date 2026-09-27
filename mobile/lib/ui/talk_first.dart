import 'package:flutter/material.dart';

import '../core/models.dart';
import 'screens.dart' show MessageCard;
import 'voice_avatar.dart';
import 'hold_control.dart';

class TalkAgent {
  const TalkAgent({
    required this.id,
    required this.name,
    required this.topic,
    required this.voice,
    this.canRecord = true,
  });
  factory TalkAgent.fromAgent(Agent agent) => TalkAgent(
    id: agent.id,
    name: agent.name,
    topic: agent.name,
    voice: agent.voice,
    canRecord: agent.state != AgentState.offline,
  );
  final String id, name, topic, voice;
  final bool canRecord;
}

class TalkFirstView extends StatefulWidget {
  const TalkFirstView({
    super.key,
    required this.agents,
    required this.messages,
    required this.selectedId,
    required this.auto,
    required this.onSelect,
    required this.onMode,
    required this.onHold,
    required this.onFinish,
    required this.settings,
    this.enabled = true,
    this.recordingId,
    this.resetToken,
    this.paused = false,
    this.onPause,
    this.onReplay,
    this.onPauseSpeech,
    this.onSkip,
    this.onRecall,
    this.pausedMessageId = 0,
    this.notice,
    this.feedback,

    this.initialTab = 0,
    this.initialDetail,
    this.showCancelTarget = false,
    this.showRecentCancel = false,
    this.showDetailCancel = false,
  });
  final int initialTab;
  final int? initialDetail;
  final List<TalkAgent> agents;
  final List<Message> messages;
  final String? selectedId, recordingId, notice, feedback;
  final bool auto, enabled, paused;
  final Object? resetToken;
  final Widget settings;
  final ValueChanged<String> onSelect, onHold;
  final ValueChanged<bool> onMode, onFinish;
  final VoidCallback? onPause;
  final ValueChanged<Message>? onReplay, onPauseSpeech, onSkip, onRecall;
  final int pausedMessageId;
  final bool showCancelTarget;
  final bool showRecentCancel;
  final bool showDetailCancel;
  @override
  State<TalkFirstView> createState() => _TalkFirstViewState();
}

class _TalkFirstViewState extends State<TalkFirstView> {
  bool get auto => widget.auto;
  bool get paused => widget.paused;
  String? get feedback => widget.feedback;
  List<TalkAgent> get _crew => widget.agents;
  List<Message> get _messages => widget.messages;
  int get selected => _crew.indexWhere((a) => a.id == widget.selectedId);
  late int tab = widget.initialTab;
  late String? detailId = widget.initialDetail == null
      ? null
      : _crew[widget.initialDetail!].id;
  int? get detail {
    final index = _crew.indexWhere((a) => a.id == detailId);
    return index < 0 ? null : index;
  }

  String? heldId;
  int? get held {
    final index = _crew.indexWhere((a) => a.id == heldId);
    return index < 0 ? null : index;
  }

  final _navigationKey = GlobalKey();
  Rect _navigationRect() {
    final box = _navigationKey.currentContext!.findRenderObject()! as RenderBox;
    return Rect.fromPoints(
      box.localToGlobal(Offset.zero),
      box.localToGlobal(box.size.bottomRight(Offset.zero)),
    );
  }

  void openDetail(int index) {
    widget.onSelect(_crew[index].id);
    setState(() => detailId = _crew[index].id);
  }

  void startHold(int index) {
    if (!widget.enabled || index < 0) return;
    setState(() => heldId = _crew[index].id);
    widget.onHold(_crew[index].id);
  }

  void finishHold(bool cancelled) {
    if (held == null) return;
    widget.onFinish(cancelled);
    setState(() => heldId = null);
  }

  @override
  void didUpdateWidget(TalkFirstView oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.resetToken != widget.resetToken) heldId = null;
  }

  MessageCard _messageCard(Message message, {bool embedded = false}) =>
      MessageCard(
        embedded: embedded,
        message: message,
        onReplay: widget.onReplay,
        onPause: widget.onPauseSpeech,
        onSkip: widget.onSkip,
        onCancel: widget.onRecall,
        paused: widget.pausedMessageId == message.id,
      );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      leading: detail == null
          ? null
          : IconButton(
              onPressed: () {
                finishHold(true);
                setState(() => detailId = null);
              },
              icon: const Icon(Icons.arrow_back),
              tooltip: 'Back',
            ),
      title: Text(
        detail == null ? 'Noisy Studio' : _crew[detail!].name,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      actions: [_mode(), const SizedBox(width: 12)],
    ),
    body: SafeArea(
      child: Column(
        children: [
          if (widget.notice != null)
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text(widget.notice!, style: const TextStyle(fontSize: 12)),
            ),
          Expanded(
            child: detail != null
                ? _detail(detail!)
                : tab == 1
                ? _recent()
                : tab == 2
                ? widget.settings
                : _crew.isEmpty
                ? const Center(
                    child: Text(
                      'No open conversations. Connect your desktop in Settings.',
                    ),
                  )
                : _agents(),
          ),
        ],
      ),
    ),
    bottomNavigationBar: Opacity(
      key: const ValueKey('nav-visibility'),
      opacity: held != null && detail != null ? 0 : 1,
      child: AbsorbPointer(
        absorbing: held != null,
        child: NavigationBar(
          key: _navigationKey,
          selectedIndex: tab,
          onDestinationSelected: (value) => setState(() {
            tab = value;
            detailId = null;
            heldId = null;
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
      ),
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
    onSelectionChanged: widget.enabled
        ? (values) => widget.onMode(values.first)
        : null,
  );

  Widget _status({bool crew = false}) {
    if (crew && !auto) return const SizedBox.shrink();
    if (held == null && !auto && feedback == null) {
      return const SizedBox.shrink();
    }
    final text = !crew && held != null
        ? '${widget.recordingId == _crew[held!].id ? 'Recording' : 'Connecting'} → ${_crew[held!].name}'
        : auto
        ? '${paused ? 'Auto paused' : 'Auto listening'} → ${selected < 0 ? 'Choose an agent' : _crew[selected].name}'
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
              onPressed: held == null ? widget.onPause : null,
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
    return HoldControl(
      enabled: widget.enabled,
      resetToken: widget.resetToken,
      key: ValueKey('portrait-${agent.id}'),
      canHold: agent.canRecord,
      cancelBelow: true,
      initiallyHeld: widget.showCancelTarget && index == 0,
      onTap: () => openDetail(index),
      onStart: () => startHold(index),
      onFinish: finishHold,
      label:
          '${agent.topic}, ${agent.name}. ${held == index
              ? widget.recordingId == agent.id
                    ? 'Recording'
                    : 'Preparing microphone'
              : auto && selected == index
              ? 'Selected Auto recipient'
              : 'Tap to open; hold to talk'}',
      child: Container(
        decoration: BoxDecoration(
          color: active
              ? Color.alphaBlend(
                  colors.primary.withValues(alpha: .1),
                  colors.surface,
                )
              : colors.surface,
          border: Border.all(
            color: active ? colors.primary : colors.outline,
            width: active ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(14),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            Expanded(
              child: LayoutBuilder(
                builder: (context, constraints) => Stack(
                  children: [
                    Positioned.fill(
                      child: ClipRect(
                        child: OverflowBox(
                          alignment: Alignment.topCenter,
                          minWidth: constraints.maxWidth,
                          maxWidth: constraints.maxWidth,
                          minHeight: constraints.maxWidth,
                          maxHeight: constraints.maxWidth,
                          child: VoiceAvatar(
                            voice: agent.voice,
                            size: constraints.maxWidth,
                            borderRadius: BorderRadius.zero,
                          ),
                        ),
                      ),
                    ),
                    if (widget.recordingId == agent.id)
                      Positioned(
                        right: 6,
                        bottom: 6,
                        child: Semantics(
                          label: 'Recording to ${agent.name}',
                          child: Container(
                            padding: const EdgeInsets.all(7),
                            decoration: BoxDecoration(
                              color: colors.error,
                              shape: BoxShape.circle,
                              border: Border.all(
                                color: colors.surface,
                                width: 2,
                              ),
                            ),
                            child: Icon(
                              Icons.mic,
                              size: 22,
                              color: colors.onError,
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
              child: Text(
                agent.topic,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _talkSurface(int index) => HoldControl(
    enabled: widget.enabled,
    resetToken: widget.resetToken,
    key: ValueKey('talk-${_crew[index].id}'),
    canHold: _crew[index].canRecord,
    cancelArea: _navigationRect,
    cancelBelow: true,
    initiallyHeld: widget.showDetailCancel,
    onStart: () => startHold(index),
    onFinish: finishHold,
    label: 'Hold to talk to ${_crew[index].name}',
    child: Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 22, horizontal: 12),
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          Theme.of(context).colorScheme.primary
              .withValues(alpha: held == index ? .25 : .1),
          Theme.of(context).colorScheme.surface,
        ),
        border: Border.all(color: Theme.of(context).colorScheme.primary),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          Icon(
            held == index
                ? widget.recordingId == _crew[index].id
                      ? Icons.graphic_eq
                      : Icons.hourglass_top
                : Icons.mic,
            size: 38,
          ),
          const SizedBox(height: 8),
          Text(
            held == index
                ? widget.recordingId == _crew[index].id
                      ? 'Release to send'
                      : 'Preparing microphone…'
                : 'Hold to talk to ${_crew[index].name}',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          const Text(
            'Release on Cancel to discard',
            style: TextStyle(fontSize: 11),
          ),
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
    final feed = _messages.where((m) => m.agentId == agent.id).toList();
    final bubbles = [
      for (final message in feed)
        Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: _messageCard(message),
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
            _status(crew: true),
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
            final index = _crew.indexWhere((a) => a.id == message.agentId);
            return Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: auto && index >= 0 && selected == index
                      ? Theme.of(context).colorScheme.primary
                      : Colors.transparent,
                ),
                child: GestureDetector(
                  key: ValueKey('message-${message.id}'),
                  onTap: auto && widget.enabled && index >= 0
                      ? () => widget.onSelect(_crew[index].id)
                      : null,
                  child: message.role == 'user'
                      ? _messageCard(message)
                      : _replyBubble(message, index),
                ),
              ),
            );
          },
        ),
      ),
    ],
  );
  Widget _replyBubble(Message message, int index) {
    final colors = Theme.of(context).colorScheme;
    return Container(
      key: ValueKey('bubble-${message.id}'),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: Color.alphaBlend(
          colors.secondary.withValues(alpha: .04),
          colors.surface,
        ),
        borderRadius: BorderRadius.circular(10),
      ),
      foregroundDecoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: colors.secondary.withValues(alpha: .3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _messageCard(message, embedded: true),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const Spacer(),
              if (index >= 0)
                HoldControl(
                  enabled: widget.enabled && index >= 0,
                  canHold: index >= 0 && _crew[index].canRecord,
                  resetToken: widget.resetToken,
                  key: ValueKey('reply-${message.id}'),
                  cancelLeft: true,
                  initiallyHeld: widget.showRecentCancel && message.id == 6,
                  onStart: () => startHold(index),
                  onFinish: finishHold,
                  label: 'Hold to reply to ${message.author}',
                  onTap: auto && widget.enabled && index >= 0
                      ? () => widget.onSelect(_crew[index].id)
                      : null,
                  child: ClipRRect(
                    borderRadius: const BorderRadius.only(
                      bottomRight: Radius.circular(10),
                    ),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                      decoration: BoxDecoration(
                        color: Color.alphaBlend(
                          colors.primary.withValues(alpha: .12),
                          colors.surface,
                        ),
                        border: Border.all(
                          color: colors.primary.withValues(alpha: .6),
                        ),
                        borderRadius: const BorderRadius.only(
                          topLeft: Radius.circular(8),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            held == index
                                ? widget.recordingId == message.agentId
                                      ? Icons.graphic_eq
                                      : Icons.hourglass_top
                                : Icons.mic_none,
                            size: 16,
                            color: colors.primary,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Reply',
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w600,
                              color: colors.primary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
