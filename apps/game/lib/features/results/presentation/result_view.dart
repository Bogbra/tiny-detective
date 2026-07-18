import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';

import '../../../core/theme/app_colors.dart';
import '../domain/case_result.dart';

/// "Juice" — confetti, a count-up on score/streak, and a brief pulse on the
/// headline — fires once, on mount, and only here: this is the one
/// meaningful moment in the game loop (solving a case), not something
/// applied to every button press. Confetti only plays for a correct
/// answer at all (none for wrong, not even a token amount) — the subtlety
/// the wrong case gets is silence, not a smaller version of the same
/// effect. A streak milestone (every 3rd correct answer) gets a visibly
/// bigger burst, not a separate animation — same mechanism, scaled.
class ResultView extends StatefulWidget {
  const ResultView({super.key, required this.result});

  final CaseResult result;

  @override
  State<ResultView> createState() => _ResultViewState();
}

class _ResultViewState extends State<ResultView> with SingleTickerProviderStateMixin {
  late final ConfettiController _confettiController;
  late final AnimationController _pulseController;
  late final Animation<double> _pulseScale;

  bool get _isMilestone =>
      widget.result.correct && widget.result.streak > 0 && widget.result.streak % 3 == 0;

  @override
  void initState() {
    super.initState();
    _confettiController = ConfettiController(duration: const Duration(milliseconds: 1200));
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 450),
    );
    _pulseScale = Tween<double>(
      begin: 0.7,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _pulseController, curve: Curves.elasticOut));

    _pulseController.forward();
    if (widget.result.correct) {
      _confettiController.play();
    }
  }

  @override
  void dispose() {
    _confettiController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      alignment: Alignment.topCenter,
      children: [
        Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                ScaleTransition(
                  scale: _pulseScale,
                  child: Icon(
                    widget.result.correct ? Icons.check_circle : Icons.cancel,
                    color: widget.result.correct ? AppColors.success : AppColors.failure,
                    size: 64,
                  ),
                ),
                const SizedBox(height: 16),
                ScaleTransition(
                  scale: _pulseScale,
                  child: Text(
                    widget.result.correct ? 'Case solved!' : 'Not quite.',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
                const SizedBox(height: 8),
                Text(widget.result.feedback, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                Text(widget.result.solutionExplanation, textAlign: TextAlign.center),
                const SizedBox(height: 16),
                _AnimatedScoreLine(score: widget.result.score, streak: widget.result.streak),
                if (_isMilestone) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${widget.result.streak}-case streak!',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        ConfettiWidget(
          confettiController: _confettiController,
          blastDirectionality: BlastDirectionality.explosive,
          numberOfParticles: _isMilestone ? 50 : 20,
          maxBlastForce: 20,
          minBlastForce: 8,
          gravity: 0.3,
          shouldLoop: false,
        ),
      ],
    );
  }
}

class _AnimatedScoreLine extends StatelessWidget {
  const _AnimatedScoreLine({required this.score, required this.streak});

  final int score;
  final int streak;

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 800),
      curve: Curves.easeOutCubic,
      builder: (context, t, _) {
        final animatedScore = (score * t).round();
        final animatedStreak = (streak * t).round();
        return Text('Score: $animatedScore   Streak: $animatedStreak');
      },
    );
  }
}
