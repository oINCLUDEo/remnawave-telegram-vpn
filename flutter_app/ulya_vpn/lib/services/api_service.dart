import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import 'storage_service.dart';

class ApiService {
  static Future<http.Response> get(String endpoint, {bool auth = true}) async {
    final url = Uri.parse('${ApiConfig.baseUrl}$endpoint');
    final headers = await _getHeaders(auth);

    try {
      final response = await http
          .get(url, headers: headers)
          .timeout(ApiConfig.receiveTimeout);
      return response;
    } catch (e) {
      rethrow;
    }
  }

  static Future<http.Response> post(
    String endpoint,
    Map<String, dynamic> body, {
    bool auth = true,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}$endpoint');
    final headers = await _getHeaders(auth);

    try {
      final response = await http
          .post(
            url,
            headers: headers,
            body: jsonEncode(body),
          )
          .timeout(ApiConfig.receiveTimeout);
      return response;
    } catch (e) {
      rethrow;
    }
  }

  static Future<http.Response> put(
    String endpoint,
    Map<String, dynamic> body, {
    bool auth = true,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}$endpoint');
    final headers = await _getHeaders(auth);

    try {
      final response = await http
          .put(
            url,
            headers: headers,
            body: jsonEncode(body),
          )
          .timeout(ApiConfig.receiveTimeout);
      return response;
    } catch (e) {
      rethrow;
    }
  }

  static Future<http.Response> delete(
    String endpoint, {
    bool auth = true,
  }) async {
    final url = Uri.parse('${ApiConfig.baseUrl}$endpoint');
    final headers = await _getHeaders(auth);

    try {
      final response = await http
          .delete(url, headers: headers)
          .timeout(ApiConfig.receiveTimeout);
      return response;
    } catch (e) {
      rethrow;
    }
  }

  static Future<Map<String, String>> _getHeaders(bool auth) async {
    if (!auth) {
      return ApiConfig.headers;
    }

    final token = await StorageService.getAccessToken();
    if (token == null) {
      return ApiConfig.headers;
    }

    return ApiConfig.authHeaders(token);
  }

  static Map<String, dynamic> parseResponse(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    } else {
      throw ApiException(
        statusCode: response.statusCode,
        message: _extractErrorMessage(response),
      );
    }
  }

  static String _extractErrorMessage(http.Response response) {
    try {
      final body = jsonDecode(response.body);
      if (body is Map<String, dynamic>) {
        return body['detail'] ?? body['message'] ?? 'Unknown error';
      }
      return 'Unknown error';
    } catch (e) {
      return 'Failed to parse error response';
    }
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String message;

  ApiException({required this.statusCode, required this.message});

  @override
  String toString() => 'ApiException: $statusCode - $message';
}
