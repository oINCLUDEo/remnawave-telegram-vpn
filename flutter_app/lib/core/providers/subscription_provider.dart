import 'package:flutter/material.dart';
import '../api/api_client.dart';

class SubscriptionProvider extends ChangeNotifier {
  final ApiClient _api = ApiClient();
  
  Map<String, dynamic>? _subscription;
  List<dynamic> _tariffs = [];
  bool _isLoading = false;
  
  Map<String, dynamic>? get subscription => _subscription;
  List<dynamic> get tariffs => _tariffs;
  bool get isLoading => _isLoading;
  bool get hasActiveSubscription => _subscription != null && (_subscription!['is_active'] ?? false);
  
  Future<void> loadSubscription() async {
    _isLoading = true;
    notifyListeners();
    
    try {
      _subscription = await _api.getSubscription();
    } catch (e) {
      _subscription = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
  
  Future<void> loadTariffs() async {
    try {
      _tariffs = await _api.getTariffs();
      notifyListeners();
    } catch (e) {
      _tariffs = [];
      notifyListeners();
    }
  }
  
  Future<bool> purchaseTariff(int tariffId, String serverUuid) async {
    try {
      await _api.purchaseTariff(tariffId, serverUuid);
      await loadSubscription();
      return true;
    } catch (e) {
      rethrow;
    }
  }
  
  Future<bool> activateTrial(String serverUuid, int devicesCount) async {
    try {
      await _api.activateTrial(serverUuid, devicesCount);
      await loadSubscription();
      return true;
    } catch (e) {
      rethrow;
    }
  }
}
