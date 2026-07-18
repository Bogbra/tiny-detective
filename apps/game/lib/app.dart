import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';
import 'features/case_generation/application/case_generation_repository.dart';
import 'features/case_play/application/case_play_view_model.dart';
import 'features/case_play/application/case_repository.dart';
import 'features/case_play/presentation/case_play_screen.dart';

class TinyDetectiveApp extends StatelessWidget {
  const TinyDetectiveApp({
    super.key,
    required this.caseRepository,
    required this.caseGenerationRepository,
  });

  final CaseRepository caseRepository;
  final CaseGenerationRepository caseGenerationRepository;

  @override
  Widget build(BuildContext context) {
    final theme = buildAppTheme();
    return MaterialApp(
      title: 'Tiny Detective',
      theme: theme,
      darkTheme: theme,
      themeMode: ThemeMode.dark,
      home: CasePlayScreen(
        viewModel: CasePlayViewModel(caseRepository),
        caseGenerationRepository: caseGenerationRepository,
      ),
    );
  }
}
