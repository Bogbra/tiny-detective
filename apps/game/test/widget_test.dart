import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/app.dart';

import 'features/case_generation/fake_case_generation_repository.dart';
import 'features/case_play/presentation/fake_case_repository.dart';
import 'features/case_play/presentation/sample_case.dart';

void main() {
  testWidgets('app boots and renders the daily case end to end', (tester) async {
    final repository = FakeCaseRepository(dailyCase: sampleCase());

    await tester.pumpWidget(
      TinyDetectiveApp(
        caseRepository: repository,
        caseGenerationRepository: FakeCaseGenerationRepository(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('The Missing Museum Key'), findsOneWidget);
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
