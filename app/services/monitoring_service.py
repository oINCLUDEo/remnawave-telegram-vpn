import asyncio
import html
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database.crud.discount_offer import (
    deactivate_expired_offers,
    upsert_discount_offer,
)
from app.database.crud.notification import (
    clear_notification_by_type,
    notification_sent,
    record_notification,
)
from app.database.crud.subscription import (
    deactivate_subscription,
    extend_subscription,
    get_expired_subscriptions,
    get_expiring_subscriptions,
    get_subscriptions_for_autopay,
    reactivate_subscription,
    restore_reserve_grace_if_active,
)
from app.database.crud.user import (
    cleanup_expired_promo_offer_discounts,
    delete_user,
    get_inactive_users,
    get_user_by_id,
    subtract_user_balance,
)
from app.database.database import AsyncSessionLocal
from app.database.models import (
    MonitoringLog,
    Subscription,
    SubscriptionStatus,
    Ticket,
    TicketStatus,
    User,
    UserPromoGroup,
    UserStatus,
)
from app.external.remnawave_api import (
    RemnaWaveAPIError,
    RemnaWaveUser,
    UserStatus as RemnaWaveUserStatus,
)
from app.keyboards.icons import ICONS, STYLE_PAY, tg_emoji
from app.localization.texts import get_texts
from app.services.notification_delivery_service import (
    notification_delivery_service,
)
from app.services.notification_settings_service import NotificationSettingsService
from app.services.promo_offer_service import promo_offer_service
from app.services.subscription_service import SubscriptionService, get_traffic_reset_strategy
from app.utils.cache import cache
from app.utils.formatters import format_human_date
from app.utils.pricing_utils import balance_covers_price, shortfall_topup_rubles
from app.utils.message_patch import caption_exceeds_telegram_limit
from app.utils.miniapp_buttons import build_miniapp_or_callback_button, strip_leading_emoji_if_custom_icon
from app.utils.promo_offer import get_user_active_promo_discount_percent
from app.utils.subscription_utils import (
    autopay_days_before,
    resolve_hwid_device_limit_for_payload,
)
from app.utils.timezone import format_local_datetime, is_quiet_hours, quiet_hours_end


# Сообщение о неудачном автопродлении приходит не больше трёх раз за одно продление:
# при первой неудаче, за день до конца подписки и в последний день. Этап хранится
# в SentNotification и стирается, когда подписку продлили (extend_subscription).
_AUTOPAY_FAILED_NOTIFICATION = 'autopay_failed'


def _autopay_failure_stage(end_date: datetime, now: datetime) -> int:
    """1 while more than two days are left, 2 on the day before the end, 3 on the last day."""
    left = end_date - now
    if left > timedelta(days=2):
        return 1
    if left > timedelta(days=1):
        return 2
    return 3


# Размер батча для проверки подписок на каналы (keyset pagination)
_CHANNEL_CHECK_BATCH_SIZE: int = 100

# Последнее напоминание о продлении по подписке: {'chat_id', 'message_id'}.
# Хранится дольше всей цепочки напоминаний (за 3 дня до конца и до третьей волны скидок).
_RENEWAL_REMINDER_KEY = 'renewal_reminder:{user_id}:{subscription_id}'
_RENEWAL_REMINDER_TTL_SECONDS: int = 86400 * 30

# За сколько часов до конца пробного периода предупреждать и предлагать тариф.
_TRIAL_WARNING_HOURS: int = 24


logger = structlog.get_logger(__name__)


LOGO_PATH = Path(settings.LOGO_FILE)


