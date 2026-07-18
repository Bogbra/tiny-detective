import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/features/case_generation/application/case_generation_view_model.dart';
import 'package:game/features/case_generation/domain/generation_event.dart';
import 'package:game/features/case_generation/presentation/generate_case_button.dart';
import 'package:game/features/case_play/domain/detective_case.dart';

import '../fake_case_generation_repository.dart';

Widget _wrap(CaseGenerationViewModel viewModel) {
  return MaterialApp(
    home: Scaffold(
      body: ListenableBuilder(
        listenable: viewModel,
        builder: (context, _) => GenerateCaseButton(viewModel: viewModel),
      ),
    ),
  );
}

DetectiveCase _sample() => const DetectiveCase(
  caseId: 'case_live_abc',
  title: 'The Generated Case',
  setting: 'A setting.',
  problem: 'A problem.',
  suspects: [],
  clues: [],
  difficulty: 'easy',
);

void main() {
  testWidgets('idle state shows the generate button', (tester) async {
    final repository = FakeCaseGenerationRepository();
    final viewModel = CaseGenerationViewModel(repository);

    await tester.pumpWidget(_wrap(viewModel));

    expect(find.text('Generate a new case'), findsOneWidget);
  });

  testWidgets(
    'shows the live checklist and a visible restart after a rejection',
    (tester) async {
      final controller = StreamController<GenerationEvent>();
      final repository = FakeCaseGenerationRepository(
        events: controller.stream,
      );
      final viewModel = CaseGenerationViewModel(repository);

      await tester.pumpWidget(_wrap(viewModel));
      await tester.tap(find.text('Generate a new case'));
      await tester.pump();

      controller.add(
        const GenerationEvent(
          step: 'generating',
          status: 'running',
          attempt: 1,
        ),
      );
      await tester.pump();
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      controller.add(
        const GenerationEvent(step: 'generating', status: 'passed', attempt: 1),
      );
      controller.add(
        const GenerationEvent(
          step: 'logic_check',
          status: 'running',
          attempt: 1,
        ),
      );
      controller.add(
        const GenerationEvent(
          step: 'logic_check',
          status: 'rejected',
          detail: 'solution not supported by clues',
          attempt: 1,
        ),
      );
      await tester.pump();

      // The raw backend detail ("solution not supported by clues") must NOT
      // appear — it's AI-judge/fidelity-check internal reasoning, not
      // player-facing text. A fixed, friendly message is shown instead.
      expect(
        find.textContaining('solution not supported by clues'),
        findsNothing,
      );
      expect(
        find.textContaining("didn't pass our quality check"),
        findsOneWidget,
      );
      expect(find.byIcon(Icons.cancel), findsOneWidget);

      // The real restart: a fresh "generating: running" for attempt 2.
      controller.add(
        const GenerationEvent(
          step: 'generating',
          status: 'running',
          attempt: 2,
        ),
      );
      await tester.pump();

      expect(find.text('Attempt 2'), findsOneWidget);
      // The checklist reset for the new attempt — no leftover "rejected" icon
      // from attempt 1's logic_check, since that row's status was cleared.
      expect(find.byIcon(Icons.cancel), findsNothing);

      await controller.close();
    },
  );

  testWidgets(
    'quota exhausted shows a clear message with a dismiss action, not a dead end',
    (tester) async {
      final controller = StreamController<GenerationEvent>();
      final repository = FakeCaseGenerationRepository(
        events: controller.stream,
      );
      final viewModel = CaseGenerationViewModel(repository);

      await tester.pumpWidget(_wrap(viewModel));
      await tester.tap(find.text('Generate a new case'));
      await tester.pump();

      controller.add(
        const GenerationEvent(
          step: 'quota_check',
          status: 'rejected',
          detail: 'daily generation quota reached',
        ),
      );
      await tester.pump();

      expect(
        find.textContaining('generation limit is reached'),
        findsOneWidget,
      );
      expect(find.textContaining('keep playing'), findsOneWidget);

      await tester.tap(find.byIcon(Icons.close));
      await tester.pump();
      expect(find.text('Generate a new case'), findsOneWidget);

      await controller.close();
    },
  );

  testWidgets('pipeline exhaustion offers a retry, not a hang', (tester) async {
    final controller = StreamController<GenerationEvent>();
    final repository = FakeCaseGenerationRepository(events: controller.stream);
    final viewModel = CaseGenerationViewModel(repository);

    await tester.pumpWidget(_wrap(viewModel));
    await tester.tap(find.text('Generate a new case'));
    await tester.pump();

    controller.add(
      const GenerationEvent(
        step: 'failed',
        status: 'done',
        detail: 'could not generate a valid case after 5 attempts',
      ),
    );
    await tester.pump();

    expect(
      find.textContaining('could not generate a valid case'),
      findsOneWidget,
    );
    expect(find.text('Retry'), findsOneWidget);

    await controller.close();
  });

  testWidgets('a successful generation is reflected in generatedCase', (
    tester,
  ) async {
    final controller = StreamController<GenerationEvent>();
    final repository = FakeCaseGenerationRepository(events: controller.stream);
    final viewModel = CaseGenerationViewModel(repository);

    await tester.pumpWidget(_wrap(viewModel));
    await tester.tap(find.text('Generate a new case'));
    await tester.pump();

    controller.add(
      GenerationEvent(step: 'saving', status: 'done', generatedCase: _sample()),
    );
    await tester.pump();

    expect(viewModel.state, CaseGenerationState.success);
    expect(viewModel.generatedCase?.title, 'The Generated Case');

    await controller.close();
  });
}
