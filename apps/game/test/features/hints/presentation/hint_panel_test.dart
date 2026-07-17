import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/features/hints/domain/hint_state.dart';
import 'package:game/features/hints/presentation/hint_panel.dart';

void main() {
  testWidgets('shows a request button when no hint has been requested yet', (tester) async {
    var requested = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HintPanel(hint: null, isLoading: false, onRequestHint: () => requested = true),
        ),
      ),
    );

    expect(find.text('Get a hint'), findsOneWidget);

    await tester.tap(find.text('Get a hint'));
    expect(requested, isTrue);
  });

  testWidgets('shows hint text and remaining count once a hint exists', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HintPanel(
            hint: const HintState(text: 'Look closely.', hintsUsed: 1, hintsRemaining: 2),
            isLoading: false,
            onRequestHint: () {},
          ),
        ),
      ),
    );

    expect(find.text('Look closely.'), findsOneWidget);
    expect(find.text('2 hint(s) remaining'), findsOneWidget);
    expect(find.text('Get another hint'), findsOneWidget);
  });

  testWidgets('disables the button once hints are exhausted', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: HintPanel(
            hint: const HintState(text: 'Last hint.', hintsUsed: 3, hintsRemaining: 0),
            isLoading: false,
            onRequestHint: () {},
          ),
        ),
      ),
    );

    final button = tester.widget<OutlinedButton>(find.byType(OutlinedButton));
    expect(button.onPressed, isNull);
  });
}
