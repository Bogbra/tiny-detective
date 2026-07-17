class ApiConfig {
  const ApiConfig._();

  /// Override at build time with --dart-define=API_BASE_URL=... (used from
  /// Phase 8 onward for the deployed backend URL).
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );
}
