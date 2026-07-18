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
      alreadySolved: false,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));
    // The score/streak line counts up over 800ms (see _AnimatedScoreLine) —
    // let it finish before asserting the final numbers. Deliberately not
    // pumpAndSettle(): ConfettiWidget's particle simulation keeps scheduling
    // frames for its own duration and never fully "settles" within
    // pumpAndSettle's timeout, a known characteristic of physics-based
    // confetti animations, not a bug in this widget.
    await tester.pump(const Duration(milliseconds: 900));

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
      alreadySolved: false,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));

    expect(find.text('Not quite.'), findsOneWidget);
  });

  testWidgets('a streak multiple of 3 shows the milestone message', (tester) async {
    const result = CaseResult(
      correct: true,
      score: 100,
      feedback: 'Correct.',
      solutionExplanation: 'Lea was near the case after closing.',
      streak: 3,
      alreadySolved: false,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));
    await tester.pump(const Duration(milliseconds: 900));

    expect(find.textContaining('streak!'), findsOneWidget);
  });

  testWidgets('a non-milestone streak shows no milestone message', (tester) async {
    const result = CaseResult(
      correct: true,
      score: 100,
      feedback: 'Correct.',
      solutionExplanation: 'Lea was near the case after closing.',
      streak: 2,
      alreadySolved: false,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));
    await tester.pump(const Duration(milliseconds: 900));

    expect(find.textContaining('streak!'), findsNothing);
  });

  testWidgets('an already-solved resubmission shows no milestone message even at a streak multiple of 3', (
    tester,
  ) async {
    const result = CaseResult(
      correct: true,
      score: 0,
      feedback: 'Correct.',
      solutionExplanation: 'Lea was near the case after closing.',
      streak: 3,
      alreadySolved: true,
    );

    await tester.pumpWidget(const MaterialApp(home: ResultView(result: result)));
    await tester.pump(const Duration(milliseconds: 900));

    // Score/streak still display honestly (they're real, current values),
    // but no celebratory milestone banner — nothing new was actually
    // earned by resubmitting.
    expect(find.textContaining('streak!'), findsNothing);
  });
}
