import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:game/features/suspects/domain/suspect.dart';
import 'package:game/features/suspects/presentation/suspect_card.dart';

void main() {
  const suspect = Suspect(
    suspectId: 'suspect_1',
    name: 'Mara',
    role: 'Curator',
    publicStatement: 'I was checking inventory in the archive.',
  );

  testWidgets('renders suspect name, role and statement', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: SuspectCard(suspect: suspect, isSelected: false, onTap: () {}),
      ),
    );

    expect(find.text('Mara'), findsOneWidget);
    expect(find.textContaining('Curator'), findsOneWidget);
    expect(find.textContaining('checking inventory'), findsOneWidget);
    expect(find.byIcon(Icons.check_circle), findsNothing);
  });

  testWidgets('shows a check icon when selected and calls onTap when tapped', (
    tester,
  ) async {
    var tapped = false;

    await tester.pumpWidget(
      MaterialApp(
        home: SuspectCard(
          suspect: suspect,
          isSelected: true,
          onTap: () => tapped = true,
        ),
      ),
    );

    expect(find.byIcon(Icons.check_circle), findsOneWidget);

    await tester.tap(find.byType(SuspectCard));
    expect(tapped, isTrue);
  });
}