class MonitoringService:
    def __init__(self, bot=None):
        self.is_running = False
        self.subscription_service = SubscriptionService()
        self.bot = bot
        self._notified_users: set[str] = set()
        self._last_cleanup = datetime.now(UTC)
        self._sla_task = None

    async def _send_message_with_logo(
        self,
        chat_id: int | None,
        text: str,
        reply_markup=None,
        parse_mode: str | None = 'HTML',
        user: User | None = None,
        disable_notification: bool = False,
    ):
        """Отправляет сообщение, добавляя логотип при необходимости.

        *disable_notification* делает сообщение тихим: так приходят чеки и
        напоминания, которые не требуют действий.
        """
        if not self.bot:
            raise RuntimeError('Bot instance is not available')

        # Skip email-only users (no telegram_id)
        if not chat_id:
            logger.debug('Пропуск уведомления: chat_id не указан (email-пользователь)')
            return None

        # Skip blocked/deleted users to save Telegram rate limits
        if user and user.status in (UserStatus.BLOCKED.value, UserStatus.DELETED.value):
            logger.debug('Пропуск уведомления: пользователь недоступен', user_id=user.id, status=user.status)
            return None

        if (
            settings.ENABLE_LOGO_MODE
            and await asyncio.to_thread(LOGO_PATH.exists)
            and not caption_exceeds_telegram_limit(text)
        ):
            try:
                from app.utils.message_patch import _cache_logo_file_id, get_logo_media

                result = await self.bot.send_photo(
                    chat_id=chat_id,
                    photo=get_logo_media(),
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification,
                )
                _cache_logo_file_id(result)
                return result
            except TelegramBadRequest as exc:
                logger.warning(
                    'Не удалось отправить сообщение с логотипом пользователю : . Отправляем текстовое сообщение.',
                    chat_id=chat_id,
                    exc=exc,
                )

        return await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_notification=disable_notification,
        )

    async def _replace_renewal_reminder(self, user: User, subscription: Subscription, sent_message) -> None:
        """Remember the reminder just sent and retire the previous one for this subscription.

        Telegram lets a bot delete its message only within 48 hours, so an older
        reminder loses its buttons instead: a stale "renew with discount" must not
        stay clickable next to the new one.
        """
        if not settings.NOTIFICATIONS_REPLACE_PREVIOUS_REMINDER or not sent_message or not self.bot:
            return

        key = _RENEWAL_REMINDER_KEY.format(user_id=user.id, subscription_id=subscription.id)
        previous = await cache.get(key)
        await cache.set(
            key,
            {'chat_id': sent_message.chat.id, 'message_id': sent_message.message_id},
            expire=_RENEWAL_REMINDER_TTL_SECONDS,
        )

        if not isinstance(previous, dict) or previous.get('message_id') == sent_message.message_id:
            return
        chat_id, message_id = previous.get('chat_id'), previous.get('message_id')
        if not chat_id or not message_id:
            return

        try:
            await self.bot.delete_message(chat_id=chat_id, message_id=message_id)
            return
        except TelegramBadRequest:
            pass
        except Exception as error:
            logger.debug('Не удалось удалить прошлое напоминание', user_id=user.id, error=error)
            return

        try:
            await self.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)
        except Exception as error:
            logger.debug('Не удалось снять кнопки с прошлого напоминания', user_id=user.id, error=error)

    @staticmethod
    def _is_unreachable_error(error: TelegramBadRequest) -> bool:
        message = str(error).lower()
        unreachable_markers = (
            'chat not found',
            'user is deactivated',
            'bot was blocked by the user',
            "bot can't initiate conversation",
            "can't initiate conversation",
            'user not found',
            'peer id invalid',
        )
        return any(marker in message for marker in unreachable_markers)

    async def _handle_unreachable_user(self, user: User, error: Exception, context: str) -> bool:
        if isinstance(error, TelegramForbiddenError):
            logger.warning('⚠️ Пользователь недоступен: бот заблокирован', telegram_id=user.telegram_id, context=context)
            return True

        if isinstance(error, TelegramBadRequest) and self._is_unreachable_error(error):
            logger.warning('⚠️ Пользователь недоступен', telegram_id=user.telegram_id, context=context, error=error)
            return True

        return False

    async def start_monitoring(self):
        if self.is_running:
            logger.warning('Мониторинг уже запущен')
            return

        self.is_running = True
        logger.info('🔄 Запуск службы мониторинга')
        # Start dedicated SLA loop with its own interval for timely 5-min checks
        try:
            if not self._sla_task or self._sla_task.done():
                self._sla_task = asyncio.create_task(self._sla_loop())
        except Exception as e:
            logger.error('Не удалось запустить SLA-мониторинг', error=e)

        while self.is_running:
            try:
                await self._monitoring_cycle()
                await asyncio.sleep(settings.MONITORING_INTERVAL * 60)

            except Exception as e:
                logger.error('Ошибка в цикле мониторинга', error=e)
                await asyncio.sleep(60)

    def stop_monitoring(self):
        self.is_running = False
        logger.info('ℹ️ Мониторинг остановлен')
        try:
            if self._sla_task and not self._sla_task.done():
                self._sla_task.cancel()
        except Exception:
            pass

    async def _monitoring_cycle(self):
        async with AsyncSessionLocal() as db:
            try:
                await self._cleanup_notification_cache()

                expired_offers = await deactivate_expired_offers(db)
                if expired_offers:
                    logger.info('🧹 Деактивировано просроченных скидочных предложений', expired_offers=expired_offers)

                expired_active_discounts = await cleanup_expired_promo_offer_discounts(db)
                if expired_active_discounts:
                    logger.info(
                        '🧹 Сброшено активных скидок промо-предложений с истекшим сроком',
                        expired_active_discounts=expired_active_discounts,
                    )

                cleaned_test_access = await promo_offer_service.cleanup_expired_test_access(db)
                if cleaned_test_access:
                    logger.info(
                        '🧹 Отозвано истекших тестовых доступов к сквадам', cleaned_test_access=cleaned_test_access
                    )

                cleaned_reserve_access = await self._cleanup_expired_reserve_access(db)
                if cleaned_reserve_access:
                    logger.info(
                        '🧹 Отозван истекший grace-доступ резервного сквада',
                        cleaned_reserve_access=cleaned_reserve_access,
                    )

                # ВАЖНО: autopay ПЕРЕД check_expired — иначе подписки с автоплатой
                # экспайрятся до того, как autopay успеет их продлить
                # Продление с баланса работает всегда, если у подписки autopay_enabled=True
                await self._process_autopayments(db)
                # Рекуррентные автоплатежи с карты: требуют ENABLE_AUTOPAY + YOOKASSA_RECURRENT_ENABLED
                if settings.ENABLE_AUTOPAY and settings.YOOKASSA_RECURRENT_ENABLED:
                    try:
                        from app.services.recurrent_payment_service import process_recurrent_payments

                        await process_recurrent_payments(db=db, bot=self.bot)
                    except Exception as recurrent_error:
                        logger.error(
                            'Ошибка рекуррентных автоплатежей',
                            error=recurrent_error,
                            exc_info=True,
                        )
                await self._check_expired_subscriptions(db)
                await self._check_expiring_subscriptions(db)
                await self._check_trial_expiring_soon(db)
                await self._check_trial_channel_subscriptions(db)
                await self._check_expired_subscription_followups(db)
                await self._retry_stuck_guest_purchases(db)
                await self._cleanup_inactive_users(db)
                await self._sync_with_remnawave(db)

                await self._log_monitoring_event(
                    db,
                    'monitoring_cycle_completed',
                    'Цикл мониторинга успешно завершен',
                    {'timestamp': datetime.now(UTC).isoformat()},
                )
                await db.commit()

            except Exception as e:
                logger.error('Ошибка в цикле мониторинга', error=e)
                try:
                    await self._log_monitoring_event(
                        db,
                        'monitoring_cycle_error',
                        f'Ошибка в цикле мониторинга: {e!s}',
                        {'error': str(e)},
                        is_success=False,
                    )
                except Exception:
                    pass
                await db.rollback()

    async def _cleanup_expired_reserve_access(self, db: AsyncSession) -> int:
        """По истечении grace-периода отзывает временный резервный сквад у пользователей,
        не продливших подписку (отключает в RemnaWave и восстанавливает исходные сквады локально)."""
        if not settings.RESERVE_SQUAD_UUID:
            return 0

        now = datetime.now(UTC)
        grace_deadline = now - timedelta(days=settings.RESERVE_GRACE_DAYS)

        result = await db.execute(
            select(Subscription)
            .options(selectinload(Subscription.user))
            .where(
                Subscription.reserve_access_granted_at.isnot(None),
                Subscription.reserve_access_granted_at <= grace_deadline,
            )
        )
        subscriptions = result.scalars().all()
        if not subscriptions:
            return 0

        from app.services.subscription_service import SubscriptionService

        subscription_service = SubscriptionService()
        cleaned = 0

        for subscription in subscriptions:
            remnawave_uuid = (
                getattr(subscription, 'remnawave_uuid', None)
                if settings.is_multi_tariff_enabled()
                else getattr(subscription.user, 'remnawave_uuid', None)
            )
            if remnawave_uuid and subscription_service.is_configured:
                await subscription_service.disable_remnawave_user(remnawave_uuid)

            restore_reserve_grace_if_active(subscription)
            cleaned += 1

        await db.commit()
        return cleaned

    async def _cleanup_notification_cache(self):
        current_time = datetime.now(UTC)

        if (current_time - self._last_cleanup).total_seconds() >= 3600:
            old_count = len(self._notified_users)
            self._notified_users.clear()

            self._last_cleanup = current_time
            logger.info('🧹 Очищен кеш уведомлений', old_count=old_count)

    async def _notify_autopay_failed(
        self,
        db: AsyncSession,
        user: User,
        subscription: Subscription,
        required: int,
        *,
        email_reason: str,
    ) -> None:
        """Tell the user autopay could not renew, at most three times per renewal.

        One message per stage (:func:`_autopay_failure_stage`). Each new one
        replaces the previous reminder, and none arrives in quiet hours unless
        the subscription ends before they are over.
        """
        now = datetime.now(UTC)
        stage = _autopay_failure_stage(subscription.end_date, now)
        if await notification_sent(db, user.id, subscription.id, _AUTOPAY_FAILED_NOTIFICATION, stage):
            return
        if is_quiet_hours(now) and subscription.end_date > quiet_hours_end(now):
            return

        if user.telegram_id:
            if not self.bot:
                return
            if not await self._send_autopay_failed_notification(
                user, user.balance_kopeks, required, subscription=subscription
            ):
                return
        else:
            await notification_delivery_service.notify_autopay_failed(user=user, reason=email_reason)

        await record_notification(db, user.id, subscription.id, _AUTOPAY_FAILED_NOTIFICATION, stage)

    async def _check_expired_subscriptions(self, db: AsyncSession):
        try:
            from app.database.crud.subscription import is_recently_updated_by_webhook

            expired_subscriptions = await get_expired_subscriptions(db)

            for subscription in expired_subscriptions:
                if is_recently_updated_by_webhook(subscription):
                    logger.debug(
                        'Пропуск expire подписки : обновлена вебхуком недавно', subscription_id=subscription.id
                    )
                    continue

                from app.database.crud.subscription import expire_subscription

                # Capture tariff name before expire_subscription's db.refresh() expires the relationship
                _tariff_name = subscription.tariff.name if getattr(subscription, 'tariff', None) else None

                await expire_subscription(db, subscription)

                user = await get_user_by_id(db, subscription.user_id)

                reserve_grace_granted = False
                if user and settings.is_reserve_access_enabled_for(user.telegram_id):
                    reserve_grace_granted = await self.subscription_service.grant_reserve_squad_grace(
                        db, user, subscription
                    )

                # Если только что выдали grace-доступ на резервный сквад, пользователь уже
                # получил "🔌 Временный доступ" — не дублируем его сообщением о том, что
                # доступ заблокирован, это противоречит только что показанному уведомлению.
                if user and self.bot and not reserve_grace_granted:
                    if subscription.is_trial and not user.has_had_paid_subscription:
                        await self._send_trial_expired_notification(user, subscription)
                    else:
                        await self._send_subscription_expired_notification(
                            user, subscription, tariff_name=_tariff_name
                        )

                logger.info(
                    "🔴 Подписка пользователя истекла и статус изменен на 'expired'", user_id=subscription.user_id
                )

            if expired_subscriptions:
                await self._log_monitoring_event(
                    db,
                    'expired_subscriptions_processed',
                    f'Обработано {len(expired_subscriptions)} истёкших подписок',
                    {'count': len(expired_subscriptions)},
                )

        except Exception as e:
            logger.error('Ошибка проверки истёкших подписок', error=e)

    async def update_remnawave_user(self, db: AsyncSession, subscription: Subscription) -> RemnaWaveUser | None:
        try:
            from app.database.crud.subscription import is_recently_updated_by_webhook

            # Пока активен grace резервного сквада, панель держит временное состояние,
            # которого нет в локальной строке — рутинный sync задисейблил бы доступ.
            # Если же подписка уже продлена, а флаг остался висеть, снимаем его сами,
            # иначе пользователь навсегда остался бы на резервном скваде и grace-лимите
            # (см. тот же guard в SubscriptionService.update_remnawave_user).
            if getattr(subscription, 'reserve_access_granted_at', None):
                if subscription.end_date is None or subscription.end_date <= datetime.now(UTC):
                    logger.debug(
                        'Пропуск RemnaWave обновления подписки : активен grace резервного сквада',
                        subscription_id=subscription.id,
                    )
                    return None

                logger.warning(
                    'Подписка продлена, но флаг grace остался — снимаем и синхронизируем реальный тариф',
                    subscription_id=subscription.id,
                    end_date=subscription.end_date,
                )
                restore_reserve_grace_if_active(subscription, preserve_end_date=True)
                await db.commit()
                # Рутинный sync ниже намеренно не пересылает сквады, а пользователь
                # сейчас сидит на резервном — уходим в полную синхронизацию, которая
                # вернёт и сквады тарифа, и его лимит трафика.
                return await self.subscription_service.update_remnawave_user(
                    db, subscription, sync_squads=True
                )

            if is_recently_updated_by_webhook(subscription):
                logger.debug(
                    'Пропуск RemnaWave обновления подписки : обновлена вебхуком недавно',
                    subscription_id=subscription.id,
                )
                return None

            user = await get_user_by_id(db, subscription.user_id)
            remnawave_uuid = (
                subscription.remnawave_uuid
                if settings.is_multi_tariff_enabled() and getattr(subscription, 'remnawave_uuid', None)
                else user.remnawave_uuid
                if user
                else None
            )
            if not user or not remnawave_uuid:
                logger.error('RemnaWave UUID не найден для пользователя', user_id=subscription.user_id)
                return None

            # Обновляем subscription в сессии, чтобы избежать detached instance
            # Загружаем tariff для определения внешнего сквада
            try:
                await db.refresh(subscription, ['tariff'])
            except Exception:
                pass

            # Re-check guard after refresh (webhook could have committed between first check and refresh)
            if is_recently_updated_by_webhook(subscription):
                logger.debug(
                    'Пропуск RemnaWave обновления подписки : обновлена вебхуком недавно (после refresh)',
                    subscription_id=subscription.id,
                )
                return None

            current_time = datetime.now(UTC)
            is_active = subscription.status == SubscriptionStatus.ACTIVE.value and subscription.end_date > current_time

            if subscription.status == SubscriptionStatus.ACTIVE.value and subscription.end_date <= current_time:
                # Суточные подписки управляются DailySubscriptionService — не экспайрим
                tariff = getattr(subscription, 'tariff', None)
                is_active_daily = (
                    tariff is not None
                    and getattr(tariff, 'is_daily', False)
                    and not getattr(subscription, 'is_daily_paused', False)
                )
                if is_active_daily:
                    logger.debug(
                        'update_remnawave_user: пропуск expire для суточной подписки',
                        subscription_id=subscription.id,
                    )
                else:
                    subscription.status = SubscriptionStatus.EXPIRED.value
                    await db.commit()
                    is_active = False
                    logger.info("📝 Статус подписки обновлен на 'expired'", subscription_id=subscription.id)

            if not self.subscription_service.is_configured:
                logger.warning(
                    'RemnaWave API не настроен. Пропускаем обновление пользователя', user_id=subscription.user_id
                )
                return None

            async with self.subscription_service.get_api_client() as api:
                hwid_limit = resolve_hwid_device_limit_for_payload(subscription)

                update_kwargs = dict(
                    uuid=remnawave_uuid,
                    status=RemnaWaveUserStatus.ACTIVE if is_active else RemnaWaveUserStatus.DISABLED,
                    # Панель отклоняет expireAt в прошлом — подстраховываемся минимальным
                    # зазором в будущее для обеих веток (см. subscription_service.py).
                    expire_at=max(subscription.end_date, current_time + timedelta(minutes=1)),
                    traffic_limit_bytes=self._gb_to_bytes(subscription.traffic_limit_gb),
                    traffic_limit_strategy=get_traffic_reset_strategy(subscription.tariff),
                    description=settings.format_remnawave_user_description(
                        full_name=user.full_name, username=user.username, telegram_id=user.telegram_id
                    ),
                )

                # Не пересылаем activeInternalSquads в рутинном sync — сквады уже назначены
                # при создании подписки, пересылка стейловых UUID вызывает FK violation → A039

                if hwid_limit is not None:
                    update_kwargs['hwid_device_limit'] = hwid_limit

                # Внешний сквад НЕ пересылаем в рутинном sync — стейловый UUID
                # вызывает FK violation → A039. Назначается при создании подписки.

                updated_user = await api.update_user(**update_kwargs)

                subscription.subscription_url = updated_user.subscription_url
                subscription.subscription_crypto_link = updated_user.happ_crypto_link
                await db.commit()

                status_text = 'активным' if is_active else 'истёкшим'
                logger.info(
                    '✅ Обновлен RemnaWave пользователь со статусом',
                    remnawave_uuid=remnawave_uuid,
                    status_text=status_text,
                )
                return updated_user

        except RemnaWaveAPIError as e:
            logger.error('Ошибка обновления RemnaWave пользователя', error=e)
            return None
        except Exception as e:
            logger.error('Ошибка обновления RemnaWave пользователя', error=e)
            return None

    async def _check_expiring_subscriptions(self, db: AsyncSession):
        try:
            warning_days = settings.get_autopay_warning_days()
            all_processed_users = set()
            # Ночью напоминание откладываем до утра, если подписка доживёт до конца тихих часов
            quiet_until = quiet_hours_end() if is_quiet_hours() else None

            for days in warning_days:
                expiring_subscriptions = await self._get_expiring_paid_subscriptions(db, days)
                sent_count = 0

                # Batch-запрос: собираем user_id с autopay и проверяем наличие карт одним запросом
                users_with_cards: set[int] = set()
                if settings.ENABLE_AUTOPAY and settings.YOOKASSA_RECURRENT_ENABLED:
                    autopay_user_ids = [s.user_id for s in expiring_subscriptions if s.autopay_enabled]
                    if autopay_user_ids:
                        from app.database.crud.saved_payment_method import get_user_ids_with_active_payment_methods

                        users_with_cards = await get_user_ids_with_active_payment_methods(db, autopay_user_ids)

                for subscription in expiring_subscriptions:
                    user = await get_user_by_id(db, subscription.user_id)
                    if not user:
                        continue

                    # Use user.id + subscription.id for key to support multiple subscriptions per user
                    sub_key = f'user_{user.id}_sub_{subscription.id}_today'
                    user_identifier = user.telegram_id or f'email:{user.id}'

                    if (
                        await notification_sent(db, user.id, subscription.id, 'expiring', days)
                        or sub_key in all_processed_users
                    ):
                        logger.debug(
                            'Уведомление уже отправлено, пропускаем',
                            user_identifier=user_identifier,
                            days=days,
                        )
                        continue

                    has_saved_card = subscription.autopay_enabled and user.id in users_with_cards

                    should_send = True
                    for other_days in warning_days:
                        if other_days < days:
                            other_subs = await self._get_expiring_paid_subscriptions(db, other_days)
                            if any(s.id == subscription.id for s in other_subs):
                                should_send = False
                                logger.debug(
                                    '🎯 Пропускаем уведомление на дней для пользователя есть более срочное на дней',
                                    days=days,
                                    user_identifier=user_identifier,
                                    other_days=other_days,
                                )
                                break

                    if not should_send:
                        continue

                    if quiet_until and subscription.end_date and subscription.end_date > quiet_until:
                        continue

                    # Handle email-only users via notification delivery service
                    if not user.telegram_id:
                        success = await notification_delivery_service.notify_subscription_expiring(
                            user=user,
                            days_left=days,
                            expires_at=subscription.end_date,
                        )
                        if success:
                            await record_notification(db, user.id, subscription.id, 'expiring', days)
                            all_processed_users.add(sub_key)
                            sent_count += 1
                            logger.info(
                                '✅ Email-пользователю отправлено уведомление об истечении подписки через дней',
                                user_id=user.id,
                                days=days,
                            )
                        continue

                    if self.bot:
                        success = await self._send_subscription_expiring_notification(
                            db, user, subscription, days, has_saved_card=has_saved_card
                        )
                        if success:
                            await record_notification(db, user.id, subscription.id, 'expiring', days)
                            all_processed_users.add(sub_key)
                            sent_count += 1
                            logger.info(
                                '✅ Пользователю отправлено уведомление об истечении подписки через дней',
                                telegram_id=user.telegram_id,
                                days=days,
                            )
                        else:
                            logger.warning(
                                '❌ Не удалось отправить уведомление пользователю', telegram_id=user.telegram_id
                            )

                if sent_count > 0:
                    await self._log_monitoring_event(
                        db,
                        'expiring_notifications_sent',
                        f'Отправлено {sent_count} уведомлений об истечении через {days} дней',
                        {'days': days, 'count': sent_count},
                    )

        except Exception as e:
            logger.error('Ошибка проверки истекающих подписок', error=e)

    async def _check_trial_expiring_soon(self, db: AsyncSession):
        """A day before the trial ends: when the VPN stops and what to buy, with the price.

        A day leaves time to decide and pay; two hours did not, and arrived at
        night. A trial started less than 12 hours ago is left alone, so a short
        trial does not get «закончится завтра» right after it began.
        """
        # Это продажа, ночью не шлём. Тихие часы короче суток, так что у каждого
        # пробного периода в окне есть дневное время, и утром цикл его отправит.
        if is_quiet_hours():
            return

        try:
            now = datetime.now(UTC)
            threshold_time = now + timedelta(hours=_TRIAL_WARNING_HOURS)

            result = await db.execute(
                select(Subscription)
                .join(Subscription.user)
                .options(
                    selectinload(Subscription.tariff),
                    selectinload(Subscription.user).selectinload(User.promo_group),
                    selectinload(Subscription.user)
                    .selectinload(User.user_promo_groups)
                    .selectinload(UserPromoGroup.promo_group),
                )
                .where(
                    and_(
                        Subscription.status == SubscriptionStatus.ACTIVE.value,
                        Subscription.is_trial == True,
                        Subscription.end_date <= threshold_time,
                        Subscription.end_date > now,
                        Subscription.start_date <= now - timedelta(hours=12),
                        User.status == UserStatus.ACTIVE.value,
                    )
                )
            )
            trial_expiring = result.scalars().all()
            sent_count = 0

            for subscription in trial_expiring:
                user = subscription.user
                if not user or user.has_had_paid_subscription:
                    continue

                # trial_2h — the old two-hour reminder: whoever got it must not get this one too.
                if await notification_sent(db, user.id, subscription.id, 'trial_24h'):
                    continue
                if await notification_sent(db, user.id, subscription.id, 'trial_2h'):
                    continue

                if self.bot:
                    success = await self._send_trial_ending_notification(db, user, subscription)
                    if success:
                        await record_notification(db, user.id, subscription.id, 'trial_24h')
                        sent_count += 1
                        logger.info(
                            '🎁 Пользователю отправлено предупреждение о конце пробного периода',
                            telegram_id=user.telegram_id,
                        )

            if sent_count:
                await self._log_monitoring_event(
                    db,
                    'trial_expiring_notifications_sent',
                    f'Отправлено {sent_count} предупреждений о конце пробного периода',
                    {'count': sent_count},
                )

        except Exception as e:
            logger.error('Ошибка проверки истекающих тестовых подписок', error=e)

    async def _check_trial_channel_subscriptions(self, db: AsyncSession):
        """Background reconciliation of channel subscriptions (rate-limited).

        Processes subscriptions in batches using keyset pagination to avoid
        loading all trial subscriptions into memory at once. Each batch gets
        a fresh DB session to avoid holding a connection pool slot for hours.

        When CHANNEL_REQUIRED_FOR_ALL is True, checks ALL active subscriptions
        (not just trials). Otherwise only checks trial subscriptions.
        """
        from app.database.crud.subscription import is_recently_updated_by_webhook

        if not settings.CHANNEL_IS_REQUIRED_SUB:
            return

        if not self.bot:
            logger.debug('Skipping channel subscription check - bot unavailable')
            return

        from app.database.crud.required_channel import upsert_user_channel_sub
        from app.services.channel_subscription_service import channel_subscription_service
        from app.utils.cache import ChannelSubCache

        channels = await channel_subscription_service.get_required_channels()
        if not channels:
            return

        # When no channel has any disable-on-leave rule, skip deactivation but
        # still run reactivation to restore orphaned DISABLED subscriptions
        # (e.g., admin turned off disable flags after subscriptions were already disabled).
        has_any_disable_rule = any(
            ch.get('disable_trial_on_leave', True) or ch.get('disable_paid_on_leave', False) for ch in channels
        )
        skip_deactivation = not has_any_disable_rule and not settings.CHANNEL_REQUIRED_FOR_ALL

        # Ensure bot is set on service
        if not channel_subscription_service.bot:
            channel_subscription_service.bot = self.bot

        try:
            now = datetime.now(UTC)
            notifications_allowed = (
                NotificationSettingsService.are_notifications_globally_enabled()
                and NotificationSettingsService.is_trial_channel_unsubscribed_enabled()
            )

            disabled_count = 0
            restored_count = 0
            checked_count = 0
            last_id = 0

            # Build the trial/all filter based on CHANNEL_REQUIRED_FOR_ALL setting
            # Also include paid subs if any channel has disable_paid_on_leave=True,
            # so monitoring can reconcile missed real-time events for paid users.
            from sqlalchemy import true as sa_true

            has_paid_disable_rule = any(ch.get('disable_paid_on_leave', False) for ch in channels)
            include_all = settings.CHANNEL_REQUIRED_FOR_ALL or has_paid_disable_rule
            is_trial_filter = sa_true() if include_all else Subscription.is_trial.is_(True)

            while True:
                # Fresh session per batch to avoid long-running connections
                async with AsyncSessionLocal() as batch_db:
                    result = await batch_db.execute(
                        select(Subscription)
                        .join(Subscription.user)
                        .options(
                            selectinload(Subscription.user),
                            selectinload(Subscription.tariff),
                        )
                        .where(
                            and_(
                                Subscription.id > last_id,
                                is_trial_filter,
                                Subscription.end_date > now,
                                Subscription.status.in_(
                                    [
                                        SubscriptionStatus.ACTIVE.value,
                                        SubscriptionStatus.DISABLED.value,
                                    ]
                                ),
                                User.status == UserStatus.ACTIVE.value,
                            )
                        )
                        .order_by(Subscription.id)
                        .limit(_CHANNEL_CHECK_BATCH_SIZE)
                    )

                    subscriptions = result.scalars().all()
                    if not subscriptions:
                        break

                    last_id = subscriptions[-1].id

                    for subscription in subscriptions:
                        user = subscription.user
                        if not user or not user.telegram_id:
                            continue

                        # Skip admins -- consistent with channel_member.py and channel_checker.py
                        if settings.is_admin(user.telegram_id):
                            continue

                        # Existing guard: skip if recently updated by webhook
                        if is_recently_updated_by_webhook(subscription):
                            logger.debug(
                                'Skipping subscription: recently updated by webhook',
                                subscription_id=subscription.id,
                            )
                            continue

                        checked_count += 1

                        # Rate-limited check for ALL channels
                        all_subscribed = True
                        unsubscribed_channels: list[dict] = []
                        for ch in channels:
                            is_member = await channel_subscription_service._rate_limited_check(
                                user.telegram_id, ch['channel_id']
                            )
                            # Update DB + cache
                            await upsert_user_channel_sub(batch_db, user.telegram_id, ch['channel_id'], is_member)
                            await ChannelSubCache.set_sub_status(user.telegram_id, ch['channel_id'], is_member)

                            if not is_member:
                                all_subscribed = False
                                unsubscribed_channels.append(ch)

                        # DEACTIVATE: was active, now not subscribed to all
                        if subscription.status == SubscriptionStatus.ACTIVE.value and not all_subscribed:
                            if skip_deactivation:
                                continue

                            # Respect per-channel disable_trial_on_leave / disable_paid_on_leave settings
                            should_disable = any(
                                channel_subscription_service.should_disable_subscription(ch, subscription.is_trial)
                                for ch in unsubscribed_channels
                            )
                            if not should_disable:
                                continue

                            subscription = await deactivate_subscription(batch_db, subscription, commit=False)
                            disabled_count += 1
                            logger.info(
                                'Subscription deactivated (channel unsubscribe)',
                                telegram_id=user.telegram_id,
                                subscription_id=subscription.id,
                                is_trial=subscription.is_trial,
                            )

                            panel_uuid = (
                                subscription.remnawave_uuid
                                if settings.is_multi_tariff_enabled() and subscription.remnawave_uuid
                                else user.remnawave_uuid
                            )
                            if panel_uuid:
                                try:
                                    await self.subscription_service.disable_remnawave_user(panel_uuid)
                                except Exception as api_error:
                                    logger.error(
                                        'Failed to disable RemnaWave user',
                                        remnawave_uuid=panel_uuid,
                                        api_error=api_error,
                                    )

                            if notifications_allowed:
                                if not await notification_sent(
                                    batch_db,
                                    user.id,
                                    subscription.id,
                                    'trial_channel_unsubscribed',
                                ):
                                    sent = await self._send_trial_channel_unsubscribed_notification(user)
                                    if sent:
                                        await record_notification(
                                            batch_db,
                                            user.id,
                                            subscription.id,
                                            'trial_channel_unsubscribed',
                                            commit=False,
                                        )

                        # REACTIVATE: was disabled, now subscribed to all
                        elif subscription.status == SubscriptionStatus.DISABLED.value and all_subscribed:
                            # Guard: traffic limit exhausted
                            if (
                                subscription.traffic_limit_gb
                                and subscription.traffic_used_gb is not None
                                and subscription.traffic_used_gb >= subscription.traffic_limit_gb
                            ):
                                logger.debug(
                                    'Skipping reactivation: traffic exhausted',
                                    subscription_id=subscription.id,
                                    traffic_used=subscription.traffic_used_gb,
                                    traffic_limit=subscription.traffic_limit_gb,
                                )
                                continue

                            # Guard: disabled by webhook, not by monitoring
                            if (
                                subscription.last_webhook_update_at
                                and subscription.updated_at
                                and subscription.last_webhook_update_at
                                >= subscription.updated_at - timedelta(seconds=10)
                            ):
                                logger.debug(
                                    'Skipping reactivation: disabled by RemnaWave panel',
                                    subscription_id=subscription.id,
                                    last_webhook_at=subscription.last_webhook_update_at,
                                    updated_at=subscription.updated_at,
                                )
                                continue

                            subscription = await reactivate_subscription(batch_db, subscription, commit=False)
                            if subscription.status != SubscriptionStatus.ACTIVE.value:
                                # reactivate_subscription silently skipped (expired or wrong status)
                                continue

                            restored_count += 1
                            logger.info(
                                'Subscription restored (channel resubscribe)',
                                telegram_id=user.telegram_id,
                                subscription_id=subscription.id,
                                is_trial=subscription.is_trial,
                            )

                            try:
                                panel_uuid_restore = (
                                    subscription.remnawave_uuid
                                    if settings.is_multi_tariff_enabled() and subscription.remnawave_uuid
                                    else user.remnawave_uuid
                                )
                                if panel_uuid_restore:
                                    await self.subscription_service.enable_remnawave_user(panel_uuid_restore)
                                else:
                                    # create_remnawave_user calls db.commit() internally --
                                    # flush accumulated batch state first to preserve atomicity.
                                    await batch_db.commit()
                                    await self.subscription_service.create_remnawave_user(batch_db, subscription)
                            except Exception as api_error:
                                logger.error(
                                    'Failed to update RemnaWave user',
                                    telegram_id=user.telegram_id,
                                    api_error=api_error,
                                )

                            await clear_notification_by_type(
                                batch_db,
                                subscription.id,
                                'trial_channel_unsubscribed',
                                commit=False,
                            )

                    # Commit all changes for this batch
                    await batch_db.commit()

            if disabled_count or restored_count:
                check_scope = 'all' if settings.CHANNEL_REQUIRED_FOR_ALL else 'trial'
                await self._log_monitoring_event(
                    db,
                    'trial_channel_subscription_check',
                    (
                        f'Checked {checked_count} {check_scope} subscriptions: '
                        f'disabled {disabled_count}, restored {restored_count}'
                    ),
                    {
                        'checked': checked_count,
                        'disabled': disabled_count,
                        'restored': restored_count,
                        'scope': check_scope,
                    },
                )

        except Exception as error:
            logger.error('Error checking channel subscriptions', error=error)

    async def _check_expired_subscription_followups(self, db: AsyncSession):
        if not NotificationSettingsService.are_notifications_globally_enabled():
            return
        if not self.bot:
            return
        # Напоминания и скидки после окончания подписки — маркетинг, ночью не шлём.
        # Окна у них сутки и больше, утром следующий цикл их отправит.
        if is_quiet_hours():
            return

        try:
            now = datetime.now(UTC)
            # Пробные периоды получают те же скидочные волны, что и платные подписки:
            # это самые тёплые люди. Старые пробные (их тысячи) не грузим: волны
            # всё равно только в первые дни после конца.
            trial_window_days = max(4, NotificationSettingsService.get_third_wave_trigger_days() + 1)

            result = await db.execute(
                select(Subscription)
                .options(
                    selectinload(Subscription.user),
                    selectinload(Subscription.tariff),
                )
                .where(
                    and_(
                        Subscription.end_date <= now,
                        or_(
                            Subscription.is_trial == False,
                            Subscription.end_date >= now - timedelta(days=trial_window_days),
                        ),
                    )
                )
            )

            all_subscriptions = result.scalars().all()

            # Исключаем суточные тарифы - для них отдельная логика
            subscriptions = [
                sub for sub in all_subscriptions if not (sub.tariff and getattr(sub.tariff, 'is_daily', False))
            ]

            sent_day1 = 0
            sent_wave2 = 0
            sent_wave3 = 0

            for subscription in subscriptions:
                user = subscription.user
                if not user:
                    continue

                if subscription.end_date is None:
                    continue

                is_trial = bool(subscription.is_trial)
                if is_trial and user.has_had_paid_subscription:
                    # Пробный период, после которого человек уже что-то купил.
                    continue

                time_since_end = now - subscription.end_date
                if time_since_end.total_seconds() < 0:
                    continue

                days_since = time_since_end.total_seconds() / 86400

                # Day 1 reminder. После пробного его нет: «Пробный период закончился»
                # пришёл в момент окончания, а повтор без скидки ничего не добавляет.
                if not is_trial and NotificationSettingsService.is_expired_1d_enabled() and 1 <= days_since < 2:
                    if not await notification_sent(db, user.id, subscription.id, 'expired_1d'):
                        success = await self._send_expired_day1_notification(user, subscription)
                        if success:
                            await record_notification(db, user.id, subscription.id, 'expired_1d')
                            sent_day1 += 1

                # Second wave (2-3 days) discount
                if NotificationSettingsService.is_second_wave_enabled() and 2 <= days_since < 4:
                    if not await notification_sent(db, user.id, subscription.id, 'expired_discount_wave2'):
                        percent = NotificationSettingsService.get_second_wave_discount_percent()
                        valid_hours = NotificationSettingsService.get_second_wave_valid_hours()
                        offer = await upsert_discount_offer(
                            db,
                            user_id=user.id,
                            subscription_id=subscription.id,
                            notification_type='expired_discount_wave2',
                            discount_percent=percent,
                            bonus_amount_kopeks=0,
                            valid_hours=valid_hours,
                            effect_type='percent_discount',
                        )
                        success = await self._send_expired_discount_notification(
                            user,
                            subscription,
                            percent,
                            offer.expires_at,
                            offer.id,
                            'second',
                            is_trial=is_trial,
                        )
                        if success:
                            await record_notification(db, user.id, subscription.id, 'expired_discount_wave2')
                            sent_wave2 += 1

                # Third wave (N days) discount
                if NotificationSettingsService.is_third_wave_enabled():
                    trigger_days = NotificationSettingsService.get_third_wave_trigger_days()
                    if trigger_days <= days_since < trigger_days + 1:
                        if not await notification_sent(db, user.id, subscription.id, 'expired_discount_wave3'):
                            percent = NotificationSettingsService.get_third_wave_discount_percent()
                            valid_hours = NotificationSettingsService.get_third_wave_valid_hours()
                            offer = await upsert_discount_offer(
                                db,
                                user_id=user.id,
                                subscription_id=subscription.id,
                                notification_type='expired_discount_wave3',
                                discount_percent=percent,
                                bonus_amount_kopeks=0,
                                valid_hours=valid_hours,
                                effect_type='percent_discount',
                            )
                            success = await self._send_expired_discount_notification(
                                user,
                                subscription,
                                percent,
                                offer.expires_at,
                                offer.id,
                                'third',
                                trigger_days=trigger_days,
                                is_trial=is_trial,
                            )
                            if success:
                                await record_notification(db, user.id, subscription.id, 'expired_discount_wave3')
                                sent_wave3 += 1

            if sent_day1 or sent_wave2 or sent_wave3:
                await self._log_monitoring_event(
                    db,
                    'expired_followups_sent',
                    (f'Follow-ups: 1д={sent_day1}, скидка 2-3д={sent_wave2}, скидка N={sent_wave3}'),
                    {
                        'day1': sent_day1,
                        'wave2': sent_wave2,
                        'wave3': sent_wave3,
                    },
                )

        except Exception as e:
            logger.error('Ошибка проверки напоминаний об истекшей подписке', error=e)

    async def _get_expiring_paid_subscriptions(self, db: AsyncSession, days_before: int) -> list[Subscription]:
        current_time = datetime.now(UTC)
        threshold_date = current_time + timedelta(days=days_before)

        result = await db.execute(
            select(Subscription)
            .options(
                selectinload(Subscription.user),
                selectinload(Subscription.tariff),
            )
            .where(
                and_(
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                    Subscription.is_trial == False,
                    Subscription.end_date > current_time,
                    Subscription.end_date <= threshold_date,
                )
            )
        )

        logger.debug('🔍 Поиск платных подписок, истекающих в ближайшие дней', days_before=days_before)
        logger.debug('📅 Текущее время', current_time=current_time)
        logger.debug('📅 Пороговая дата', threshold_date=threshold_date)

        all_subscriptions = result.scalars().all()

        # Исключаем суточные тарифы - для них отдельная логика списания
        subscriptions = [
            sub for sub in all_subscriptions if not (sub.tariff and getattr(sub.tariff, 'is_daily', False))
        ]

        excluded_count = len(all_subscriptions) - len(subscriptions)
        if excluded_count > 0:
            logger.debug('🔄 Исключено суточных подписок из уведомлений', excluded_count=excluded_count)

        logger.info('📊 Найдено платных подписок для уведомлений', subscriptions_count=len(subscriptions))

        return subscriptions

    async def _process_autopayments(self, db: AsyncSession):
        try:
            current_time = datetime.now(UTC)

            # Берём ACTIVE + недавно EXPIRED (middleware или check_and_update могли
            # экспайрить до того, как monitoring успел запустить autopay)
            recently_expired_threshold = current_time - timedelta(hours=2)
            result = await db.execute(
                select(Subscription)
                .options(
                    selectinload(Subscription.user).options(
                        selectinload(User.promo_group),
                        selectinload(User.user_promo_groups).selectinload(UserPromoGroup.promo_group),
                    ),
                    selectinload(Subscription.tariff),
                )
                .where(
                    and_(
                        or_(
                            Subscription.status == SubscriptionStatus.ACTIVE.value,
                            # Подписки, которые были экспайрены middleware/CRUD
                            # недавно (в пределах 2ч) — autopay может их восстановить
                            and_(
                                Subscription.status == SubscriptionStatus.EXPIRED.value,
                                Subscription.end_date >= recently_expired_threshold,
                            ),
                        ),
                        Subscription.autopay_enabled == True,
                        Subscription.is_trial == False,
                    )
                )
            )
            all_autopay_subscriptions = result.scalars().all()

            autopay_subscriptions = []
            for sub in all_autopay_subscriptions:
                # Суточные подписки имеют свой собственный механизм продления
                # (DailySubscriptionService), глобальный autopay на них не распространяется
                if sub.tariff and getattr(sub.tariff, 'is_daily', False):
                    logger.debug(
                        'Пропускаем суточную подписку (тариф) в глобальном autopay', sub_id=sub.id, name=sub.tariff.name
                    )
                    continue

                # Skip classic subscriptions (tariff_id=NULL) when tariff mode is active
                if settings.is_tariffs_mode() and not sub.tariff_id:
                    logger.debug(
                        'Пропускаем классическую подписку без тарифа в autopay (tariff mode)',
                        sub_id=sub.id,
                        user_id=sub.user_id,
                    )
                    # Notify user once that autopay won't work without a tariff
                    autopay_legacy_key = f'autopay_legacy_notified:{sub.user_id}'
                    try:
                        if not await cache.exists(autopay_legacy_key):
                            user = sub.user
                            if user and user.telegram_id and self.bot:
                                await self.bot.send_message(
                                    chat_id=user.telegram_id,
                                    text=(
                                        '⚠️ <b>Автопродление приостановлено</b>\n'
                                        'Подписка оформлена до появления тарифов. '
                                        'Чтобы она продлевалась сама, выберите тариф: '
                                        '«Моя подписка» → «Продлить подписку».'
                                    ),
                                    parse_mode='HTML',
                                )
                            await cache.set(autopay_legacy_key, 1, expire=86400 * 7)
                    except Exception as notify_err:
                        logger.debug('Не удалось уведомить о пропуске autopay для legacy подписки', error=notify_err)
                    continue

                # Not earlier than the subscription's days, so the date on the autopay screen holds.
                if sub.end_date - current_time <= timedelta(days=autopay_days_before(sub)):
                    autopay_subscriptions.append(sub)

            processed_count = 0
            failed_count = 0

            for subscription in autopay_subscriptions:
                from app.database.crud.subscription import is_recently_updated_by_webhook

                if is_recently_updated_by_webhook(subscription):
                    logger.debug(
                        'Пропуск автоплатежа подписки : обновлена вебхуком недавно', subscription_id=subscription.id
                    )
                    continue

                user = subscription.user
                if not user:
                    continue

                user_identifier = user.telegram_id or f'email:{user.id}'

                # Определяем период продления: из тарифа (минимальный) или 30 дней по умолчанию
                tariff = getattr(subscription, 'tariff', None)
                if tariff:
                    autopay_period = tariff.get_shortest_period() or 30
                else:
                    autopay_period = 30

                try:
                    from app.database.crud.user import lock_user_for_pricing
                    from app.services.pricing_engine import pricing_engine

                    user = await lock_user_for_pricing(db, user.id)

                    pricing = await pricing_engine.calculate_renewal_price(
                        db,
                        subscription,
                        autopay_period,
                        user=user,
                    )
                    renewal_cost = pricing.final_total
                except Exception as e:
                    logger.error(
                        'Ошибка расчёта стоимости автопродления, пропускаем',
                        subscription_id=subscription.id,
                        user_id=user.id,
                        error=str(e),
                    )
                    failed_count += 1
                    continue

                if renewal_cost <= 0:
                    logger.warning(
                        'Нулевая стоимость автопродления, пропускаем',
                        subscription_id=subscription.id,
                        user_id=user.id,
                        renewal_cost=renewal_cost,
                    )
                    failed_count += 1
                    continue

                # calculate_renewal_price уже включает promo_group + promo_offer скидки.
                # Не применяем promo_offer повторно — только consume-им при успешной оплате.
                charge_amount = renewal_cost
                promo_discount_percent = get_user_active_promo_discount_percent(user)

                autopay_key = f'autopay_{user.id}_{subscription.id}'
                if autopay_key in self._notified_users:
                    continue

                if balance_covers_price(user.balance_kopeks, charge_amount):
                    success = await subtract_user_balance(
                        db,
                        user,
                        charge_amount,
                        'Автопродление подписки',
                        consume_promo_offer=promo_discount_percent > 0,
                        mark_as_paid_subscription=True,
                    )

                    if success:
                        # extend_subscription сам обработает EXPIRED→ACTIVE переход
                        # (проверяет status + end_date для определения was_expired)
                        if subscription.status == SubscriptionStatus.EXPIRED.value:
                            logger.info(
                                '🔄 Autopay: продление EXPIRED подписки (восстановление)',
                                subscription_id=subscription.id,
                                user_id=user.id,
                            )
                        old_end_date = subscription.end_date
                        # Подписка могла стоять на резервном скваде grace-периода —
                        # снимаем его, иначе панель так и оставит временный сквад
                        # и урезанный трафик поверх оплаченного продления.
                        restore_reserve_squads = restore_reserve_grace_if_active(subscription)
                        await extend_subscription(db, subscription, autopay_period)
                        await self.subscription_service.update_remnawave_user(
                            db,
                            subscription,
                            reset_traffic=settings.RESET_TRAFFIC_ON_PAYMENT,
                            reset_reason='автопродление подписки',
                            sync_squads=restore_reserve_squads,
                        )

                        # Создаём транзакцию, чтобы автопродление было видно в статистике и карточке пользователя
                        try:
                            from app.database.crud.transaction import create_transaction
                            from app.database.models import PaymentMethod, TransactionType

                            transaction = await create_transaction(
                                db=db,
                                user_id=user.id,
                                type=TransactionType.SUBSCRIPTION_PAYMENT,
                                amount_kopeks=charge_amount,
                                description=f'Автопродление подписки на {autopay_period} дней',
                                payment_method=PaymentMethod.BALANCE,
                            )
                        except Exception as exc:
                            logger.warning('Не удалось создать транзакцию автопродления', user_id=user.id, exc=exc)
                            transaction = None

                        # Отправляем уведомление администраторам
                        try:
                            from app.services.subscription_renewal_service import with_admin_notification_service

                            if transaction:
                                await with_admin_notification_service(
                                    lambda svc: svc.send_subscription_extension_notification(
                                        db,
                                        user,
                                        subscription,
                                        transaction,
                                        autopay_period,
                                        old_end_date,
                                        new_end_date=subscription.end_date,
                                        balance_after=user.balance_kopeks,
                                    )
                                )
                        except Exception as exc:
                            logger.warning(
                                'Не удалось отправить админ-уведомление об автопродлении', user_id=user.id, exc=exc
                            )

                        # Send notification via appropriate channel
                        if user.telegram_id and self.bot:
                            await self._send_autopay_success_notification(
                                user, charge_amount, autopay_period, subscription=subscription
                            )
                        elif not user.telegram_id:
                            # Email-only user - use notification delivery service
                            await notification_delivery_service.notify_autopay_success(
                                user=user,
                                amount_kopeks=charge_amount,
                                new_expires_at=subscription.end_date,
                            )

                        processed_count += 1
                        self._notified_users.add(autopay_key)
                        logger.info(
                            '💳 Автопродление подписки пользователя успешно (списано , скидка %)',
                            user_identifier=user_identifier,
                            charge_amount=charge_amount,
                            promo_discount_percent=promo_discount_percent,
                        )
                    else:
                        failed_count += 1
                        await self._notify_autopay_failed(
                            db, user, subscription, charge_amount, email_reason='Ошибка списания средств'
                        )
                        logger.warning(
                            '💳 Ошибка списания средств для автопродления пользователя', user_identifier=user_identifier
                        )
                else:
                    failed_count += 1
                    await self._notify_autopay_failed(
                        db, user, subscription, charge_amount, email_reason='Недостаточно средств на балансе'
                    )

                    logger.warning(
                        '💳 Недостаточно средств для автопродления у пользователя', user_identifier=user_identifier
                    )

            if processed_count > 0 or failed_count > 0:
                await self._log_monitoring_event(
                    db,
                    'autopayments_processed',
                    f'Автоплатежи: успешно {processed_count}, неудачно {failed_count}',
                    {'processed': processed_count, 'failed': failed_count},
                )

        except Exception as e:
            logger.error('Ошибка обработки автоплатежей', error=e)

    async def _send_subscription_expired_notification(
        self, user: User, subscription: Subscription, *, tariff_name: str | None = None
    ) -> bool:
        try:
            tariff_label = ''
            if settings.is_multi_tariff_enabled():
                if tariff_name:
                    tariff_label = f' «{tariff_name}»'
                elif hasattr(subscription, 'tariff') and subscription.tariff:
                    tariff_label = f' «{subscription.tariff.name}»'
            message = f"""
⛔ <b>Подписка{tariff_label} истекла</b>

Ваша подписка истекла. Для восстановления доступа продлите подписку.

🔧 Доступ к серверам заблокирован до продления.
"""

            from aiogram.types import InlineKeyboardMarkup

            extend_callback = f'se:{subscription.id}' if settings.is_multi_tariff_enabled() else 'subscription_extend'
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        build_miniapp_or_callback_button(
                            text='Продлить подписку',
                            callback_data=extend_callback,
                            style='success',
                            icon_custom_emoji_id=ICONS['renew'].custom_emoji_id,
                        )
                    ],
                    [build_miniapp_or_callback_button(text='💳 Пополнить баланс', callback_data='balance_topup')],
                ]
            )

            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'уведомление об истечении подписки'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке уведомления об истечении подписки пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
            return False
        except Exception as e:
            logger.error(
                'Ошибка отправки уведомления об истечении подписки пользователю', telegram_id=user.telegram_id, e=e
            )
            return False

    async def _send_subscription_expiring_notification(
        self,
        db: AsyncSession,
        user: User,
        subscription: Subscription,
        days: int,
        *,
        has_saved_card: bool = False,
    ) -> bool:
        """Remind that a paid subscription ends, saying what will actually happen.

        - Autopay on and the money is there: a silent note with the renewal date.
        - Autopay on and not enough money: once autopay has tried, its failure
          message says this, so nothing more is sent; before that, «Не хватает
          N ₽» with a button that tops up exactly that.
        - Autopay off: «Подписка закончится …» with a renew button.

        Returns True when the reminder is done with, including the case where
        the autopay message covers it.
        """
        try:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            from app.keyboards.icons import icon_button
            from app.utils.formatters import format_deadline
            from app.utils.subscription_utils import autopay_renewal_date, get_renewal_price

            texts = get_texts(user.language)
            now = datetime.now(UTC)
            tariff_label = self._tariff_suffix(subscription)
            price = await get_renewal_price(db, subscription, user) if subscription.autopay_enabled else None
            balance = user.balance_kopeks or 0
            silent = False
            keyboard = None

            if subscription.autopay_enabled and price is not None:
                renew_at = max(autopay_renewal_date(subscription) or now, now)
                renew_date = format_human_date(renew_at, user.language)
                if balance_covers_price(balance, price) or has_saved_card:
                    if balance_covers_price(balance, price):
                        message = texts.t(
                            'SUBSCRIPTION_RENEWS_SOON',
                            '{icon} <b>Подписка{tariff_label} продлится {renew_date}</b>\n'
                            'С баланса спишется {amount}, денег хватает.',
                        )
                    else:
                        message = texts.t(
                            'SUBSCRIPTION_RENEWS_SOON_CARD',
                            '{icon} <b>Подписка{tariff_label} продлится {renew_date}</b>\n'
                            'На балансе не хватает {missing}, их спишут с карты.',
                        )
                    message = message.format(
                        icon=tg_emoji('renew'),
                        tariff_label=tariff_label,
                        renew_date=renew_date,
                        amount=settings.format_price(price),
                        missing=settings.format_price(max(0, price - balance)),
                    )
                    silent = True
                else:
                    if subscription.end_date - now <= timedelta(days=autopay_days_before(subscription)):
                        # Autopay has already tried and said «не хватает» itself.
                        return True
                    missing = price - balance
                    message = texts.t(
                        'SUBSCRIPTION_RENEWAL_SHORTFALL',
                        '{icon} <b>Не хватает {missing} на продление подписки{tariff_label}</b>\n'
                        'Чтобы подписка продлилась сама {renew_date}, пополните баланс. Продление стоит {amount}.',
                    ).format(
                        icon=tg_emoji('warning'),
                        tariff_label=tariff_label,
                        missing=settings.format_price(missing),
                        renew_date=renew_date,
                        amount=settings.format_price(price),
                    )
                    keyboard = self._shortfall_topup_keyboard(texts, missing)
            else:
                message = texts.t(
                    'SUBSCRIPTION_ENDS_SOON',
                    '{icon} <b>Подписка{tariff_label} закончится {end_date}</b>\n'
                    'Чтобы VPN работал дальше, продлите подписку.',
                ).format(
                    icon=tg_emoji('warning'),
                    tariff_label=tariff_label,
                    end_date=format_deadline(subscription.end_date, user.language),
                )
                extend_callback = (
                    f'se:{subscription.id}' if settings.is_multi_tariff_enabled() else 'subscription_extend'
                )
                rows = [
                    [
                        icon_button(
                            'renew',
                            texts.t('MAIN_MENU_BTN_RENEW', 'Продлить подписку'),
                            callback_data=extend_callback,
                            style=STYLE_PAY,
                        )
                    ]
                ]
                if settings.ENABLE_AUTOPAY and not subscription.autopay_enabled:
                    rows.append(
                        [
                            InlineKeyboardButton(
                                text=texts.t('AUTOPAY_ENABLE_BUTTON', 'Включить автопродление'),
                                callback_data='autopay_enable',
                            )
                        ]
                    )
                keyboard = InlineKeyboardMarkup(inline_keyboard=rows)

            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
                disable_notification=silent,
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'уведомление об истекающей подписке'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке уведомления об истечении подписки пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
            return False
        except TelegramNetworkError as e:
            logger.warning(
                'Таймаут отправки уведомления об истечении подписки пользователю', telegram_id=user.telegram_id, e=e
            )
            return False
        except Exception as e:
            logger.error(
                'Ошибка отправки уведомления об истечении подписки пользователю', telegram_id=user.telegram_id, e=e
            )
            return False

    @staticmethod
    def _trial_keeps_setup_note(texts) -> str:
        """« Переподключаться не придётся.»: a purchase turns the trial into the paid subscription, same link.

        With several subscriptions a purchase opens a new one with its own
        link, so the promise is left out there.
        """
        if settings.is_multi_tariff_enabled():
            return ''
        return ' ' + texts.t('TRIAL_KEEPS_SETUP_NOTE', 'Переподключаться не придётся.')

    async def _trial_offer(self, db: AsyncSession, user: User, texts):
        """The tariff to offer when the trial ends: the one most people buy, with the user's price.

        Returns (offer line, keyboard rows). Without a recommended tariff the
        line is empty and the only button is «Выбрать тариф».
        """
        from aiogram.types import InlineKeyboardButton

        from app.database.crud.tariff import get_tariffs_for_user
        from app.handlers.subscription.tariff_purchase import (
            _period_label,
            _tariff_bypass,
            _tariff_devices,
            _tariff_icon_and_name,
            get_recommended_tariff_id,
            tariff_list_price,
        )
        from app.keyboards.icons import icon_button

        choose_button = [
            icon_button(
                'buy',
                texts.t('MAIN_MENU_BTN_CHOOSE_TARIFF', 'Выбрать тариф'),
                callback_data='menu_buy',
                style=STYLE_PAY,
            )
        ]
        if not settings.is_tariffs_mode():
            return '', [choose_button]

        try:
            tariffs = [
                tariff
                for tariff in await get_tariffs_for_user(db, getattr(user, 'promo_group_id', None))
                if not getattr(tariff, 'is_daily', False)
            ]
            recommended_id = await get_recommended_tariff_id(db, tariffs)
            tariff = next((tariff for tariff in tariffs if tariff.id == recommended_id), None)
            list_price = tariff_list_price(tariff, user) if tariff else None
        except Exception as error:
            logger.warning('Не удалось подобрать тариф для конца пробного периода', user_id=user.id, error=error)
            return '', [choose_button]
        if not tariff or not list_price:
            return '', [choose_button]

        language = user.language
        price, period, _discount = list_price
        price_text = settings.format_price(price)
        if period == 30:
            price_line = texts.t('TRIAL_OFFER_PRICE_MONTH', '{price} в месяц').format(price=price_text)
        else:
            price_line = texts.t('TARIFF_PRICE_FOR', '{price} за {period}').format(
                price=price_text, period=_period_label(texts, language, period)
            )
        _icon, name = _tariff_icon_and_name(tariff)
        offer = texts.t(
            'TRIAL_OFFER_LINE',
            'Чаще всего берут «{name}»: {devices}, {traffic}, {price}.',
        ).format(
            name=html.escape(name),
            devices=_tariff_devices(texts, language, tariff.device_limit),
            traffic=_tariff_bypass(texts, tariff),
            price=price_line,
        )
        rows = [
            [
                icon_button(
                    'buy',
                    texts.t('TRIAL_OFFER_BUY_BUTTON', 'Оформить за {price}').format(price=price_text),
                    callback_data=f'tariff_select:{tariff.id}',
                    style=STYLE_PAY,
                )
            ]
        ]
        if len(tariffs) > 1:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=texts.t('TRIAL_OFFER_ALL_TARIFFS', 'Все тарифы'),
                        callback_data='menu_buy',
                    )
                ]
            )
        return offer, rows

    async def _send_trial_ending_notification(self, db: AsyncSession, user: User, subscription: Subscription) -> bool:
        """«Пробный период закончится завтра в 18:40», what happens then, and the tariff to buy with its price."""
        try:
            from aiogram.types import InlineKeyboardMarkup

            from app.utils.formatters import format_deadline

            texts = get_texts(user.language)
            offer, rows = await self._trial_offer(db, user, texts)

            message = texts.t(
                'TRIAL_ENDS_SOON',
                '{icon} <b>Пробный период закончится {end_date}</b>\n'
                'Дальше VPN выключится. Если он вам пригодился, оформите подписку сейчас, '
                'и он продолжит работать без перерыва.{keeps_setup}',
            ).format(
                icon=tg_emoji('warning'),
                end_date=format_deadline(subscription.end_date, user.language),
                keeps_setup=self._trial_keeps_setup_note(texts),
            )
            if offer:
                message += '\n\n' + offer

            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
                user=user,
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'уведомление о завершении тестовой подписки'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке уведомления о завершении тестовой подписки пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
            return False
        except TelegramNetworkError as e:
            logger.warning(
                'Таймаут отправки уведомления об окончании тестовой подписки пользователю',
                telegram_id=user.telegram_id,
                e=e,
            )
            return False
        except Exception as e:
            logger.error(
                'Ошибка отправки уведомления об окончании тестовой подписки пользователю',
                telegram_id=user.telegram_id,
                e=e,
            )
            return False

    async def _send_trial_expired_notification(self, user: User, subscription: Subscription) -> bool:
        """«Пробный период закончился» and «Выбрать тариф»: nothing was bought, so no «Продлить».

        Quiet at night: the VPN is already off, and the message can wait for
        the morning without waking anyone.
        """
        try:
            from aiogram.types import InlineKeyboardMarkup

            from app.keyboards.icons import icon_button

            texts = get_texts(user.language)
            message = texts.t(
                'TRIAL_EXPIRED',
                '{icon} <b>Пробный период закончился</b>\n'
                'VPN выключен. Выберите тариф, и он заработает сразу после оплаты.{keeps_setup}',
            ).format(icon=tg_emoji('expired'), keeps_setup=self._trial_keeps_setup_note(texts))
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        icon_button(
                            'buy',
                            texts.t('MAIN_MENU_BTN_CHOOSE_TARIFF', 'Выбрать тариф'),
                            callback_data='menu_buy',
                            style=STYLE_PAY,
                        )
                    ]
                ]
            )
            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
                user=user,
                disable_notification=is_quiet_hours(),
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'уведомление о конце пробного периода'):
                return True
            logger.error('Ошибка Telegram API при отправке уведомления о конце пробного периода', exc=exc)
            return False
        except Exception as e:
            logger.error('Ошибка отправки уведомления о конце пробного периода', telegram_id=user.telegram_id, e=e)
            return False

    async def _send_trial_channel_unsubscribed_notification(self, user: User) -> bool:
        try:
            texts = get_texts(user.language)
            template = texts.get(
                'TRIAL_CHANNEL_UNSUBSCRIBED',
                (
                    '🚫 <b>Доступ приостановлен</b>\n\n'
                    'Мы не нашли вашу подписку на наш канал, поэтому тестовая подписка отключена.\n\n'
                    'Подпишитесь на канал и нажмите «{check_button}», чтобы вернуть доступ.'
                ),
            )

            check_button = texts.t('CHANNEL_CHECK_BUTTON', '✅ Я подписался')
            message = template.format(check_button=check_button)

            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            from app.services.channel_subscription_service import channel_subscription_service

            unsubscribed = await channel_subscription_service.get_unsubscribed_channels(user.telegram_id)

            buttons = []
            for ch in unsubscribed:
                link = ch.get('channel_link')
                if link:
                    title = ch.get('title') or texts.t('CHANNEL_SUBSCRIBE_BUTTON', '🔗 Подписаться')
                    buttons.append([InlineKeyboardButton(text=f'🔗 {title}', url=link)])
            buttons.append(
                [
                    InlineKeyboardButton(
                        text=check_button,
                        callback_data='sub_channel_check',
                    )
                ]
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
                user=user,
            )
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'уведомление об отписке от канала'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке уведомления об отписке от канала пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
            return False
        except TelegramNetworkError as error:
            logger.warning(
                'Таймаут отправки уведомления об отписке от канала пользователю',
                telegram_id=user.telegram_id,
                error=error,
            )
            return False
        except Exception as error:
            logger.error(
                'Ошибка отправки уведомления об отписке от канала пользователю',
                telegram_id=user.telegram_id,
                error=error,
            )
            return False

    async def _send_expired_day1_notification(self, user: User, subscription: Subscription) -> bool:
        try:
            texts = get_texts(user.language)
            tariff_label = ''
            if settings.is_multi_tariff_enabled() and hasattr(subscription, 'tariff') and subscription.tariff:
                tariff_label = f' «{subscription.tariff.name}»'
            template = texts.get(
                'SUBSCRIPTION_EXPIRED_1D',
                (
                    '⛔ <b>Подписка{tariff_label} закончилась</b>\n\n'
                    'Доступ был отключён {end_date}. Продлите подписку, чтобы вернуться в сервис.'
                ),
            )
            message = template.format(
                end_date=format_local_datetime(subscription.end_date, '%d.%m.%Y %H:%M'),
                price=settings.format_price(settings.PRICE_30_DAYS),
                tariff_label=tariff_label,
            )

            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            extend_callback = f'se:{subscription.id}' if settings.is_multi_tariff_enabled() else 'subscription_extend'

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        build_miniapp_or_callback_button(
                            text=strip_leading_emoji_if_custom_icon(
                                texts.t('SUBSCRIPTION_EXTEND', '💎 Продлить подписку'), ICONS['renew'].custom_emoji_id
                            ),
                            callback_data=extend_callback,
                            style='success',
                            icon_custom_emoji_id=ICONS['renew'].custom_emoji_id,
                        )
                    ],
                    [
                        build_miniapp_or_callback_button(
                            text=texts.t('BALANCE_TOPUP', '💳 Пополнить баланс'),
                            callback_data='balance_topup',
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=texts.t('SUPPORT_BUTTON', '🆘 Поддержка'), callback_data='menu_support'
                        )
                    ],
                ]
            )

            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'напоминание об истекшей подписке'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке напоминания об истекшей подписке пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
            return False
        except TelegramNetworkError as e:
            logger.warning(
                'Таймаут отправки напоминания об истекшей подписке пользователю', telegram_id=user.telegram_id, e=e
            )
            return False
        except Exception as e:
            logger.error(
                'Ошибка отправки напоминания об истекшей подписке пользователю', telegram_id=user.telegram_id, e=e
            )
            return False

    async def _send_expired_discount_notification(
        self,
        user: User,
        subscription: Subscription,
        percent: int,
        expires_at: datetime,
        offer_id: int,
        wave: str,
        trigger_days: int = None,
        *,
        is_trial: bool = False,
    ) -> bool:
        if is_trial:
            return await self._send_trial_discount_notification(
                user, subscription, percent, expires_at, offer_id, wave, trigger_days
            )
        try:
            texts = get_texts(user.language)

            tariff_label = ''
            if settings.is_multi_tariff_enabled() and hasattr(subscription, 'tariff') and subscription.tariff:
                tariff_label = f' «{subscription.tariff.name}»'

            if wave == 'second':
                template = texts.get(
                    'SUBSCRIPTION_EXPIRED_SECOND_WAVE',
                    (
                        '🔥 <b>Скидка {percent}% на продление{tariff_label}</b>\n\n'
                        'Активируйте предложение, чтобы получить дополнительную скидку. '
                        'Она суммируется с вашей промогруппой и действует до {expires_at}.'
                    ),
                )
            else:
                template = texts.get(
                    'SUBSCRIPTION_EXPIRED_THIRD_WAVE',
                    (
                        '🎁 <b>Индивидуальная скидка {percent}%{tariff_label}</b>\n\n'
                        'Прошло {trigger_days} дней без подписки — возвращайтесь и активируйте дополнительную скидку. '
                        'Она суммируется с промогруппой и действует до {expires_at}.'
                    ),
                )

            message = template.format(
                percent=percent,
                expires_at=format_local_datetime(expires_at, '%d.%m.%Y %H:%M'),
                trigger_days=trigger_days or '',
                tariff_label=tariff_label,
            )

            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            extend_callback = f'se:{subscription.id}' if settings.is_multi_tariff_enabled() else 'subscription_extend'

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        build_miniapp_or_callback_button(
                            text='🎁 Получить скидку', callback_data=f'claim_discount_{offer_id}'
                        )
                    ],
                    [
                        build_miniapp_or_callback_button(
                            text=strip_leading_emoji_if_custom_icon(
                                texts.t('SUBSCRIPTION_EXTEND', '💎 Продлить подписку'), ICONS['renew'].custom_emoji_id
                            ),
                            callback_data=extend_callback,
                            style='success',
                            icon_custom_emoji_id=ICONS['renew'].custom_emoji_id,
                        )
                    ],
                    [
                        build_miniapp_or_callback_button(
                            text=texts.t('BALANCE_TOPUP', '💳 Пополнить баланс'),
                            callback_data='balance_topup',
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=texts.t('SUPPORT_BUTTON', '🆘 Поддержка'), callback_data='menu_support'
                        )
                    ],
                ]
            )

            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'скидочное уведомление'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке скидочного уведомления пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
            return False
        except TelegramNetworkError as e:
            logger.warning('Таймаут отправки скидочного уведомления пользователю', telegram_id=user.telegram_id, e=e)
            return False
        except Exception as e:
            logger.error('Ошибка отправки скидочного уведомления пользователю', telegram_id=user.telegram_id, e=e)
            return False

    async def _send_trial_discount_notification(
        self,
        user: User,
        subscription: Subscription,
        percent: int,
        expires_at: datetime,
        offer_id: int,
        wave: str,
        trigger_days: int | None = None,
    ) -> bool:
        """The same discount waves after a trial: «на первую подписку», not «на продление»."""
        try:
            from aiogram.types import InlineKeyboardMarkup

            from app.keyboards.icons import icon_button
            from app.utils.formatters import format_days_declension, format_deadline

            texts = get_texts(user.language)
            if wave == 'second':
                template = texts.t(
                    'TRIAL_EXPIRED_SECOND_WAVE',
                    '{icon} <b>Скидка {percent}% на первую подписку</b>\n'
                    'Пробный период закончился, а скидка только началась. Она действует до {expires_at}: '
                    'нажмите «Получить скидку», и она применится при оплате.',
                )
            else:
                template = texts.t(
                    'TRIAL_EXPIRED_THIRD_WAVE',
                    '{icon} <b>Скидка {percent}% на первую подписку</b>\n'
                    'Прошло {days} без VPN. Если белые списки снова мешают, возвращайтесь: '
                    'скидка действует до {expires_at}, больше таких предложений не будет.',
                )
            message = template.format(
                icon=tg_emoji('trial'),
                percent=percent,
                expires_at=format_deadline(expires_at, user.language),
                days=format_days_declension(trigger_days or 0, user.language),
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        icon_button(
                            'trial',
                            texts.t('TRIAL_DISCOUNT_CLAIM_BUTTON', 'Получить скидку {percent}%').format(
                                percent=percent
                            ),
                            callback_data=f'claim_discount_{offer_id}',
                            style=STYLE_PAY,
                        )
                    ]
                ]
            )
            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=keyboard,
                user=user,
            )
            await self._replace_renewal_reminder(user, subscription, sent)
            return True

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'скидка после пробного периода'):
                return True
            logger.error('Ошибка Telegram API при отправке скидки после пробного периода', exc=exc)
            return False
        except TelegramNetworkError as e:
            logger.warning('Таймаут отправки скидки после пробного периода', telegram_id=user.telegram_id, e=e)
            return False
        except Exception as e:
            logger.error('Ошибка отправки скидки после пробного периода', telegram_id=user.telegram_id, e=e)
            return False

    @staticmethod
    def _tariff_suffix(subscription: Subscription | None) -> str:
        """« «Стандарт»» after the subject when the user can have several subscriptions."""
        if settings.is_multi_tariff_enabled() and subscription and getattr(subscription, 'tariff', None):
            return f' «{html.escape(subscription.tariff.name)}»'
        return ''

    async def _send_autopay_success_notification(
        self, user: User, amount: int, days: int, *, subscription: Subscription | None = None
    ):
        """A silent receipt: nothing to do, so it must not buzz."""
        try:
            texts = get_texts(user.language)
            end_date = format_human_date(subscription.end_date, user.language) if subscription else ''
            message = texts.AUTOPAY_SUCCESS.format(
                icon=tg_emoji('subscription'),
                tariff_label=self._tariff_suffix(subscription),
                end_date=end_date,
                amount=settings.format_price(amount),
                balance=settings.format_price(user.balance_kopeks),
                days=days,
            )
            await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                disable_notification=True,
            )
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if not await self._handle_unreachable_user(user, exc, 'уведомление об успешном автоплатеже'):
                logger.error(
                    'Ошибка Telegram API при отправке уведомления об автоплатеже пользователю',
                    telegram_id=user.telegram_id,
                    exc=exc,
                )
        except TelegramNetworkError as e:
            logger.warning(
                'Таймаут отправки уведомления об автоплатеже пользователю', telegram_id=user.telegram_id, e=e
            )
        except Exception as e:
            logger.error('Ошибка отправки уведомления об автоплатеже пользователю', telegram_id=user.telegram_id, e=e)

    @staticmethod
    def _shortfall_topup_keyboard(texts, missing_kopeks: int):
        """«Пополнить на N ₽» with the shortfall filled in, and «Другая сумма»."""
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        rubles = shortfall_topup_rubles(missing_kopeks)
        balance_icon = ICONS['balance']
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=texts.t('TOPUP_FOR_AMOUNT_BUTTON', 'Пополнить на {amount}').format(
                            amount=texts.format_price(rubles * 100)
                        ),
                        callback_data=f'balance_topup_amount:{rubles}',
                        style=STYLE_PAY,
                        icon_custom_emoji_id=balance_icon.custom_emoji_id,
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=texts.t('TOPUP_OTHER_AMOUNT_BUTTON', '✏️ Другая сумма'),
                        callback_data='balance_topup_other',
                    )
                ],
            ]
        )

    async def _send_autopay_failed_notification(
        self, user: User, balance: int, required: int, *, subscription: Subscription | None = None
    ) -> bool:
        """«Не хватает N ₽» with a button that tops up exactly that. Returns True when sent."""
        try:
            texts = get_texts(user.language)
            missing = max(0, required - balance)
            message = texts.AUTOPAY_FAILED.format(
                icon='⚠️',
                tariff_label=self._tariff_suffix(subscription),
                missing=settings.format_price(missing),
                end_date=format_human_date(subscription.end_date, user.language) if subscription else '',
                balance=settings.format_price(balance),
                required=settings.format_price(required),
            )

            sent = await self._send_message_with_logo(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML',
                reply_markup=self._shortfall_topup_keyboard(texts, missing),
                user=user,
            )
            if sent and subscription:
                await self._replace_renewal_reminder(user, subscription, sent)
            return sent is not None

        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            if await self._handle_unreachable_user(user, exc, 'уведомление о неудачном автоплатеже'):
                return True
            logger.error(
                'Ошибка Telegram API при отправке уведомления о неудачном автоплатеже пользователю',
                telegram_id=user.telegram_id,
                exc=exc,
            )
        except TelegramNetworkError as e:
            logger.warning(
                'Таймаут отправки уведомления о неудачном автоплатеже пользователю', telegram_id=user.telegram_id, e=e
            )
        except Exception as e:
            logger.error(
                'Ошибка отправки уведомления о неудачном автоплатеже пользователю', telegram_id=user.telegram_id, e=e
            )
        return False

    async def _retry_stuck_guest_purchases(self, db: AsyncSession):
        from app.services.guest_purchase_service import (
            recover_stuck_pending_purchases,
            retry_stuck_paid_purchases,
            retry_stuck_pending_activation,
        )

        # Phase 1: Recover PENDING purchases where provider payment already succeeded
        try:
            recovered = await recover_stuck_pending_purchases(db, stale_minutes=10, limit=10)
            if recovered:
                logger.info('Recovered stuck PENDING purchases', recovered=recovered)
        except Exception:
            logger.error('Error recovering stuck PENDING guest purchases', exc_info=True)

        # Phase 2: Retry fulfillment for purchases in PAID status
        try:
            retried = await retry_stuck_paid_purchases(db, stale_minutes=5, limit=10)
            if retried:
                logger.info('Retried stuck guest purchases', retried=retried)
        except Exception:
            logger.error('Error retrying stuck PAID guest purchases', exc_info=True)

        # Phase 3: Retry activation for purchases in PENDING_ACTIVATION status
        try:
            retried_pa = await retry_stuck_pending_activation(db, stale_minutes=10, limit=10)
            if retried_pa:
                logger.info('Retried stuck pending_activation purchases', retried=retried_pa)
        except Exception:
            logger.error('Error retrying stuck PENDING_ACTIVATION guest purchases', exc_info=True)

    async def _cleanup_inactive_users(self, db: AsyncSession):
        try:
            if not settings.INACTIVE_USER_AUTO_CLEANUP_ENABLED:
                return

            now = datetime.now(UTC)
            if now.hour != 3:
                return

            inactive_users = await get_inactive_users(db, settings.INACTIVE_USER_DELETE_MONTHS)
            deleted_count = 0

            for user in inactive_users:
                # Check if user has ANY active subscription (multi-tariff aware)
                has_active = any(sub.is_active for sub in (getattr(user, 'subscriptions', None) or []))
                if not has_active:
                    success = await delete_user(db, user)
                    if success:
                        deleted_count += 1

            if deleted_count > 0:
                await self._log_monitoring_event(
                    db,
                    'inactive_users_cleanup',
                    f'Удалено {deleted_count} неактивных пользователей',
                    {'deleted_count': deleted_count},
                )
                logger.info('🗑️ Удалено неактивных пользователей', deleted_count=deleted_count)

        except Exception as e:
            logger.error('Ошибка очистки неактивных пользователей', error=e)

    async def _sync_with_remnawave(self, db: AsyncSession):
        try:
            now = datetime.now(UTC)
            if now.minute != 0:
                return

            if not self.subscription_service.is_configured:
                logger.warning('RemnaWave API не настроен. Пропускаем синхронизацию')
                return

            async with self.subscription_service.get_api_client() as api:
                system_stats = await api.get_system_stats()

                await self._log_monitoring_event(
                    db, 'remnawave_sync', 'Синхронизация с RemnaWave завершена', {'stats': system_stats}
                )

        except Exception as e:
            logger.error('Ошибка синхронизации с RemnaWave', error=e)
            await self._log_monitoring_event(
                db,
                'remnawave_sync_error',
                f'Ошибка синхронизации с RemnaWave: {e!s}',
                {'error': str(e)},
                is_success=False,
            )

    async def _check_ticket_sla(self, db: AsyncSession):
        try:
            # Quick guards
            # Allow runtime toggle from SupportSettingsService
            try:
                from app.services.support_settings_service import SupportSettingsService

                sla_enabled_runtime = SupportSettingsService.get_sla_enabled()
            except Exception:
                sla_enabled_runtime = getattr(settings, 'SUPPORT_TICKET_SLA_ENABLED', True)
            if not sla_enabled_runtime:
                return
            if not self.bot:
                return
            if not settings.is_admin_notifications_enabled():
                return

            try:
                from app.services.support_settings_service import SupportSettingsService

                sla_minutes = max(1, int(SupportSettingsService.get_sla_minutes()))
            except Exception:
                sla_minutes = max(1, int(getattr(settings, 'SUPPORT_TICKET_SLA_MINUTES', 5)))
            cooldown_minutes = max(1, int(getattr(settings, 'SUPPORT_TICKET_SLA_REMINDER_COOLDOWN_MINUTES', 15)))
            now = datetime.now(UTC)
            stale_before = now - timedelta(minutes=sla_minutes)
            cooldown_before = now - timedelta(minutes=cooldown_minutes)

            # Tickets to remind: open, no admin reply yet after user's last message (status OPEN), stale by SLA,
            # and either never reminded or cooldown passed
            result = await db.execute(
                select(Ticket)
                .options(selectinload(Ticket.user))
                .where(
                    and_(
                        Ticket.status == TicketStatus.OPEN.value,
                        Ticket.updated_at <= stale_before,
                        or_(Ticket.last_sla_reminder_at.is_(None), Ticket.last_sla_reminder_at <= cooldown_before),
                    )
                )
            )
            tickets = result.scalars().all()
            if not tickets:
                return

            from app.services.admin_notification_service import AdminNotificationService

            reminders_sent = 0
            service = AdminNotificationService(self.bot)

            for ticket in tickets:
                try:
                    waited_minutes = max(0, int((now - ticket.updated_at).total_seconds() // 60))
                    title = (ticket.title or '').strip()
                    if len(title) > 60:
                        title = title[:57] + '...'

                    # Детали пользователя: имя, Telegram ID и username
                    full_name = html.escape(ticket.user.full_name or '') if ticket.user else 'Unknown'
                    telegram_id_display = ticket.user.telegram_id if ticket.user else '—'
                    username_display = html.escape(
                        (ticket.user.username or 'отсутствует') if ticket.user else 'отсутствует'
                    )
                    safe_title = html.escape(title) if title else '—'

                    text = (
                        f'⏰ <b>Ожидание ответа на тикет превышено</b>\n\n'
                        f'🆔 <b>ID:</b> <code>{ticket.id}</code>\n'
                        f'👤 <b>Пользователь:</b> {full_name}\n'
                        f'🆔 <b>Telegram ID:</b> <code>{telegram_id_display}</code>\n'
                        f'📱 <b>Username:</b> @{username_display}\n'
                        f'📝 <b>Заголовок:</b> {safe_title}\n'
                        f'⏱️ <b>Ожидает ответа:</b> {waited_minutes} мин\n'
                    )

                    sent = await service.send_ticket_event_notification(text)
                    if sent:
                        ticket.last_sla_reminder_at = now
                        reminders_sent += 1
                        # commit after each to persist timestamp and avoid duplicate reminders on crash
                        await db.commit()
                except Exception as notify_error:
                    logger.error(
                        'Ошибка отправки SLA-уведомления по тикету', ticket_id=ticket.id, notify_error=notify_error
                    )

            if reminders_sent > 0:
                await self._log_monitoring_event(
                    db,
                    'ticket_sla_reminders_sent',
                    f'Отправлено {reminders_sent} SLA-напоминаний по тикетам',
                    {'count': reminders_sent},
                )
        except Exception as e:
            logger.error('Ошибка проверки SLA тикетов', error=e)

    async def _sla_loop(self):
        try:
            interval_seconds = max(10, int(getattr(settings, 'SUPPORT_TICKET_SLA_CHECK_INTERVAL_SECONDS', 60)))
        except Exception:
            interval_seconds = 60
        while self.is_running:
            try:
                async with AsyncSessionLocal() as db:
                    try:
                        await self._check_ticket_sla(db)
                        await db.commit()
                    except Exception as e:
                        logger.error('Ошибка в SLA-проверке', error=e)
                        await db.rollback()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error('Ошибка в SLA-цикле', error=e)
            await asyncio.sleep(interval_seconds)

    async def _log_monitoring_event(
        self, db: AsyncSession, event_type: str, message: str, data: dict[str, Any] = None, is_success: bool = True
    ):
        try:
            log_entry = MonitoringLog(event_type=event_type, message=message, data=data or {}, is_success=is_success)

            db.add(log_entry)
            await db.commit()

        except Exception as e:
            logger.error('Ошибка логирования события мониторинга', error=e)

    async def get_monitoring_status(self, db: AsyncSession) -> dict[str, Any]:
        try:
            from sqlalchemy import desc, select

            recent_events_result = await db.execute(
                select(MonitoringLog).order_by(desc(MonitoringLog.created_at)).limit(10)
            )
            recent_events = recent_events_result.scalars().all()

            yesterday = datetime.now(UTC) - timedelta(days=1)

            events_24h_result = await db.execute(select(MonitoringLog).where(MonitoringLog.created_at >= yesterday))
            events_24h = events_24h_result.scalars().all()

            successful_events = sum(1 for event in events_24h if event.is_success)
            failed_events = sum(1 for event in events_24h if not event.is_success)

            return {
                'is_running': self.is_running,
                'last_update': datetime.now(UTC),
                'recent_events': [
                    {
                        'type': event.event_type,
                        'message': event.message,
                        'success': event.is_success,
                        'created_at': event.created_at,
                    }
                    for event in recent_events
                ],
                'stats_24h': {
                    'total_events': len(events_24h),
                    'successful': successful_events,
                    'failed': failed_events,
                    'success_rate': round(successful_events / len(events_24h) * 100, 1) if events_24h else 0,
                },
            }

        except Exception as e:
            logger.error('Ошибка получения статуса мониторинга', error=e)
            return {
                'is_running': self.is_running,
                'last_update': datetime.now(UTC),
                'recent_events': [],
                'stats_24h': {'total_events': 0, 'successful': 0, 'failed': 0, 'success_rate': 0},
            }

    async def force_check_subscriptions(self, db: AsyncSession) -> dict[str, int]:
        from app.database.crud.subscription import is_recently_updated_by_webhook

        try:
            expired_subscriptions = await get_expired_subscriptions(db)
            expired_count = 0

            for subscription in expired_subscriptions:
                if is_recently_updated_by_webhook(subscription):
                    logger.debug(
                        'Пропуск force-check подписки : обновлена вебхуком недавно', subscription_id=subscription.id
                    )
                    continue
                await deactivate_subscription(db, subscription)
                expired_count += 1

            expiring_subscriptions = await get_expiring_subscriptions(db, 1)
            expiring_count = len(expiring_subscriptions)

            autopay_subscriptions = await get_subscriptions_for_autopay(db)
            autopay_processed = 0

            for subscription in autopay_subscriptions:
                user = await get_user_by_id(db, subscription.user_id)
                if user and user.balance_kopeks >= settings.PRICE_30_DAYS:
                    autopay_processed += 1

            await self._log_monitoring_event(
                db,
                'manual_check_subscriptions',
                f'Принудительная проверка: истекло {expired_count}, истекает {expiring_count}, автоплатежей {autopay_processed}',
                {'expired': expired_count, 'expiring': expiring_count, 'autopay_ready': autopay_processed},
            )

            return {'expired': expired_count, 'expiring': expiring_count, 'autopay_ready': autopay_processed}

        except Exception as e:
            logger.error('Ошибка принудительной проверки подписок', error=e)
            return {'expired': 0, 'expiring': 0, 'autopay_ready': 0}

    async def get_monitoring_logs(
        self, db: AsyncSession, limit: int = 50, event_type: str | None = None, page: int = 1, per_page: int = 20
    ) -> list[dict[str, Any]]:
        try:
            from sqlalchemy import desc, select

            query = select(MonitoringLog).order_by(desc(MonitoringLog.created_at))

            if event_type:
                query = query.where(MonitoringLog.event_type == event_type)

            if page > 1 or per_page != 20:
                offset = (page - 1) * per_page
                query = query.offset(offset).limit(per_page)
            else:
                query = query.limit(limit)

            result = await db.execute(query)
            logs = result.scalars().all()

            return [
                {
                    'id': log.id,
                    'event_type': log.event_type,
                    'message': log.message,
                    'data': log.data,
                    'is_success': log.is_success,
                    'created_at': log.created_at,
                }
                for log in logs
            ]

        except Exception as e:
            logger.error('Ошибка получения логов мониторинга', error=e)
            return []

    async def get_monitoring_logs_count(self, db: AsyncSession, event_type: str | None = None) -> int:
        try:
            from sqlalchemy import func, select

            query = select(func.count(MonitoringLog.id))

            if event_type:
                query = query.where(MonitoringLog.event_type == event_type)

            result = await db.execute(query)
            count = result.scalar()

            return count or 0

        except Exception as e:
            logger.error('Ошибка получения количества логов', error=e)
            return 0

    async def get_monitoring_event_types(self, db: AsyncSession) -> list[str]:
        try:
            from sqlalchemy import select

            result = await db.execute(
                select(MonitoringLog.event_type)
                .where(MonitoringLog.event_type.isnot(None))
                .distinct()
                .order_by(MonitoringLog.event_type)
            )

            return [row[0] for row in result.fetchall() if row[0]]

        except Exception as e:
            logger.error('Ошибка получения списка типов событий мониторинга', error=e)
            return []

    async def cleanup_old_logs(self, db: AsyncSession, days: int = 30) -> int:
        try:
            from sqlalchemy import delete

            if days == 0:
                result = await db.execute(delete(MonitoringLog))
            else:
                cutoff_date = datetime.now(UTC) - timedelta(days=days)
                result = await db.execute(delete(MonitoringLog).where(MonitoringLog.created_at < cutoff_date))

            deleted_count = result.rowcount
            await db.commit()

            if days == 0:
                logger.info('🗑️ Удалены все логи мониторинга ( записей)', deleted_count=deleted_count)
            else:
                logger.info('🗑️ Удалено старых записей логов (старше дней)', deleted_count=deleted_count, days=days)

            return deleted_count

        except Exception as e:
            logger.error('Ошибка очистки логов', error=e)
            await db.rollback()
            return 0


monitoring_service = MonitoringService()
