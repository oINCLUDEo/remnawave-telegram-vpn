import 'package:flutter/foundation.dart';
import '../config/api_config.dart';
import '../models/subscription.dart';
import '../services/api_service.dart';

class SubscriptionProvider extends ChangeNotifier {
  Subscription? _subscription;
  bool _isLoading = false;
  String? _error;

  Subscription? get subscription => _subscription;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get hasActiveSubscription => 
      _subscription != null && _subscription!.isActive;

  // Load subscription
  Future<void> loadSubscription() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await ApiService.get(ApiConfig.userSubscription);
      final data = ApiService.parseResponse(response);
      
      if (data.isNotEmpty) {
        _subscription = Subscription.fromJson(data);
      } else {
        _subscription = null;
      }
    } on ApiException catch (e) {
      _error = e.message;
      _subscription = null;
    } catch (e) {
      _error = 'Failed to load subscription: $e';
      _subscription = null;
    }

    _isLoading = false;
    notifyListeners();
  }

  // Refresh subscription
  Future<void> refreshSubscription() async {
    await loadSubscription();
  }

  // Clear error
  void clearError() {
    _error = null;
    notifyListeners();
  }

  // Clear subscription data
  void clear() {
    _subscription = null;
    _error = null;
    _isLoading = false;
    notifyListeners();
  }
}
