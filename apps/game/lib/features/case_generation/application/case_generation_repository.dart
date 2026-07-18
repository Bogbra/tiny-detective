import '../domain/generation_event.dart';

abstract class CaseGenerationRepository {
  Stream<GenerationEvent> generateCase();
}
