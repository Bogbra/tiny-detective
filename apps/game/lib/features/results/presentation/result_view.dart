import 'package:flutter/material.dart';

import '../domain/case_result.dart';

class ResultView extends StatelessWidget {
  const ResultView({super.key, required this.result});

  final CaseResult result;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              result.correct ? Icons.check_circle : Icons.cancel,
              color: result.correct ? Colors.green : Colors.red,
              size: 64,
            ),
            const SizedBox(height: 16),
            Text(
              result.correct ? 'Case solved!' : 'Not quite.',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 8),
            Text(result.feedback, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            Text(result.solutionExplanation, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            Text('Score: ${result.score}   Streak: ${result.streak}'),
          ],
        ),
      ),
    );
  }
}
