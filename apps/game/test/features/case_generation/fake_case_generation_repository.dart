import 'package:game/features/case_generation/application/case_generation_repository.dart';
import 'package:game/features/case_generation/domain/generation_event.dart';

/// Hand-rolled test double — no mocking package, matching
/// FakeCaseRepository's style. generateCase() returns whatever stream
/// `eventsToEmit` currently holds; tests build that stream with a
/// StreamController when they need to control timing/errors precisely, or
/// just pass a pre-built Stream.fromIterable for a fixed sequence.
class FakeCaseGenerationRepository implements CaseGenerationRepository {
  FakeCaseGenerationRepository({Stream<GenerationEvent>? events})
    : events = events ?? const Stream.empty();

  Stream<GenerationEvent> events;
  int calls = 0;

  @override
  Stream<GenerationEvent> generateCase() {
    calls += 1;
    return events;
  }
}
