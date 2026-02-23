import 'package:flutter/material.dart';
import '../api/api_client.dart';

class BalanceProvider extends ChangeNotifier {
  final ApiClient _api = ApiClient();
  
  double _balance = 0.0;
  List<dynamic> _transactions = [];
  bool _isLoading = false;
  
  double get balance => _balance;
  List<dynamic> get transactions => _transactions;
  bool get isLoading => _isLoading;
  
  Future<void> loadBalance() async {
    _isLoading = true;
    notifyListeners();
    
    try {
      final data = await _api.getBalance();
      _balance = (data['balance_rubles'] ?? 0.0).toDouble();
    } catch (e) {
      _balance = 0.0;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
  
  Future<void> loadTransactions({int page = 1}) async {
    try {
      _transactions = await _api.getTransactions(page: page);
      notifyListeners();
    } catch (e) {
      _transactions = [];
      notifyListeners();
    }
  }
  
  Future<String> topUp(double amount, String paymentMethod) async {
    try {
      final response = await _api.topUp(amount, paymentMethod);
      return response['confirmation_url'] ?? '';
    } catch (e) {
      rethrow;
    }
  }
}
