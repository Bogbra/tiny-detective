import 'app.dart';
import 'bootstrap.dart';
import 'features/case_play/data/case_api_client.dart';
import 'features/case_play/data/case_repository_impl.dart';

void main() {
  bootstrap(() => TinyDetectiveApp(caseRepository: CaseRepositoryImpl(CaseApiClient())));
}
