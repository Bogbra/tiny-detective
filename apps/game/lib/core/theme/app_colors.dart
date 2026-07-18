import 'package:flutter/material.dart';

/// Fixed design colors — given as exact hex values, not a Material seed to
/// generate a palette from. Kept in one place so every usage site (the app
/// theme, suspect selection, success/fail indicators) references the same
/// named constant instead of repeating a hex literal.
class AppColors {
  const AppColors._();

  static const background = Color(0xFF070600);
  static const onBackground = Color(0xFFFFFAFF);
  static const selectedSuspect = Color(0xFF683257);
  static const success = Color(0xFF60992D);
  static const failure = Color(0xFFF93943);
}
