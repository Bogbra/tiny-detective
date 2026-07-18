import 'package:flutter/material.dart';

import '../application/case_generation_view_model.dart';
import 'generation_progress_checklist.dart';

/// Purely presentational — reflects viewModel.state as-is. Reacting to a
/// successful generation (handing the new case to CasePlayViewModel) is the
/// parent screen's job (a ChangeNotifier listener, not a build()-time side
/// effect) — see case_play_screen.dart.
class GenerateCaseButton extends StatelessWidget {
  const GenerateCaseButton({super.key, required this.viewModel});

  final CaseGenerationViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    switch (viewModel.state) {
      case CaseGenerationState.idle:
      case CaseGenerationState.success:
        return OutlinedButton.icon(
          onPressed: viewModel.start,
          icon: const Icon(Icons.auto_awesome),
          label: const Text('Generate a new case'),
        );

      case CaseGenerationState.inProgress:
        return Card(
          margin: EdgeInsets.zero,
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: GenerationProgressChecklist(viewModel: viewModel),
          ),
        );

      case CaseGenerationState.quotaExhausted:
        return _Message(
          icon: Icons.hourglass_bottom,
          text:
              "Today's free-generation limit is reached — come back tomorrow, "
              'or keep playing the case you already have.',
          onDismiss: viewModel.reset,
        );

      case CaseGenerationState.pipelineFailed:
        return _Message(
          icon: Icons.refresh,
          text: viewModel.errorMessage ?? 'Could not generate a valid case this time.',
          onDismiss: viewModel.reset,
          onRetry: viewModel.start,
        );

      case CaseGenerationState.networkError:
        return _Message(
          icon: Icons.wifi_off,
          text: viewModel.errorMessage ?? 'Something went wrong.',
          onDismiss: viewModel.reset,
          onRetry: viewModel.start,
        );
    }
  }
}

class _Message extends StatelessWidget {
  const _Message({required this.icon, required this.text, required this.onDismiss, this.onRetry});

  final IconData icon;
  final String text;
  final VoidCallback onDismiss;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            Icon(icon),
            const SizedBox(width: 8),
            Expanded(child: Text(text)),
            if (onRetry != null)
              TextButton(onPressed: onRetry, child: const Text('Retry')),
            IconButton(onPressed: onDismiss, icon: const Icon(Icons.close)),
          ],
        ),
      ),
    );
  }
}
