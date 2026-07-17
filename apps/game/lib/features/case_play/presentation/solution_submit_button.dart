import 'package:flutter/material.dart';

class SolutionSubmitButton extends StatelessWidget {
  const SolutionSubmitButton({
    super.key,
    required this.enabled,
    required this.isSubmitting,
    required this.onPressed,
  });

  final bool enabled;
  final bool isSubmitting;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: (enabled && !isSubmitting) ? onPressed : null,
      child: isSubmitting
          ? const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          : const Text('Submit accusation'),
    );
  }
}
