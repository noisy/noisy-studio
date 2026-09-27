import 'package:flutter/material.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/talk_first.dart';
export 'package:noisy_studio_mobile/ui/hold_control.dart' show HoldControl;

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
  final bool initialAuto, showCancelTarget, showRecentCancel, showDetailCancel;
  @override
  State<TalkFirstPreview> createState() => _TalkFirstPreviewState();
}

class _TalkFirstPreviewState extends State<TalkFirstPreview> {
  late bool auto = widget.initialAuto;
  late String selected = 'a${(widget.initialDetail ?? 0) + 1}';
  String? held, feedback;
  bool paused = false;
  @override
  Widget build(BuildContext context) => TalkFirstView(
    agents: [
      for (var i = 0; i < _crew.length; i++)
        TalkAgent(
          id: 'a${i + 1}',
          name: _crew[i].name,
          topic: _crew[i].topic,
          voice: _crew[i].voice,
        ),
    ],
    messages: _messages,
    selectedId: selected,
    auto: auto,
    recordingId: held,
    initialTab: widget.initialTab,
    initialDetail: widget.initialDetail,
    showCancelTarget: widget.showCancelTarget,
    showRecentCancel: widget.showRecentCancel,
    showDetailCancel: widget.showDetailCancel,
    settings: const Center(child: Text('Connection and preferences')),
    onSelect: (id) => setState(() => selected = id),
    onMode: (value) => setState(() => auto = value),
    onHold: (id) => setState(() => held = id),
    onFinish: (cancel) => setState(() {
      held = null;
      feedback = cancel ? 'Recording preview cancelled' : 'Preview sent';
    }),
    paused: paused,
    onPause: () => setState(() => paused = !paused),
    feedback: feedback,
  );
}
