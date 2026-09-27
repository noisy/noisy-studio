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
    this.showCancelTarget = false,
    this.showRecentCancel = false,
    this.showDetailCancel = false,
  });
  final int initialTab;
  final int? initialDetail;
  final bool initialAuto;
  final bool showCancelTarget;
  final bool showRecentCancel;
  final bool showDetailCancel;
  @override
  State<TalkFirstPreview> createState() => _TalkFirstPreviewState();
}

class _TalkFirstPreviewState extends State<TalkFirstPreview> {
  late bool auto = widget.initialAuto;
  late int tab = widget.initialTab;
  late int selected = widget.initialDetail ?? 0;
  late int? detail = widget.initialDetail;
  late int? held = (widget.showCancelTarget || widget.showDetailCancel)
      ? 0
      : widget.showRecentCancel
      ? 2
      : null;
  final _navigationKey = GlobalKey();
  Rect _navigationRect() {
    final box = _navigationKey.currentContext!.findRenderObject()! as RenderBox;
    return Rect.fromPoints(
      box.localToGlobal(Offset.zero),
      box.localToGlobal(box.size.bottomRight(Offset.zero)),
    );
  }

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
    bottomNavigationBar: AbsorbPointer(
      absorbing: held != null,
      child: NavigationBar(
        key: _navigationKey,
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
        ? 'Recording → ${_crew[held!].name}'
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
      cancelBelow: true,
      initiallyHeld: widget.showCancelTarget && index == 0,
      onTap: () => openDetail(index),
      onStart: () => startHold(index),
      onFinish: finishHold,
      label:
          '${agent.topic}, ${agent.name}. ${held == index
              ? 'Recording'
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
                    if (held == index)
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

  Widget _talkSurface(int index) => PreviewHold(
    key: ValueKey('talk-$index'),
    cancelArea: _navigationRect,
    cancelBelow: true,
    initiallyHeld: widget.showDetailCancel,
    onStart: () => startHold(index),
    onFinish: finishHold,
    label: 'Hold to talk to ${_crew[index].name}',
    child: Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 22),
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
          Icon(held == index ? Icons.graphic_eq : Icons.mic, size: 38),
          const SizedBox(height: 8),
          Text(
            held == index
                ? 'Release to send'
                : 'Hold to talk to ${_crew[index].name}',
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
            final index = int.parse(message.agentId.substring(1)) - 1;
            return Padding(
              padding: const EdgeInsets.only(bottom: 14),
              child: Container(
                padding: const EdgeInsets.all(2),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  color: auto && selected == index
                      ? Theme.of(context).colorScheme.primary
                      : Colors.transparent,
                ),
                child: GestureDetector(
                  key: ValueKey('message-${message.id}'),
                  onTap: auto ? () => setState(() => selected = index) : null,
                  child: message.role == 'user'
                      ? MessageCard(message: message)
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
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    VoiceAvatar(voice: message.voice, size: 26),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        message.author.toUpperCase(),
                        style: TextStyle(
                          fontSize: 10,
                          letterSpacing: 1.2,
                          color: colors.secondary,
                        ),
                      ),
                    ),
                    Text(
                      message.time,
                      style: TextStyle(
                        fontSize: 10,
                        color: colors.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 9),
                Text(
                  message.text,
                  key: ValueKey('body-${message.id}'),
                  style: const TextStyle(fontSize: 14, height: 1.5),
                ),
              ],
            ),
          ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(12, 0, 8, 10),
                  child: Text(
                    '✓ ${message.status.toUpperCase()}',
                    style: TextStyle(
                      fontSize: 9,
                      letterSpacing: .6,
                      color: colors.secondary,
                    ),
                  ),
                ),
              ),
              PreviewHold(
                key: ValueKey('reply-${message.id}'),
                cancelLeft: true,
                initiallyHeld: widget.showRecentCancel && message.id == 6,
                onStart: () => startHold(index),
                onFinish: finishHold,
                label: 'Hold to reply to ${_crew[index].name}',
                onTap: auto ? () => setState(() => selected = index) : null,
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
                          held == index ? Icons.graphic_eq : Icons.mic_none,
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

/// Flutter's gesture arena separates tap from long press and scrolling.
/// Visible targets arm on hover and cancel only on release.
class PreviewHold extends StatefulWidget {
  const PreviewHold({
    super.key,
    required this.child,
    required this.label,
    required this.onStart,
    required this.onFinish,
    this.onTap,
    this.cancelBelow = false,
    this.cancelLeft = false,
    this.initiallyHeld = false,
    this.cancelArea,
  });
  final Widget child;
  final String label;
  final VoidCallback onStart;
  final ValueChanged<bool> onFinish;
  final VoidCallback? onTap;
  final bool cancelBelow;
  final bool cancelLeft;
  final bool initiallyHeld;
  final Rect Function()? cancelArea;
  @override
  State<PreviewHold> createState() => _PreviewHoldState();
}

class _PreviewHoldState extends State<PreviewHold>
    with SingleTickerProviderStateMixin {
  late final AnimationController _reveal = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 180),
  );
  double get progress => Curves.easeOutCubic.transform(_reveal.value);
  Offset? _pointer;
  @override
  void dispose() {
    _reveal.dispose();
    super.dispose();
  }

