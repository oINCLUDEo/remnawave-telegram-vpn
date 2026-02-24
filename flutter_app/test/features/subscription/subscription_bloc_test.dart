import 'package:bloc_test/bloc_test.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

import 'package:ulya_vpn/features/subscription/domain/entities/renewal_option.dart';
import 'package:ulya_vpn/features/subscription/domain/entities/subscription.dart';
import 'package:ulya_vpn/features/subscription/domain/usecases/get_renewal_options_usecase.dart';
import 'package:ulya_vpn/features/subscription/domain/usecases/get_subscription_usecase.dart';
import 'package:ulya_vpn/features/subscription/presentation/bloc/subscription_bloc.dart';
import 'package:ulya_vpn/features/subscription/presentation/bloc/subscription_event.dart';
import 'package:ulya_vpn/features/subscription/presentation/bloc/subscription_state.dart';
import 'package:ulya_vpn/core/errors/failures.dart';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

class MockGetSubscriptionUseCase extends Mock
    implements GetSubscriptionUseCase {}

class MockGetRenewalOptionsUseCase extends Mock
    implements GetRenewalOptionsUseCase {}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

Subscription _makeSubscription() => Subscription(
      id: 1,
      status: 'active',
      isTrial: false,
      startDate: DateTime(2024, 1, 1),
      endDate: DateTime(2024, 12, 31),
      daysLeft: 300,
      hoursLeft: 0,
      timeLeftDisplay: '300д',
      trafficLimitGb: 0,
      trafficUsedGb: 0,
      trafficUsedPercent: 0,
      deviceLimit: 3,
      autopayEnabled: false,
      isActive: true,
      isExpired: false,
      tariffName: 'Базовый',
    );

const _testRenewalOptions = [
  RenewalOption(periodDays: 30, priceKopeks: 29900, priceRubles: 299.0),
  RenewalOption(
    periodDays: 90,
    priceKopeks: 79900,
    priceRubles: 799.0,
    discountPercent: 11,
    originalPriceKopeks: 89700,
  ),
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  late MockGetSubscriptionUseCase mockGetSubscription;
  late MockGetRenewalOptionsUseCase mockGetRenewalOptions;

  setUp(() {
    mockGetSubscription = MockGetSubscriptionUseCase();
    mockGetRenewalOptions = MockGetRenewalOptionsUseCase();
  });

  SubscriptionBloc buildBloc() => SubscriptionBloc(
        getSubscription: mockGetSubscription,
        getRenewalOptions: mockGetRenewalOptions,
      );

  group('SubscriptionBloc', () {
    test('initial state is SubscriptionInitial', () {
      expect(buildBloc().state, const SubscriptionInitial());
    });

    blocTest<SubscriptionBloc, SubscriptionState>(
      'emits [Loading, Loaded] when subscription exists',
      setUp: () {
        when(() => mockGetSubscription())
            .thenAnswer((_) async => _makeSubscription());
        when(() => mockGetRenewalOptions())
            .thenAnswer((_) async => _testRenewalOptions);
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SubscriptionLoadRequested()),
      expect: () => [
        const SubscriptionLoading(),
        SubscriptionLoaded(
          subscription: _makeSubscription(),
          renewalOptions: _testRenewalOptions,
        ),
      ],
    );

    blocTest<SubscriptionBloc, SubscriptionState>(
      'emits [Loading, Loaded] with null subscription when user has none',
      setUp: () {
        when(() => mockGetSubscription()).thenAnswer((_) async => null);
        when(() => mockGetRenewalOptions())
            .thenAnswer((_) async => _testRenewalOptions);
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SubscriptionLoadRequested()),
      expect: () => [
        const SubscriptionLoading(),
        const SubscriptionLoaded(
          subscription: null,
          renewalOptions: _testRenewalOptions,
        ),
      ],
    );

    blocTest<SubscriptionBloc, SubscriptionState>(
      'emits [Loading, Error] on network failure',
      setUp: () {
        when(() => mockGetSubscription())
            .thenThrow(const NetworkFailure());
        when(() => mockGetRenewalOptions())
            .thenAnswer((_) async => []);
      },
      build: buildBloc,
      act: (bloc) => bloc.add(const SubscriptionLoadRequested()),
      expect: () => [
        const SubscriptionLoading(),
        const SubscriptionError('Нет подключения к интернету'),
      ],
    );

    blocTest<SubscriptionBloc, SubscriptionState>(
      'SubscriptionRefreshRequested re-fetches without emitting Loading',
      setUp: () {
        when(() => mockGetSubscription())
            .thenAnswer((_) async => _makeSubscription());
        when(() => mockGetRenewalOptions())
            .thenAnswer((_) async => _testRenewalOptions);
      },
      build: buildBloc,
      seed: () => const SubscriptionLoaded(
        subscription: null,
        renewalOptions: [],
      ),
      act: (bloc) => bloc.add(const SubscriptionRefreshRequested()),
      expect: () => [
        SubscriptionLoaded(
          subscription: _makeSubscription(),
          renewalOptions: _testRenewalOptions,
        ),
      ],
    );
  });

  group('RenewalOption.periodLabel', () {
    test('30 days → "1 месяц"', () {
      const option =
          RenewalOption(periodDays: 30, priceKopeks: 1000, priceRubles: 10.0);
      expect(option.periodLabel, '1 месяц');
    });

    test('90 days → "3 месяца"', () {
      const option =
          RenewalOption(periodDays: 90, priceKopeks: 1000, priceRubles: 10.0);
      expect(option.periodLabel, '3 месяца');
    });

    test('365 days → "1 год"', () {
      const option =
          RenewalOption(periodDays: 365, priceKopeks: 1000, priceRubles: 10.0);
      expect(option.periodLabel, '1 год');
    });

    test('hasDiscount is true when discountPercent > 0', () {
      const option = RenewalOption(
        periodDays: 90,
        priceKopeks: 800,
        priceRubles: 8.0,
        discountPercent: 20,
      );
      expect(option.hasDiscount, isTrue);
    });

    test('hasDiscount is false when discountPercent == 0', () {
      const option =
          RenewalOption(periodDays: 30, priceKopeks: 800, priceRubles: 8.0);
      expect(option.hasDiscount, isFalse);
    });
  });

  group('Subscription', () {
    test('isUnlimited is true when trafficLimitGb is 0', () {
      expect(_makeSubscription().isUnlimited, isTrue);
    });

    test('isUnlimited is false when trafficLimitGb > 0', () {
      final sub = Subscription(
        id: 1,
        status: 'active',
        isTrial: false,
        startDate: DateTime(2024),
        endDate: DateTime(2024),
        daysLeft: 10,
        hoursLeft: 0,
        timeLeftDisplay: '',
        trafficLimitGb: 100,
        trafficUsedGb: 0,
        trafficUsedPercent: 0,
        deviceLimit: 1,
        autopayEnabled: false,
        isActive: true,
        isExpired: false,
      );
      expect(sub.isUnlimited, isFalse);
    });
  });
}

