import 'package:flutter/material.dart';

import '../application/case_generation_view_model.dart';

const _stepLabels = [
  ('generating', 'Generating case…'),
  ('logic_check', 'Checking logical solvability…'),
  ('safety_check', 'Checking content safety…'),
];

/// A live checklist driven entirely by real backend events (see
/// CaseGenerationViewModel) — no timer, no synthetic progress. A rejection
/// followed by a real restart resets these rows back to pending, which is
/// what actually makes the restart visible rather than assumed.
class GenerationProgressChecklist extends StatelessWidget {
  const GenerationProgressChecklist({super.key, required this.viewModel});

  final CaseGenerationViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          viewModel.attempt == 1 ? 'Generating…' : 'Attempt ${viewModel.attempt}',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        const SizedBox(height: 8),
        for (final (step, label) in _stepLabels)
          _StepRow(label: label, status: viewModel.stepStatuses[step]),
        if (viewModel.lastRejectionDetail != null) ...[
          const SizedBox(height: 8),
          Text(
            viewModel.lastRejectionDetail!,
            style: Theme.of(
              context,
            ).textTheme.bodySmall?.copyWith(color: Theme.of(context).colorScheme.error),
          ),
        ],
      ],
    );
  }
}

class _StepRow extends StatelessWidget {
  const _StepRow({required this.label, required this.status});

  final String label;
  final String? status;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(width: 20, height: 20, child: _statusIcon(status)),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
    );
  }

  Widget _statusIcon(String? status) {
    switch (status) {
      case 'running':
        return const CircularProgressIndicator(strokeWidth: 2);
      case 'passed':
        return const Icon(Icons.check_circle, color: Colors.green, size: 20);
      case 'rejected':
        return const Icon(Icons.cancel, color: Colors.red, size: 20);
      default:
        return const Icon(Icons.circle_outlined, size: 20);
    }
  }
}
