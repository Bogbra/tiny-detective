import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config/api_config.dart';
import '../../../core/errors/api_exception.dart';
import 'dtos/generation_event_dto.dart';

/// The one place in this app that reads a chunked text/event-stream HTTP
/// body — nothing here uses the browser's native EventSource (GET-only;
/// irrelevant since Flutter Web never touches it) or any SSE package. POST
/// works fine for a hand-parsed SSE body: split on line breaks, take lines
/// starting with "data: ", decode the JSON. The backend only ever emits one
/// single-line JSON payload per event, so line-splitting is sufficient —
/// no multi-line SSE "data:" continuations to handle.
class CaseGenerationApiClient {
  CaseGenerationApiClient({http.Client? httpClient, String? baseUrl})
    : _httpClient = httpClient ?? http.Client(),
      _baseUrl = baseUrl ?? ApiConfig.baseUrl;

  final http.Client _httpClient;
  final String _baseUrl;

  Stream<GenerationEventDto> generateCase() async* {
    final request = http.Request('POST', Uri.parse('$_baseUrl/cases/generate'));
    // Times out getting the response headers/status at all (a dead
    // connection before the stream even opens) — separate from the
    // per-chunk timeout below, which covers the stream once it's
    // actually flowing.
    final streamedResponse = await _httpClient
        .send(request)
        .timeout(const Duration(seconds: 15));

    if (streamedResponse.statusCode < 200 ||
        streamedResponse.statusCode >= 300) {
      final body = await streamedResponse.stream.bytesToString();
      throw ApiException.fromResponseBody(streamedResponse.statusCode, body);
    }

    final lines = streamedResponse.stream
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        // A per-chunk idle timeout, not a total-request one — a full
        // generation can legitimately run for the whole multi-attempt
        // retry loop (tens of seconds), but the backend now emits a
        // ": keep-alive" comment line at least every 15s even mid-attempt
        // (see cases.py's event_stream), so a real gap this long past
        // that means the connection actually died, not that generation
        // is still working. Comment lines don't start with "data: " and
        // are already skipped by the loop below, unmodified for this.
        .timeout(const Duration(seconds: 45));

    await for (final line in lines) {
      if (!line.startsWith('data: ')) continue;
      final json =
          jsonDecode(line.substring('data: '.length)) as Map<String, dynamic>;
      yield GenerationEventDto.fromJson(json);
    }
  }
}
