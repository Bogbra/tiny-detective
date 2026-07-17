import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/features/results/domain/case_result.dart';
import 'package:game/features/results/presentation/result_view.dart';

void main() {
  testWidgets('displays score, streak, feedback and explanation', (tester) async {
    const result = CaseResult(
      correct: true,
      score: 85,
      feedback: 'Correct.',
      solutionExplanation: 'Lea was near the case after closing.',
      streak: 2,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));

    expect(find.text('Case solved!'), findsOneWidget);
    expect(find.text('Correct.'), findsOneWidget);
    expect(find.text('Lea was near the case after closing.'), findsOneWidget);
    expect(find.textContaining('Score: 85'), findsOneWidget);
    expect(find.textContaining('Streak: 2'), findsOneWidget);
  });

  testWidgets('shows an incorrect result distinctly', (tester) async {
    const result = CaseResult(
      correct: false,
      score: 0,
      feedback: 'Not quite — review the clues again.',
      solutionExplanation: 'Lea was near the case after closing.',
      streak: 0,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));

    expect(find.text('Not quite.'), findsOneWidget);
  });
}
