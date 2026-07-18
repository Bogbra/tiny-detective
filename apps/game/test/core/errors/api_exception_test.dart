import 'package:flutter_test/flutter_test.dart';
import 'package:game/core/errors/api_exception.dart';

void main() {
  test('extracts the detail field from a FastAPI-shaped error body', () {
    final exception = ApiException.fromResponseBody(
      404,
      '{"detail":"no daily case is currently published"}',
    );

    expect(exception.message, 'no daily case is currently published');
    expect(exception.statusCode, 404);
  });

  test('falls back to the raw body when it is not JSON', () {
    final exception = ApiException.fromResponseBody(
      500,
      'Internal Server Error',
    );

    expect(exception.message, 'Internal Server Error');
  });

  test('falls back to the raw body when JSON has no detail field', () {
    final exception = ApiException.fromResponseBody(
      400,
      '{"error":"something else"}',
    );

    expect(exception.message, '{"error":"something else"}');
  });
}
