import 'package:flutter/material.dart';

import '../domain/clue.dart';

class ClueBoard extends StatelessWidget {
  const ClueBoard({super.key, required this.clues});

  final List<Clue> clues;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Clues', style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (final clue in clues)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.search, size: 18),
                const SizedBox(width: 8),
                Expanded(child: Text(clue.text)),
              ],
            ),
          ),
      ],
    );
  }
}
