import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../api/api_client.dart';

class AuthProvider extends ChangeNotifier {
  final ApiClient _api = ApiClient();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  
  bool _isAuthenticated = false;
  Map<String, dynamic>? _user;
  bool _isLoading = false;
  
  bool get isAuthenticated => _isAuthenticated;
  Map<String, dynamic>? get user => _user;
  bool get isLoading => _isLoading;
  
  AuthProvider() {
    _checkAuth();
  }
  
  Future<void> _checkAuth() async {
    final token = await _storage.read(key: 'access_token');
    if (token != null) {
      try {
        _user = await _api.getMe();
        _isAuthenticated = true;
        notifyListeners();
      } catch (e) {
        await logout();
      }
    }
  }
  
  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    
    try {
      final response = await _api.login(email, password);
      await _storage.write(key: 'access_token', value: response['access_token']);
      await _storage.write(key: 'refresh_token', value: response['refresh_token']);
      _user = response['user'];
      _isAuthenticated = true;
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      rethrow;
    }
  }
  
  Future<bool> register(String email, String password, String firstName) async {
    _isLoading = true;
    notifyListeners();
    
    try {
      final response = await _api.register(email, password, firstName);
      // Auto-login after registration if tokens provided
      if (response.containsKey('access_token')) {
        await _storage.write(key: 'access_token', value: response['access_token']);
        await _storage.write(key: 'refresh_token', value: response['refresh_token']);
        _user = response['user'];
        _isAuthenticated = true;
      }
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _isLoading = false;
      notifyListeners();
      rethrow;
    }
  }
  
  Future<void> logout() async {
    await _storage.deleteAll();
    _isAuthenticated = false;
    _user = null;
    notifyListeners();
  }
}
