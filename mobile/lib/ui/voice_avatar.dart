import 'dart:math' as math;

import 'package:flutter/material.dart';

import 'avatar_catalog.dart';

/// VoiceAvatar.vue equivalent. Bottom-aligned, proportionate irregular crop.
class VoiceAvatar extends StatelessWidget {
  const VoiceAvatar({super.key, required this.voice, this.size = 64});
  final String voice;
  final double size;
  @override
  Widget build(BuildContext context) {
    final frame = portraitFrames[voice.trim().toLowerCase()];
    return Semantics(
      label: '$voice voice portrait',
      image: true,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(size * .24),
        child: SizedBox(
          width: size,
          height: size,
          child: ColoredBox(
            color: const Color(0xff2c394b),
            child: frame == null
                ? Center(
                    child: Text(
                      voice.isEmpty
                          ? '—'
                          : voice
                                .substring(0, math.min(3, voice.length))
                                .toUpperCase(),
                      style: TextStyle(
                        color: const Color(0xffc4d8f7),
                        fontSize: size * .25,
                      ),
                    ),
                  )
                : Align(
                    alignment: Alignment.bottomCenter,
                    child: SizedBox(
                      width:
                          frame.width *
                          size /
                          math.max(frame.width, frame.height),
                      height:
                          frame.height *
                          size /
                          math.max(frame.width, frame.height),
                      child: LayoutBuilder(
                        builder: (context, constraints) {
                          final scale = constraints.maxWidth / frame.width;
                          return Stack(
                            clipBehavior: Clip.hardEdge,
                            children: [
                              Positioned(
                                left: -frame.left * scale,
                                top: -frame.top * scale,
                                width: portraitSheetSize.width * scale,
                                height: portraitSheetSize.height * scale,
                                child: Image.asset(
                                  'assets/avatars/editorial.webp',
                                  fit: BoxFit.fill,
                                  excludeFromSemantics: true,
                                ),
                              ),
                            ],
                          );
                        },
                      ),
                    ),
                  ),
          ),
        ),
      ),
    );
  }
}
