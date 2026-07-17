import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/features/case_play/application/case_play_view_model.dart';
import 'package:game/features/case_play/presentation/case_play_screen.dart';
import 'package:game/features/hints/domain/hint_state.dart';
import 'package:game/features/results/domain/case_result.dart';

import 'fake_case_repository.dart';
import 'sample_case.dart';

Widget _wrap(FakeCaseRepository repository) {
  return MaterialApp(home: CasePlayScreen(viewModel: CasePlayViewModel(repository)));
}

void main() {
  testWidgets('shows a loading indicator while the daily case loads', (tester) async {
    final repository = FakeCaseRepository(dailyCase: sampleCase());

    await tester.pumpWidget(_wrap(repository));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
  });

  testWidgets('renders the case, suspects and clues once loaded', (tester) async {
    final repository = FakeCaseRepository(dailyCase: sampleCase());

    await tester.pumpWidget(_wrap(repository));
    await tester.pumpAndSettle();

    expect(find.text('The Missing Museum Key'), findsOneWidget);
    expect(find.text('Mara'), findsOneWidget);
    expect(find.text('Jonas'), findsOneWidget);
    expect(find.text('Lea'), findsOneWidget);
    expect(find.textContaining('wristband'), findsOneWidget);
  });

  testWidgets('shows an error state and recovers via retry', (tester) async {
    final repository = FakeCaseRepository(throwOnGetDailyCase: Exception('network down'));

    await tester.pumpWidget(_wrap(repository));
    await tester.pumpAndSettle();

    expect(find.text('Retry'), findsOneWidget);
    expect(find.text('The Missing Museum Key'), findsNothing);

    repository.throwOnGetDailyCase = null;
    repository.dailyCase = sampleCase();
    await tester.tap(find.text('Retry'));
    await tester.pumpAndSettle();

    expect(find.text('The Missing Museum Key'), findsOneWidget);
  });

  testWidgets('requesting a hint shows the returned hint text', (tester) async {
    final repository = FakeCaseRepository(
      dailyCase: sampleCase(),
      hintState: const HintState(
        text: 'Compare each suspect statement with the clues.',
        hintsUsed: 1,
        hintsRemaining: 2,
      ),
    );

    await tester.pumpWidget(_wrap(repository));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Get a hint'));
    await tester.tap(find.text('Get a hint'));
    await tester.pumpAndSettle();

    expect(find.text('Compare each suspect statement with the clues.'), findsOneWidget);
    expect(find.text('2 hint(s) remaining'), findsOneWidget);
    expect(repository.hintCalls, 1);
  });

  testWidgets('selecting a suspect and submitting shows the result screen', (tester) async {
    final repository = FakeCaseRepository(
      dailyCase: sampleCase(),
      result: const CaseResult(
        correct: true,
        score: 100,
        feedback: 'Correct.',
        solutionExplanation: 'Lea was near the case after closing.',
        streak: 1,
      ),
    );

    await tester.pumpWidget(_wrap(repository));
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Lea'));
    await tester.tap(find.text('Lea'));
    await tester.pump();

    await tester.ensureVisible(find.text('Submit accusation'));
    await tester.tap(find.text('Submit accusation'));
    await tester.pumpAndSettle();

    expect(find.text('Case solved!'), findsOneWidget);
    expect(find.textContaining('Score: 100'), findsOneWidget);
    expect(repository.submitCalls, 1);
  });
}
