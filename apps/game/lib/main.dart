import 'app.dart';
import 'bootstrap.dart';
import 'features/case_generation/data/case_generation_api_client.dart';
import 'features/case_generation/data/case_generation_repository_impl.dart';
import 'features/case_play/data/case_api_client.dart';
import 'features/case_play/data/case_repository_impl.dart';

void main() {
  bootstrap(
    () => TinyDetectiveApp(
      caseRepository: CaseRepositoryImpl(CaseApiClient()),
      caseGenerationRepository: CaseGenerationRepositoryImpl(
        CaseGenerationApiClient(),
      ),
    ),
  );
}
