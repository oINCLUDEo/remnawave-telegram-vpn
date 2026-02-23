# Flutter App - Быстрый старт

## 5 минут до первого запуска

### 1. Настройка Backend

В `.env` файле активируйте Cabinet API:

```env
CABINET_ENABLED=true
CABINET_JWT_SECRET=your-secret-key-here-min-32-chars
CABINET_ALLOWED_ORIGINS=myapp://,https://yourdomain.com
```

Перезапустите сервер:
```bash
docker-compose restart
```

API теперь доступен на: `https://your-domain.com/cabinet`

### 2. Создайте Flutter проект

```bash
flutter create vpn_app
cd vpn_app
```

### 3. Добавьте зависимости

В `pubspec.yaml`:
```yaml
dependencies:
  flutter:
    sdk: flutter
  dio: ^5.4.0
  flutter_secure_storage: ^9.0.0
  uni_links: ^0.5.1
```

```bash
flutter pub get
```

### 4. Создайте API клиент

Создайте файл `lib/api_client.dart`:

```dart
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  static const String baseUrl = 'https://your-domain.com/cabinet';
  final Dio _dio = Dio(BaseOptions(baseUrl: baseUrl));
  final _storage = const FlutterSecureStorage();

  // Вход
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await _dio.post('/auth/login-email', data: {
      'email': email,
      'password': password,
    });
    
    await _storage.write(key: 'access_token', value: response.data['access_token']);
    await _storage.write(key: 'refresh_token', value: response.data['refresh_token']);
    
    return response.data;
  }

  // Регистрация
  Future<Map<String, dynamic>> register(String email, String password, String firstName) async {
    final response = await _dio.post('/auth/register-email', data: {
      'email': email,
      'password': password,
      'first_name': firstName,
    });
    return response.data;
  }

  // Получить текущего пользователя
  Future<Map<String, dynamic>> getMe() async {
    final token = await _storage.read(key: 'access_token');
    final response = await _dio.get('/auth/me',
      options: Options(headers: {'Authorization': 'Bearer $token'}),
    );
    return response.data;
  }

  // Баланс
  Future<Map<String, dynamic>> getBalance() async {
    final token = await _storage.read(key: 'access_token');
    final response = await _dio.get('/balance',
      options: Options(headers: {'Authorization': 'Bearer $token'}),
    );
    return response.data;
  }

  // Подписка
  Future<Map<String, dynamic>> getSubscription() async {
    final token = await _storage.read(key: 'access_token');
    final response = await _dio.get('/subscription',
      options: Options(headers: {'Authorization': 'Bearer $token'}),
    );
    return response.data;
  }

  // Пополнить баланс
  Future<Map<String, dynamic>> topUp(double amount, String paymentMethod) async {
    final token = await _storage.read(key: 'access_token');
    final response = await _dio.post('/balance/top-up',
      data: {
        'amount_rubles': amount,
        'payment_method': paymentMethod,
        'return_url': 'myapp://payment/callback',
      },
      options: Options(headers: {'Authorization': 'Bearer $token'}),
    );
    return response.data;
  }
}
```

### 5. Простой экран входа

`lib/login_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'api_client.dart';

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _apiClient = ApiClient();
  bool _loading = false;

  Future<void> _login() async {
    setState(() => _loading = true);
    
    try {
      final result = await _apiClient.login(
        _emailController.text,
        _passwordController.text,
      );
      
      // Успешный вход
      Navigator.pushReplacementNamed(context, '/home');
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка входа: $e')),
      );
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Вход')),
      body: Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _emailController,
              decoration: InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
            ),
            SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(labelText: 'Пароль'),
              obscureText: true,
            ),
            SizedBox(height: 24),
            ElevatedButton(
              onPressed: _loading ? null : _login,
              child: _loading
                ? CircularProgressIndicator()
                : Text('Войти'),
            ),
          ],
        ),
      ),
    );
  }
}
```

### 6. Экран баланса и подписки

