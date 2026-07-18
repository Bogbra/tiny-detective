import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config/api_config.dart';
import '../../../core/errors/api_exception.dart';
import '../../hints/data/hint_dto.dart';
import '../../results/data/case_result_dto.dart';
import 'dtos/case_dto.dart';
import 'dtos/player_dto.dart';

class CaseApiClient {
  CaseApiClient({http.Client? httpClient, String? baseUrl})
    : _httpClient = httpClient ?? http.Client(),
      _baseUrl = baseUrl ?? ApiConfig.baseUrl;

  final http.Client _httpClient;
  final String _baseUrl;

  static const _jsonHeaders = {'Content-Type': 'application/json'};

  // Every call here used to have no timeout at all — an unresponsive
  // backend or a dead connection would hang the request indefinitely,
  // leaving the UI stuck on a loading spinner forever instead of
  // reaching the existing error state. 15s is generous for a plain JSON
  // request against this backend's real observed latency (well under a
  // second normally); a genuine timeout surfaces as a plain
  // TimeoutException, which the existing generic `catch (_)` handlers in
  // the view models already turn into "Could not reach the server" — no
  // new exception type or UI branch needed for this.
  static const _requestTimeout = Duration(seconds: 15);

  Future<CaseDto> getDailyCase() async {
    final response = await _httpClient
        .get(Uri.parse('$_baseUrl/cases/daily'))
        .timeout(_requestTimeout);
    _throwIfNotOk(response);
    return CaseDto.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<PlayerDto> createPlayer() async {
    final response = await _httpClient
        .post(Uri.parse('$_baseUrl/players'))
        .timeout(_requestTimeout);
    _throwIfNotOk(response);
    return PlayerDto.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<CaseResultDto> submitSolution({
    required String caseId,
    required String playerId,
    required String suspectId,
  }) async {
    final response = await _httpClient
        .post(
          Uri.parse('$_baseUrl/cases/$caseId/solution'),
          headers: _jsonHeaders,
          body: jsonEncode({'playerId': playerId, 'suspectId': suspectId}),
        )
        .timeout(_requestTimeout);
    _throwIfNotOk(response);
    return CaseResultDto.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<HintDto> requestHint({
    required String caseId,
    required String playerId,
  }) async {
    final response = await _httpClient
        .post(
          Uri.parse('$_baseUrl/cases/$caseId/hint'),
          headers: _jsonHeaders,
          body: jsonEncode({'playerId': playerId}),
        )
        .timeout(_requestTimeout);
    _throwIfNotOk(response);
    return HintDto.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  void _throwIfNotOk(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException.fromResponseBody(response.statusCode, response.body);
    }
  }
}
