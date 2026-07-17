import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/features/clues/domain/clue.dart';
import 'package:game/features/clues/presentation/clue_board.dart';

void main() {
  testWidgets('renders every clue text', (tester) async {
    const clues = [
      Clue(clueId: 'clue_1', text: 'A visitor wristband was found near the display case.'),
      Clue(clueId: 'clue_2', text: 'There were no signs of forced entry.'),
    ];

    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: ClueBoard(clues: clues))));

    expect(find.text('A visitor wristband was found near the display case.'), findsOneWidget);
    expect(find.text('There were no signs of forced entry.'), findsOneWidget);
  });
}
