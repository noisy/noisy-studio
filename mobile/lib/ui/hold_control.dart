import 'package:flutter/material.dart';

/// Flutter's gesture arena separates tap from long press and scrolling.
/// Visible targets arm on hover and cancel only on release.
class HoldControl extends StatefulWidget {
  const HoldControl({
    super.key,
    required this.child,
    required this.label,
    required this.onStart,
    required this.onFinish,
    this.onTap,
    this.enabled = true,
    this.canHold = true,
    this.resetToken,
    this.cancelBelow = false,
    this.cancelLeft = false,
    this.initiallyHeld = false,
    this.cancelArea,
  });
  final bool enabled, canHold;
  final Object? resetToken;
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
  State<HoldControl> createState() => _HoldControlState();
}

class _HoldControlState extends State<HoldControl>
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
        : Rect.fromLTRB(
            0,
            targetBox.globalToLocal(nav.topLeft).dy,
            targetBox.size.width,
            targetBox.globalToLocal(nav.bottomRight).dy,
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

  @override
  void didUpdateWidget(HoldControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.resetToken != widget.resetToken && holding) {
      holding = false;
      _reveal.stop();
      _overlay.hide();
    }
  }

  void _begin() {
    if (!widget.enabled || !widget.canHold) return;
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
            onTap: widget.enabled ? widget.onTap : null,
            onLongPressStart: (widget.enabled && widget.canHold) || holding
                ? (_) => _begin()
                : null,
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
