import 'package:flutter/material.dart';

import '../domain/hint_state.dart';

class HintPanel extends StatelessWidget {
  const HintPanel({
    super.key,
    required this.hint,
    required this.isLoading,
    required this.onRequestHint,
  });

  final HintState? hint;
  final bool isLoading;
  final VoidCallback onRequestHint;

  @override
  Widget build(BuildContext context) {
    final exhausted = hint != null && !hint!.canRequestMore;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (hint != null) ...[
          Text(hint!.text, style: Theme.of(context).textTheme.bodyMedium),
          const SizedBox(height: 4),
          Text(
            '${hint!.hintsRemaining} hint(s) remaining',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 8),
        ],
        OutlinedButton.icon(
          onPressed: (isLoading || exhausted) ? null : onRequestHint,
          icon: const Icon(Icons.lightbulb_outline),
          label: Text(hint == null ? 'Get a hint' : 'Get another hint'),
        ),
      ],
    );
  }
}