  static const cancelDistance = 48.0;
  final _overlay = OverlayPortalController();
  bool cancelled = false;
  bool cancelArmed = false;
  Color get cancelColor => (_pointer != null && cancelZone.contains(_pointer!))
      ? const Color(0xffed4058)
      : const Color(0xffb52d43);
  bool holding = false;
  final _link = LayerLink();
  final _target = GlobalKey();
  Size controlSize = Size.zero;
  RenderBox get targetBox =>
      _target.currentContext!.findRenderObject()! as RenderBox;
  Rect? get navLocal {
    final nav = widget.cancelArea?.call();
    return nav == null
        ? null
        : Rect.fromPoints(
            targetBox.globalToLocal(nav.topLeft),
            targetBox.globalToLocal(nav.bottomRight),
          );
  }

  Rect get cancelZone {
    final size = targetBox.size;
    final nav = navLocal;
    final local = widget.cancelLeft
        ? Rect.fromLTWH(-80 * progress, 0, 80 * progress, size.height)
        : Rect.fromLTWH(
            nav?.left ?? 0,
            size.height,
            nav?.width ?? size.width,
            ((nav?.bottom ?? size.height * 4 / 3) - size.height) * progress,
          );
    return Rect.fromPoints(
      targetBox.localToGlobal(local.topLeft),
      targetBox.localToGlobal(local.bottomRight),
    );
  }