`lib/home_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'api_client.dart';

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _apiClient = ApiClient();
  Map<String, dynamic>? _user;
  Map<String, dynamic>? _balance;
  Map<String, dynamic>? _subscription;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      final user = await _apiClient.getMe();
      final balance = await _apiClient.getBalance();
      final subscription = await _apiClient.getSubscription();
      
      setState(() {
        _user = user;
        _balance = balance;
        _subscription = subscription;
        _loading = false;
      });
    } catch (e) {
      print('Error loading data: $e');
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text('VPN Service'),
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: ListView(
          padding: EdgeInsets.all(16),
          children: [
            // Информация о пользователе
            Card(
              child: ListTile(
                leading: Icon(Icons.person),
                title: Text(_user?['first_name'] ?? 'Пользователь'),
                subtitle: Text(_user?['email'] ?? ''),
              ),
            ),
            SizedBox(height: 16),
            
            // Баланс
            Card(
              child: ListTile(
                leading: Icon(Icons.account_balance_wallet),
                title: Text('Баланс'),
                subtitle: Text(
                  '${_balance?['balance_rubles']?.toStringAsFixed(2) ?? '0.00'} ₽'
                ),
                trailing: ElevatedButton(
                  onPressed: _showTopUpDialog,
                  child: Text('Пополнить'),
                ),
              ),
            ),
            SizedBox(height: 16),
            
            // Подписка
            Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Подписка', style: Theme.of(context).textTheme.titleLarge),
                    SizedBox(height: 8),
                    if (_subscription != null) ...[
                      Text('Активна до: ${_subscription!['expires_at']}'),
                      Text('Трафик: ${_formatBytes(_subscription!['data_remaining_bytes'])}'),
                      Text('Устройств: ${_subscription!['devices_count']}/${_subscription!['max_devices']}'),
                    ] else
                      Text('Нет активной подписки'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showTopUpDialog() {
    final controller = TextEditingController();
    
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Пополнение баланса'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: controller,
              decoration: InputDecoration(
                labelText: 'Сумма (₽)',
                hintText: '500',
              ),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: Text('Отмена'),
          ),
          ElevatedButton(
            onPressed: () async {
              final amount = double.tryParse(controller.text);
              if (amount != null && amount > 0) {
                Navigator.pop(context);
                await _topUp(amount);
              }
            },
            child: Text('Пополнить'),
          ),
        ],
      ),
    );
  }

  Future<void> _topUp(double amount) async {
    try {
      final result = await _apiClient.topUp(amount, 'YOOKASSA_SBP');
      final url = result['confirmation_url'];
      
      // Здесь нужно открыть URL в браузере
      // import 'package:url_launcher/url_launcher.dart';
      // await launchUrl(Uri.parse(url));
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Перенаправление на оплату...')),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка: $e')),
      );
    }
  }

  String _formatBytes(int? bytes) {
    if (bytes == null) return 'Безлимит';
    final gb = bytes / (1024 * 1024 * 1024);
    return '${gb.toStringAsFixed(1)} GB';
  }
}
```

### 7. Главный файл приложения

`lib/main.dart`:

```dart
import 'package:flutter/material.dart';
import 'login_screen.dart';
import 'home_screen.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'VPN Service',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
      ),
      initialRoute: '/login',
      routes: {
        '/login': (context) => LoginScreen(),
        '/home': (context) => HomeScreen(),
      },
    );
  }
}
```

### 8. Запустите приложение

```bash
flutter run
```

## Следующие шаги

1. **Добавьте обработку токенов** - автоматическое обновление через refresh token
2. **Реализуйте deep links** - для возврата из платежей
3. **Добавьте WebSocket** - для real-time уведомлений
4. **Telegram авторизация** - интеграция Telegram Widget Auth
5. **Покупка подписок** - интерфейс выбора тарифов и серверов

## API Endpoints Reference

### Аутентификация
- `POST /cabinet/auth/login-email` - Вход по email
- `POST /cabinet/auth/register-email` - Регистрация
- `POST /cabinet/auth/refresh` - Обновление токена
- `GET /cabinet/auth/me` - Текущий пользователь

### Баланс
- `GET /cabinet/balance` - Получить баланс
- `GET /cabinet/balance/transactions` - История транзакций
- `POST /cabinet/balance/top-up` - Пополнить баланс
- `GET /cabinet/balance/payment-methods` - Методы оплаты

### Подписки
- `GET /cabinet/subscription` - Текущая подписка
- `GET /cabinet/subscription/status` - Статус подписки
- `GET /cabinet/subscription/tariffs` - Доступные тарифы
- `POST /cabinet/subscription/purchase-tariff` - Купить тариф
- `POST /cabinet/subscription/activate-trial` - Активировать триал

### Реферальная система
- `GET /cabinet/referral/stats` - Статистика рефералов
- `GET /cabinet/referral/referrals` - Список рефералов

### Поддержка
- `GET /cabinet/tickets` - Список тикетов
- `POST /cabinet/tickets` - Создать тикет
- `GET /cabinet/tickets/{id}/messages` - Сообщения в тикете

## Полная документация

Для подробной информации см. [FLUTTER_INTEGRATION.md](./FLUTTER_INTEGRATION.md)

## Тестирование API

Swagger UI: `https://your-domain.com/docs`

Тестовый запрос с curl:
```bash
curl -X POST https://your-domain.com/cabinet/auth/register-email \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!",
    "first_name": "Test"
  }'
```

## Поддержка

- **Документация API**: https://your-domain.com/docs
- **Чат Bedolaga**: https://t.me/+wTdMtSWq8YdmZmVi
- **GitHub Issues**: https://github.com/oINCLUDEo/remnawave-telegram-vpn/issues
