import 'package:flutter/material.dart';

import 'features/case_play/application/case_play_view_model.dart';
import 'features/case_play/application/case_repository.dart';
import 'features/case_play/presentation/case_play_screen.dart';

class TinyDetectiveApp extends StatelessWidget {
  const TinyDetectiveApp({super.key, required this.caseRepository});

  final CaseRepository caseRepository;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Tiny Detective',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
        useMaterial3: true,
      ),
      home: CasePlayScreen(viewModel: CasePlayViewModel(caseRepository)),
    );
  }
}