  @override
  void initState() {
    super.initState();
    if (widget.initiallyHeld) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _begin();
      });
    }
  }

  void _begin() {
    cancelled = false;
    cancelArmed = false;
    _pointer = null;
    holding = true;
    if (widget.cancelBelow || widget.cancelLeft) {
      controlSize = targetBox.size;
      if (MediaQuery.disableAnimationsOf(context)) {
        _reveal.value = 1;
      } else {
        _reveal.forward(from: 0);
      }
      _overlay.show();
    }
    widget.onStart();
  }

  void _finish(bool cancel) {
    if (!holding) return;
    holding = false;
    cancelled = cancel;
    _reveal.stop();
    _overlay.hide();
    widget.onFinish(cancel);
  }

  Widget _cancelLabel() => const Center(
    child: FittedBox(
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.close, color: Colors.white, size: 20),
          SizedBox(width: 6),
          Text(
            'Cancel',
            style: TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
        ],
      ),
    ),
  );

  Widget _animatedPaper() {
    final left = widget.cancelLeft;
    final nav = navLocal;
    final controlLeft = nav == null ? 0.0 : -nav.left;
    final width = left
        ? 80 + controlSize.width
        : nav?.width ?? controlSize.width;
    final exposed = left
        ? 80.0
        : nav == null
        ? controlSize.height / 3
        : nav.bottom - controlSize.height;
    final height = left ? controlSize.height : controlSize.height + exposed;
    final overlap = (left ? controlSize.width : controlSize.height) * .28;
    final clip = left
        ? Rect.fromLTRB(80 * (1 - progress), 0, 80 + overlap * progress, height)
        : Rect.fromLTRB(
            0,
            controlSize.height - overlap * progress,
            width,
            controlSize.height + exposed * progress,
          );
    return SizedBox(
      width: width,
      height: height,
      child: Stack(
        children: [
          Positioned.fill(
            child: ClipRect(
              clipper: _PaperClip(clip),
              child: Transform.translate(
                offset: left
                    ? Offset(exposed * (1 - progress), 0)
                    : Offset(0, -exposed * (1 - progress)),
                child: Stack(
                  children: [
                    if (left) ...[
                      Positioned(
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: 80 + overlap,
                        child: Material(
                          key: const ValueKey('cancel-sheet'),
                          color: cancelColor,
                          borderRadius: const BorderRadius.only(
                            topLeft: Radius.circular(8),
                          ),
                        ),
                      ),
                      Positioned(
                        left: 0,
                        top: 0,
                        bottom: 0,
                        width: 80,
                        child: _cancelLabel(),
                      ),
                    ] else ...[
                      Positioned(
                        top: controlSize.height - overlap,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        child: Material(
                          key: const ValueKey('cancel-sheet'),
                          color: cancelColor,
                          borderRadius: BorderRadius.circular(14),
                        ),
                      ),
                      Positioned(
                        top: controlSize.height,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        child: _cancelLabel(),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            left: left ? 80 : controlLeft,
            top: 0,
            width: controlSize.width,
            height: controlSize.height,
            child: ExcludeSemantics(child: widget.child),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => OverlayPortal(
    controller: _overlay,
    overlayChildBuilder: (_) => Positioned(
      left: 0,
      top: 0,
      child: CompositedTransformFollower(
        link: _link,
        showWhenUnlinked: false,
        offset: widget.cancelLeft
            ? const Offset(-80, 0)
            : widget.cancelArea == null
            ? Offset.zero
            : Offset(navLocal!.left, 0),
        child: IgnorePointer(
          child: AnimatedBuilder(
            animation: _reveal,
            builder: (_, _) => _animatedPaper(),
          ),
        ),
      ),
    ),
    child: CompositedTransformTarget(
      key: _target,
      link: _link,
      child: Semantics(
        button: true,
        label: widget.label,
        child: Listener(
          onPointerCancel: (_) => _finish(true),
          child: GestureDetector(
            behavior: HitTestBehavior.opaque,
            onTap: widget.onTap,
            onLongPressStart: (_) => _begin(),
            onLongPressMoveUpdate: (details) {
              if (!holding || cancelled) return;
              if (widget.cancelBelow || widget.cancelLeft) {
                _pointer = details.globalPosition;
                final armed = cancelZone.contains(details.globalPosition);
                if (armed != cancelArmed) setState(() => cancelArmed = armed);
              } else if (details.offsetFromOrigin.distance > cancelDistance) {
                _finish(true);
              }
            },
            onLongPressEnd: (details) {
              if (!cancelled) {
                _finish(
                  (widget.cancelBelow || widget.cancelLeft) &&
                      cancelZone.contains(details.globalPosition),
                );
              }
            },
            onLongPressCancel: () => _finish(true),
            child: widget.child,
          ),
        ),
      ),
    ),
  );
}

class _PaperClip extends CustomClipper<Rect> {
  const _PaperClip(this.rect);
  final Rect rect;
  @override
  Rect getClip(Size size) => rect;
  @override
  bool shouldReclip(_PaperClip oldClipper) => oldClipper.rect != rect;
}
