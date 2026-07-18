import 'package:flutter/material.dart';

import '../../case_generation/application/case_generation_repository.dart';
import '../../case_generation/application/case_generation_view_model.dart';
import '../../case_generation/presentation/generate_case_button.dart';
import '../../clues/presentation/clue_board.dart';
import '../../hints/presentation/hint_panel.dart';
import '../../results/presentation/result_view.dart';
import '../../suspects/presentation/suspect_card.dart';
import '../application/case_play_view_model.dart';
import 'solution_submit_button.dart';

class CasePlayScreen extends StatefulWidget {
  const CasePlayScreen({
    super.key,
    required this.viewModel,
    required this.caseGenerationRepository,
  });

  final CasePlayViewModel viewModel;
  final CaseGenerationRepository caseGenerationRepository;

  @override
  State<CasePlayScreen> createState() => _CasePlayScreenState();
}

class _CasePlayScreenState extends State<CasePlayScreen> {
  late final CaseGenerationViewModel _generationViewModel;

  @override
  void initState() {
    super.initState();
    widget.viewModel.start();
    _generationViewModel = CaseGenerationViewModel(
      widget.caseGenerationRepository,
    );
    _generationViewModel.addListener(_onGenerationChanged);
  }

  @override
  void dispose() {
    _generationViewModel.removeListener(_onGenerationChanged);
    _generationViewModel.dispose();
    super.dispose();
  }

  /// A ChangeNotifier-listener side effect, deliberately not inline in
  /// build() — swapping in the generated case and resetting the generation
  /// view model are state mutations, not something a build() method should
  /// trigger as a side effect of being called.
  void _onGenerationChanged() {
    final generated = _generationViewModel.generatedCase;
    if (_generationViewModel.state == CaseGenerationState.success &&
        generated != null) {
      widget.viewModel.loadGeneratedCase(generated);
      _generationViewModel.reset();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Tiny Detective')),
      body: SafeArea(
        child: ListenableBuilder(
          listenable: Listenable.merge([
            widget.viewModel,
            _generationViewModel,
          ]),
          builder: (context, _) => _buildBody(context, widget.viewModel),
        ),
      ),
    );
  }

  Widget _buildBody(BuildContext context, CasePlayViewModel viewModel) {
    switch (viewModel.status) {
      case CasePlayStatus.loading:
        return const Center(child: CircularProgressIndicator());
      case CasePlayStatus.error:
        return _ErrorView(
          message: viewModel.errorMessage ?? 'Something went wrong.',
          onRetry: viewModel.start,
        );
      case CasePlayStatus.solved:
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              ResultView(result: viewModel.result!),
              const SizedBox(height: 24),
              GenerateCaseButton(viewModel: _generationViewModel),
            ],
          ),
        );
      case CasePlayStatus.playing:
        return _PlayingView(viewModel: viewModel);
    }
  }
}

class _PlayingView extends StatelessWidget {
  const _PlayingView({required this.viewModel});

  final CasePlayViewModel viewModel;

  @override
  Widget build(BuildContext context) {
    final detectiveCase = viewModel.detectiveCase!;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            detectiveCase.title,
            style: Theme.of(context).textTheme.headlineSmall,
          ),
          const SizedBox(height: 4),
          Text(detectiveCase.setting),
          const SizedBox(height: 8),
          Text(detectiveCase.problem),
          const SizedBox(height: 16),
          ClueBoard(clues: detectiveCase.clues),
          const SizedBox(height: 16),
          Text('Suspects', style: Theme.of(context).textTheme.titleMedium),
          for (final suspect in detectiveCase.suspects)
            SuspectCard(
              suspect: suspect,
              isSelected: viewModel.selectedSuspectId == suspect.suspectId,
              onTap: () => viewModel.selectSuspect(suspect.suspectId),
            ),
          const SizedBox(height: 16),
          HintPanel(
            hint: viewModel.hint,
            isLoading: viewModel.isRequestingHint,
            onRequestHint: viewModel.requestHint,
          ),
          const SizedBox(height: 16),
          if (viewModel.errorMessage != null) ...[
            Text(
              viewModel.errorMessage!,
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            const SizedBox(height: 8),
          ],
          SolutionSubmitButton(
            enabled: viewModel.selectedSuspectId != null,
            isSubmitting: viewModel.isSubmitting,
            onPressed: viewModel.submitSolution,
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, size: 48),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
