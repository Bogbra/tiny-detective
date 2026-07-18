import 'package:flutter/material.dart';

import 'app_colors.dart';

const _fontFamily = 'Avenir Next';
const _minFontSize = 16.0;

/// Raises every named text style to at least [_minFontSize] — Material's
/// default text theme has several styles below that (bodySmall/labelSmall
/// etc. default to 11-14px). Styles already at or above the minimum are
/// left untouched rather than forced to a uniform size, so headings still
/// read larger than body text.
TextStyle _atLeastMinSize(TextStyle? style) {
  final base = style ?? const TextStyle();
  final size = base.fontSize ?? _minFontSize;
  return base.copyWith(fontSize: size < _minFontSize ? _minFontSize : size);
}

TextTheme _buildTextTheme(TextTheme base) {
  return base
      .copyWith(
        displayLarge: _atLeastMinSize(base.displayLarge),
        displayMedium: _atLeastMinSize(base.displayMedium),
        displaySmall: _atLeastMinSize(base.displaySmall),
        headlineLarge: _atLeastMinSize(base.headlineLarge),
        headlineMedium: _atLeastMinSize(base.headlineMedium),
        headlineSmall: _atLeastMinSize(base.headlineSmall),
        titleLarge: _atLeastMinSize(base.titleLarge),
        titleMedium: _atLeastMinSize(base.titleMedium),
        titleSmall: _atLeastMinSize(base.titleSmall),
        bodyLarge: _atLeastMinSize(base.bodyLarge),
        bodyMedium: _atLeastMinSize(base.bodyMedium),
        bodySmall: _atLeastMinSize(base.bodySmall),
        labelLarge: _atLeastMinSize(base.labelLarge),
        labelMedium: _atLeastMinSize(base.labelMedium),
        labelSmall: _atLeastMinSize(base.labelSmall),
      )
      .apply(
        fontFamily: _fontFamily,
        bodyColor: AppColors.onBackground,
        displayColor: AppColors.onBackground,
        decorationColor: AppColors.onBackground,
      );
}

/// The app only ever runs in this one theme (see app.dart's
/// `themeMode: ThemeMode.dark`) — a single builder rather than near-duplicate
/// light/dark blocks. Accent colors (buttons, outlines) still come from a
/// Material seed, since the design only specified background/text/selection/
/// success/failure colors, not a full palette; everything it did specify
/// overrides the seed-derived defaults explicitly.
ThemeData buildAppTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: Colors.deepPurple,
    brightness: Brightness.dark,
  ).copyWith(surface: AppColors.background, onSurface: AppColors.onBackground);

  final base = ThemeData(colorScheme: colorScheme, useMaterial3: true);

  return base.copyWith(
    scaffoldBackgroundColor: AppColors.background,
    textTheme: _buildTextTheme(base.textTheme),
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.onBackground,
      // Material 3 blends in colorScheme.surfaceTint once content is
      // scrolled under the app bar by default (scrolledUnderElevation),
      // which visibly shifts the exact background color on scroll unless
      // disabled here — found by scrolling in a real browser check, not
      // by reading the color values in isolation.
      surfaceTintColor: Colors.transparent,
    ),
  );
}
