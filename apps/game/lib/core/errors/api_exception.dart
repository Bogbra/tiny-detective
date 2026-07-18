import 'dart:convert';

class ApiException implements Exception {
  const ApiException(this.statusCode, this.message);

  /// The backend's error bodies are JSON (`{"detail": "..."}`, FastAPI's
  /// default `HTTPException` shape) — displaying that raw JSON string as
  /// player-facing text (as `ApiException(statusCode, response.body)` used
  /// to do at both call sites) is a bug, not a style choice. This extracts
  /// just the human-readable `detail` field; falls back to the raw body
  /// only if it isn't the expected shape at all, so nothing is silently
  /// swallowed.
  factory ApiException.fromResponseBody(int statusCode, String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic> && decoded['detail'] is String) {
        return ApiException(statusCode, decoded['detail'] as String);
      }
    } catch (_) {
      // Not JSON, or not the expected shape — fall through to the raw body.
    }
    return ApiException(statusCode, body);
  }

  final int statusCode;
  final String message;

  @override
  String toString() => 'ApiException($statusCode): $message';
}
