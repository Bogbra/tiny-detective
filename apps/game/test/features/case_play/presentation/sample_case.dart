import 'package:game/features/case_play/domain/detective_case.dart';
import 'package:game/features/clues/domain/clue.dart';
import 'package:game/features/suspects/domain/suspect.dart';

/// Mirrors the backend's seeded "museum key" case (the project spec's "Public
/// Case Response Example" / services/api/app/infrastructure/seed_data.py) so
/// frontend and backend fixtures stay recognizable against each other.
DetectiveCase sampleCase() {
  return const DetectiveCase(
    caseId: 'case_museum_001',
    title: 'The Missing Museum Key',
    setting: 'A small town museum after closing time.',
    problem: 'An old display key disappeared from a locked glass case.',
    suspects: [
      Suspect(
        suspectId: 'suspect_1',
        name: 'Mara',
        role: 'Curator',
        publicStatement: 'I was checking inventory in the archive.',
      ),
      Suspect(
        suspectId: 'suspect_2',
        name: 'Jonas',
        role: 'Night Guard',
        publicStatement: 'I heard a noise near the east hallway.',
      ),
      Suspect(
        suspectId: 'suspect_3',
        name: 'Lea',
        role: 'Visitor',
        publicStatement: 'I only came back because I lost my phone.',
      ),
    ],
    clues: [
      Clue(
        clueId: 'clue_1',
        text: 'A visitor wristband was found near the display case.',
      ),
      Clue(clueId: 'clue_2', text: 'There were no signs of forced entry.'),
      Clue(
        clueId: 'clue_3',
        text: 'The archive motion sensor stayed inactive.',
      ),
    ],
    difficulty: 'easy',
  );
}
