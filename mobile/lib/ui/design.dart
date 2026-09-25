import 'package:flutter/material.dart';

/// Desktop dashboard/src/styles/tokens.css. Light is its contrast-adjusted companion.
abstract final class StudioColors {
  static const background = Color(0xff151619);
  static const panel = Color(0xff202226);
  static const line = Color(0xff363940);
  static const teal = Color(0xff80d1cb);
  static const agent = Color(0xffadb6f5);
  static const ink = Color(0xffedeef0);
  static const muted = Color(0xffa3a8b2);
  static Color accent(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? teal
      : const Color(0xff287a75);
  static Color agentAccent(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
      ? agent
      : const Color(0xff5e69aa);
}

ThemeData studioTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme =
      ColorScheme.fromSeed(
        seedColor: StudioColors.teal,
        brightness: brightness,
      ).copyWith(
        primary: dark ? StudioColors.teal : const Color(0xff287a75),
        onPrimary: const Color(0xff122b29),
        surface: dark ? StudioColors.panel : Colors.white,
        onSurface: dark ? StudioColors.ink : const Color(0xff202226),
        outline: dark ? StudioColors.line : const Color(0xffd9dce1),
        secondary: dark ? StudioColors.agent : const Color(0xff5e69aa),
      );
  return ThemeData(
    colorScheme: scheme,
    scaffoldBackgroundColor: dark
        ? StudioColors.background
        : const Color(0xfff3f4f6),
    fontFamily: 'Studio Sans',
    useMaterial3: true,
    appBarTheme: AppBarTheme(
      backgroundColor: dark ? StudioColors.background : const Color(0xfff3f4f6),
      surfaceTintColor: Colors.transparent,
      titleTextStyle: TextStyle(
        fontFamily: 'Studio Sans',
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: scheme.onSurface,
      ),
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: scheme.surface,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: scheme.outline),
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: dark ? const Color(0xff1b1d21) : Colors.white,
      indicatorColor: scheme.primary.withValues(alpha: .12),
      height: 68,
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        minimumSize: const Size(48, 46),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: scheme.onSurface,
        side: BorderSide(color: scheme.outline),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        minimumSize: const Size(48, 44),
      ),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(minimumSize: const Size(48, 44)),
    ),
    dividerTheme: DividerThemeData(color: scheme.outline),
  );
}

class Eyebrow extends StatelessWidget {
  const Eyebrow(this.text, {super.key, this.color});
  final String text;
  final Color? color;
  @override
  Widget build(BuildContext context) => Text(
    text.toUpperCase(),
    style: TextStyle(
      fontSize: 10,
      letterSpacing: 1.2,
      fontWeight: FontWeight.w600,
      color: color ?? Theme.of(context).colorScheme.onSurfaceVariant,
    ),
  );
}
