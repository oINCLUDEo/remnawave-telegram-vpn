import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../bloc/auth_bloc.dart';
import '../bloc/auth_event.dart';
import '../bloc/auth_state.dart';
import '../widgets/auth_button.dart';
import '../widgets/auth_text_field.dart';

/// Registration screen — creates a new account via email + password.
class RegisterPage extends StatefulWidget {
  const RegisterPage({
    super.key,
    this.onRegisterSuccess,
    this.onGoToLogin,
  });

  /// Called after successful registration.
  /// [requiresVerification] indicates whether the user should check their email.
  final void Function({required bool requiresVerification, required String email})?
      onRegisterSuccess;

  final VoidCallback? onGoToLogin;

  @override
  State<RegisterPage> createState() => _RegisterPageState();
}

class _RegisterPageState extends State<RegisterPage> {
  final _firstNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  bool _obscurePassword = true;
  bool _obscureConfirm = true;
  bool _agreeToTerms = false;

  String? _firstNameError;
  String? _emailError;
  String? _passwordError;
  String? _confirmError;
  String? _termsError;

  @override
  void dispose() {
    _firstNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  bool _validate() {
    final firstName = _firstNameController.text.trim();
    final email = _emailController.text.trim();
    final password = _passwordController.text;
    final confirm = _confirmPasswordController.text;

    String? fnErr;
    String? emailErr;
    String? passErr;
    String? confirmErr;
    String? termsErr;

    if (firstName.isEmpty) fnErr = 'Введите имя';

    if (email.isEmpty) {
      emailErr = 'Введите email';
    } else if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(email)) {
      emailErr = 'Неверный формат email';
    }

    if (password.isEmpty) {
      passErr = 'Введите пароль';
    } else if (password.length < AppConstants.passwordMinLength) {
      passErr = 'Минимум ${AppConstants.passwordMinLength} символов';
    }

    if (confirm != password) {
      confirmErr = 'Пароли не совпадают';
    }

    if (!_agreeToTerms) {
      termsErr = 'Необходимо принять условия';
    }

    setState(() {
      _firstNameError = fnErr;
      _emailError = emailErr;
      _passwordError = passErr;
      _confirmError = confirmErr;
      _termsError = termsErr;
    });

    return fnErr == null &&
        emailErr == null &&
        passErr == null &&
        confirmErr == null &&
        termsErr == null;
  }

  void _submit() {
    if (!_validate()) return;
    context.read<AuthBloc>().add(
          RegisterSubmitted(
            email: _emailController.text.trim(),
            password: _passwordController.text,
            firstName: _firstNameController.text.trim(),
          ),
        );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: widget.onGoToLogin,
        ),
      ),
      body: BlocConsumer<AuthBloc, AuthState>(
        listener: (context, state) {
          if (state is AuthRegisterSuccess) {
            widget.onRegisterSuccess?.call(
              requiresVerification: state.requiresVerification,
              email: state.email,
            );
          } else if (state is AuthError) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(state.message)),
            );
          }
        },
        builder: (context, state) {
          final isLoading = state is AuthLoading;
          return SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 28),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 16),
                  _buildHeader(),
                  const SizedBox(height: 32),
                  _buildForm(isLoading),
                  const SizedBox(height: 24),
                  _buildFooter(),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildHeader() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Создать аккаунт',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 8),
        Text(
          'Зарегистрируйтесь, чтобы начать пользоваться Ulya VPN',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
      ],
    );
  }

  Widget _buildForm(bool isLoading) {
    return AutofillGroup(
      child: Column(
        children: [
          AuthTextField(
            controller: _firstNameController,
            labelText: 'Имя',
            hintText: 'Ваше имя',
            prefixIcon: Icons.person_outline_rounded,
            textInputAction: TextInputAction.next,
            errorText: _firstNameError,
            autofillHints: const [AutofillHints.givenName],
            onChanged: (_) {
              if (_firstNameError != null) {
                setState(() => _firstNameError = null);
              }
            },
            enabled: !isLoading,
          ),
          const SizedBox(height: 16),
          AuthTextField(
            controller: _emailController,
            labelText: 'Email',
            hintText: 'you@example.com',
            prefixIcon: Icons.email_outlined,
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
            errorText: _emailError,
            autofillHints: const [AutofillHints.email],
            onChanged: (_) {
              if (_emailError != null) setState(() => _emailError = null);
            },
            enabled: !isLoading,
          ),
          const SizedBox(height: 16),
          AuthTextField(
            controller: _passwordController,
            labelText: 'Пароль',
            hintText: 'Минимум 8 символов',
            prefixIcon: Icons.lock_outline_rounded,
            obscureText: _obscurePassword,
            textInputAction: TextInputAction.next,
            errorText: _passwordError,
            autofillHints: const [AutofillHints.newPassword],
            suffixIcon: IconButton(
              icon: Icon(
                _obscurePassword
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
              ),
              onPressed: () =>
                  setState(() => _obscurePassword = !_obscurePassword),
            ),
            onChanged: (_) {
              if (_passwordError != null) setState(() => _passwordError = null);
            },
            enabled: !isLoading,
          ),
          const SizedBox(height: 16),
          AuthTextField(
            controller: _confirmPasswordController,
            labelText: 'Повторите пароль',
            prefixIcon: Icons.lock_outline_rounded,
            obscureText: _obscureConfirm,
            textInputAction: TextInputAction.done,
            errorText: _confirmError,
            suffixIcon: IconButton(
              icon: Icon(
                _obscureConfirm
                    ? Icons.visibility_off_outlined
                    : Icons.visibility_outlined,
              ),
              onPressed: () =>
                  setState(() => _obscureConfirm = !_obscureConfirm),
            ),
            onChanged: (_) {
              if (_confirmError != null) setState(() => _confirmError = null);
            },
            onFieldSubmitted: (_) => _submit(),
            enabled: !isLoading,
          ),
          const SizedBox(height: 20),
          _buildTermsCheckbox(isLoading),
          const SizedBox(height: 24),
          AuthButton(
            label: 'Зарегистрироваться',
            onPressed: _submit,
            isLoading: isLoading,
          ),
        ],
      ),
    );
  }

  Widget _buildTermsCheckbox(bool isLoading) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Checkbox(
              value: _agreeToTerms,
              onChanged: isLoading
                  ? null
                  : (v) => setState(() {
                        _agreeToTerms = v ?? false;
                        if (_agreeToTerms) _termsError = null;
                      }),
              activeColor: AppColors.primary,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(4),
              ),
            ),
            Expanded(
              child: Text(
                'Я принимаю условия использования и политику конфиденциальности',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          ],
        ),
        if (_termsError != null)
          Padding(
            padding: const EdgeInsets.only(left: 12, top: 4),
            child: Text(
              _termsError!,
              style: const TextStyle(color: AppColors.error, fontSize: 12),
            ),
          ),
      ],
    );
  }

  Widget _buildFooter() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Text(
          'Уже есть аккаунт? ',
          style: Theme.of(context).textTheme.bodyMedium,
        ),
        TextButton(
          onPressed: widget.onGoToLogin,
          child: const Text('Войти'),
        ),
      ],
    );
  }
}
