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
        final detail = body['detail'];
        
        // FastAPI validation errors: detail is a List
        if (detail is List && detail.isNotEmpty) {
          // Extract first error message
          if (detail[0] is Map<String, dynamic>) {
            final firstError = detail[0] as Map<String, dynamic>;
            final msg = firstError['msg'] ?? 'Validation error';
            final loc = firstError['loc'];
            
            // Include field name if available
            if (loc is List && loc.length > 1) {
              final field = loc.last;
              return '$field: $msg';
            }
            return msg;
          }
          return 'Validation error';
        }
        
        // Standard error: detail is a String
        if (detail is String) {
          return detail;
        }
        
        // Fallback to message field
        return body['message'] ?? 'Unknown error';
      }
      
      return 'Unknown error';
    } catch (e) {
      // Return response body as-is if JSON parsing fails
      return response.body.isNotEmpty ? response.body : 'Unknown error';
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
