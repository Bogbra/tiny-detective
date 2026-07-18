import 'package:flutter_test/flutter_test.dart';
import 'package:game/core/theme/app_colors.dart';
import 'package:game/core/theme/app_theme.dart';

void main() {
  test('every named text style is at least 16px', () {
    final textTheme = buildAppTheme().textTheme;
    final styles = {
      'displayLarge': textTheme.displayLarge,
      'displayMedium': textTheme.displayMedium,
      'displaySmall': textTheme.displaySmall,
      'headlineLarge': textTheme.headlineLarge,
      'headlineMedium': textTheme.headlineMedium,
      'headlineSmall': textTheme.headlineSmall,
      'titleLarge': textTheme.titleLarge,
      'titleMedium': textTheme.titleMedium,
      'titleSmall': textTheme.titleSmall,
      'bodyLarge': textTheme.bodyLarge,
      'bodyMedium': textTheme.bodyMedium,
      'bodySmall': textTheme.bodySmall,
      'labelLarge': textTheme.labelLarge,
      'labelMedium': textTheme.labelMedium,
      'labelSmall': textTheme.labelSmall,
    };

    for (final entry in styles.entries) {
      expect(
        entry.value?.fontSize,
        greaterThanOrEqualTo(16),
        reason: '${entry.key} is smaller than 16px',
      );
    }
  });

  test('text styles use the Avenir Next font family', () {
    final textTheme = buildAppTheme().textTheme;
    expect(textTheme.bodyLarge?.fontFamily, 'Avenir Next');
  });

  test('scaffold and app bar use the exact specified background color', () {
    final theme = buildAppTheme();
    expect(theme.scaffoldBackgroundColor, AppColors.background);
    expect(theme.appBarTheme.backgroundColor, AppColors.background);
  });

  test('app colors match the exact specified hex values', () {
    expect(AppColors.background.toARGB32(), 0xFF070600);
    expect(AppColors.onBackground.toARGB32(), 0xFFFFFAFF);
    expect(AppColors.selectedSuspect.toARGB32(), 0xFF683257);
    expect(AppColors.success.toARGB32(), 0xFF60992D);
    expect(AppColors.failure.toARGB32(), 0xFFF93943);
  });
}
