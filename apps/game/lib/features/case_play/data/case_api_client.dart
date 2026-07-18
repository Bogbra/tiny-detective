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

  Future<CaseDto> getDailyCase() async {
    final response = await _httpClient.get(Uri.parse('$_baseUrl/cases/daily'));
    _throwIfNotOk(response);
    return CaseDto.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<PlayerDto> createPlayer() async {
    final response = await _httpClient.post(Uri.parse('$_baseUrl/players'));
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
    final response = await _httpClient.post(
      Uri.parse('$_baseUrl/cases/$caseId/solution'),
      headers: _jsonHeaders,
      body: jsonEncode({'playerId': playerId, 'suspectId': suspectId}),
    );
    _throwIfNotOk(response);
    return CaseResultDto.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<HintDto> requestHint({
    required String caseId,
    required String playerId,
  }) async {
    final response = await _httpClient.post(
      Uri.parse('$_baseUrl/cases/$caseId/hint'),
      headers: _jsonHeaders,
      body: jsonEncode({'playerId': playerId}),
    );
    _throwIfNotOk(response);
    return HintDto.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  void _throwIfNotOk(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException.fromResponseBody(response.statusCode, response.body);
    }
  }
}
