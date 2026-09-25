import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:noisy_studio_mobile/core/models.dart';
import 'package:noisy_studio_mobile/ui/avatar_catalog.dart';
import 'package:noisy_studio_mobile/ui/message_status.dart';
import 'package:noisy_studio_mobile/ui/screens.dart';

void main() {
  test(
    'generated portrait frames match every canonical irregular desktop crop',
    () {
      final voices = jsonDecode(
        File('../dashboard/src/avatars/voice-order.json').readAsStringSync(),
      ) as List;
      final frames =
          (jsonDecode(
                File('../dashboard/src/avatars/portrait-frames.json')
                    .readAsStringSync(),
              ) as Map)['editorial']
              as List;
      expect(portraitFrames, {
        for (var i = 0; i < voices.length; i++)
          voices[i]: Rect.fromLTWH(
            (frames[i]['left'] as num).toDouble(),
            (frames[i]['top'] as num).toDouble(),
            (frames[i]['width'] as num).toDouble(),
            (frames[i]['height'] as num).toDouble(),
          ),
      });
    },
  );
  test('real daemon descriptive statuses use the desktop prefix semantics', () {
    expect(
      [
        messageChip('user', 'ready — awaiting pickup').$2,
        messageChip('user', 'transcribing…').$2,
        messageChip('user', 'unavailable — socket missing').$2,
        messageChip('claude', 'playing through speakers…').$2,
        messageState('claude', 'queued — waiting for you to finish'),
      ],
      [
        '◌ AWAITING AGENT',
        '◌ TRANSCRIBING',
        'ACTION NEEDED',
        '▶ PLAYING',
        'holding',
      ],
    );
  });
  test('message identities distinguish daemon system and named subagents', () {
    final snapshot = Snapshot.fromJson({
      'status': {
        'speaker_labels': {'worker': 'Reviewer'},
      },
      'utterances': [
        {
          'id': 1,
          'role': 'daemon',
          'agent': 'a1',
          'agent_label': 'Lux',
          'text': 'Ready',
        },
        {
          'id': 2,
          'role': 'system',
          'agent': 'a1',
          'agent_label': 'Lux',
          'text': 'Notice',
        },
        {
          'id': 3,
          'role': 'claude',
          'agent': 'a1',
          'agent_label': 'Lux',
          'speaker': 'worker',
          'text': 'Checked',
        },
        {
          'id': 4,
          'role': 'claude',
          'agent': 'a1',
          'agent_label': 'Lux',
          'speaker': 'helper',
          'text': 'Checked',
        },
      ],
    });
    expect(snapshot.messages.map((m) => [m.id, m.author]).toList(), [
      [1, 'Noisy Studio'],
      [2, 'System'],
      [3, 'Reviewer'],
      [4, 'helper · Lux'],
    ]);
  });
  testWidgets(
    'playback and recall emit original identity only in permitted states',
    (tester) async {
      final events = <String>[];
      Future<void> show(String role, String status) async {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: MessageCard(
                message: Message(
                  'a1',
                  'Lux',
                  'Example',
                  id: 91,
                  role: role,
                  status: status,
                ),
                onReplay: (m) => events.add('replay:${m.id}'),
                onPause: (m) => events.add('pause:${m.id}'),
                onSkip: (m) => events.add('skip:${m.id}'),
                onCancel: (m) => events.add('cancel:${m.id}'),
              ),
            ),
          ),
        );
      }

      await show('claude', 'playing through speakers…');
      await tester.tap(find.byTooltip('Pause playback'));
      await tester.tap(find.byTooltip('Skip the rest of this message'));
      expect(find.byTooltip('Play this message again'), findsNothing);
      await show('claude', 'played');
      await tester.tap(find.byTooltip('Play this message again'));
      await show('user', 'ready — awaiting pickup');
      await tester.tap(find.byTooltip('Recall this message'));
      await show('user', 'unavailable — action needed');
      expect(find.byTooltip('Recall this message'), findsOneWidget);
      await show('claude', 'skipped — dismissed by you');
      expect(find.byTooltip('Play this message again'), findsOneWidget);
      await show('claude', 'error');
      expect(find.byTooltip('Play this message again'), findsOneWidget);
      await show('system', 'played');
      expect(find.byTooltip('Play this message again'), findsNothing);
      await show('user', 'delivered to Claude');
      expect(find.byTooltip('Recall this message'), findsNothing);
      expect(events, ['pause:91', 'skip:91', 'replay:91', 'cancel:91']);
    },
  );
}
