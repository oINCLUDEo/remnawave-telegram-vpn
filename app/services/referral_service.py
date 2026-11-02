import html
import json

import redis.asyncio as aioredis
import structlog
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.crud.referral import create_referral_earning, get_commission_payment_count, get_user_campaign_id
from app.database.crud.user import add_user_balance, get_user_by_id
from app.database.models import ReferralEarning, TransactionType, User
from app.localization.texts import get_texts
from app.services.notification_delivery_service import (
    notification_delivery_service,
)
from app.utils.user_utils import get_effective_referral_commission_percent


logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pending referral helpers (Redis)
# ---------------------------------------------------------------------------
_PENDING_REFERRAL_TTL = 7 * 24 * 3600  # 7 days

_redis_client: aioredis.Redis | None = None
_redis_initialized: bool = False


def _get_redis() -> aioredis.Redis | None:
    """Lazy async Redis client for pending referral storage."""
    global _redis_client, _redis_initialized
    if _redis_initialized:
        return _redis_client
    try:
        _redis_client = aioredis.from_url(settings.REDIS_URL)
        _redis_initialized = True
        logger.debug('Redis client for pending referrals initialized')
    except Exception as exc:
        logger.warning('Failed to initialize Redis for pending referrals', error=exc)
        _redis_client = None
        _redis_initialized = True
    return _redis_client


async def save_pending_referral(telegram_id: int, referral_code: str, referrer_id: int) -> bool:
    """Save pending referral to Redis for a not-yet-registered user.

    Called from /start handler immediately after resolving the referral code.
    The pending referral is picked up by create_user() or cabinet auth.
    """
    client = _get_redis()
    if client is None:
        return False
    try:
        key = f'pending_referral:{telegram_id}'
        data = json.dumps({'referral_code': referral_code, 'referrer_id': referrer_id})
        await client.setex(key, _PENDING_REFERRAL_TTL, data)
        logger.info(
            'Saved pending referral to Redis',
            telegram_id=telegram_id,
            referral_code=referral_code,
            referrer_id=referrer_id,
        )
        return True
    except Exception as exc:
        logger.warning('Failed to save pending referral to Redis', error=exc)
        return False


async def get_pending_referral(telegram_id: int) -> dict[str, str | int] | None:
    """Get pending referral from Redis.

    Returns ``{'referral_code': ..., 'referrer_id': ...}`` or ``None``.
    """
    client = _get_redis()
    if client is None:
        return None
    try:
        key = f'pending_referral:{telegram_id}'
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as exc:
        logger.warning('Failed to get pending referral from Redis', error=exc)
        return None


async def clear_pending_referral(telegram_id: int) -> None:
    """Clear pending referral after successful registration."""
    client = _get_redis()
    if client is None:
        return
    try:
        await client.delete(f'pending_referral:{telegram_id}')
    except Exception:
        pass


async def _is_commission_limit_reached(db: AsyncSession, referrer_id: int, referral_id: int) -> bool:
    """Проверяет, исчерпан ли лимит комиссионных платежей для пары реферер-реферал."""
    if settings.REFERRAL_MAX_COMMISSION_PAYMENTS <= 0:
        return False
    paid_count = await get_commission_payment_count(db, referrer_id, referral_id)
    if paid_count >= settings.REFERRAL_MAX_COMMISSION_PAYMENTS:
        logger.info(
            'Лимит комиссионных платежей исчерпан',
            referrer_id=referrer_id,
            referral_id=referral_id,
            paid_count=paid_count,
            max_payments=settings.REFERRAL_MAX_COMMISSION_PAYMENTS,
        )
        return True
    return False


def _invite_more_keyboard(texts) -> InlineKeyboardMarkup:
    """«Пригласить ещё»: money from a friend has just come, the best moment to invite another one."""
    from app.keyboards.icons import icon_button

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                icon_button(
                    'referral',
                    texts.t('REFERRAL_INVITE_MORE_BUTTON', 'Пригласить ещё'),
                    callback_data='menu_referrals',
                )
            ]
        ]
    )


def _commission_notification(
    referrer: User, friend: User, amount_kopeks: int, commission_kopeks: int, percent: int, *, purchase: bool = False
) -> str:
    """«+75 ₽ от друга»: a friend paid, and the commission is already on the balance."""
    texts = get_texts(referrer.language)
    fmt = settings.format_price
    if purchase:
        body = texts.t(
            'REFERRAL_PURCHASE_COMMISSION_TEXT',
            'Ваш друг {name} оплатил покупку на {amount}. Ваши {percent}% уже на балансе.',
        )
    else:
        body = texts.t(
            'REFERRAL_COMMISSION_TEXT',
            'Ваш друг {name} пополнил баланс на {amount}. Ваши {percent}% уже на балансе.',
        )
    return (
        texts.t('REFERRAL_INCOME_TITLE', '💰 <b>+{amount} от друга</b>').format(amount=fmt(commission_kopeks))
        + '\n'
        + body.format(name=html.escape(friend.full_name or ''), amount=fmt(amount_kopeks), percent=percent)
    )


async def send_referral_notification(
    bot: Bot,
    telegram_id: int | None,
    message: str,
    user: User | None = None,
    bonus_kopeks: int = 0,
    referral_name: str = '',
    reply_markup: InlineKeyboardMarkup | None = None,
):
    """
    Отправляет реферальное уведомление в Telegram или по email.

    In Telegram it comes with the «Пригласить друга» banner (``referral``) when
    the designer's file exists, and with *reply_markup* («Пригласить ещё»).

    Args:
        bot: Telegram Bot instance
        telegram_id: Telegram user ID (может быть None для email-пользователей)
        message: Текст уведомления
        user: User object (для email-only пользователей)
        bonus_kopeks: Сумма бонуса в копейках
        referral_name: Имя реферала
    """
    # Handle email-only users via notification delivery service
    if telegram_id is None:
        if user is not None:
            success = await notification_delivery_service.notify_referral_bonus(
                user=user,
                bonus_kopeks=bonus_kopeks,
                referral_name=referral_name,
                telegram_message=message,
            )
            if success:
                logger.info('✅ Email уведомление о реферале отправлено пользователю', user_id=user.id)
            else:
                logger.warning('⚠️ Не удалось отправить email уведомление пользователю', user_id=user.id)
        else:
            logger.debug('Пропуск уведомления: пользователь без telegram_id и без User object')
        return

    try:
        from app.utils.message_patch import send_banner_message

        await send_banner_message(
            bot,
            banner='referral',
            chat_id=telegram_id,
            text=message,
            parse_mode='HTML',
            reply_markup=reply_markup,
        )
        logger.info('✅ Уведомление отправлено пользователю', telegram_id=telegram_id)
    except Exception as e:
        logger.error('❌ Ошибка отправки уведомления пользователю', telegram_id=telegram_id, error=e)


async def process_referral_registration(db: AsyncSession, new_user_id: int, referrer_id: int, bot: Bot = None):
    try:
        if new_user_id == referrer_id:
            logger.warning('Self-referral blocked in process_referral_registration', user_id=new_user_id)
            return False

        new_user = await get_user_by_id(db, new_user_id)
        referrer = await get_user_by_id(db, referrer_id)

        if not new_user or not referrer:
            logger.error(
                'Пользователи не найдены: new_user_id=, referrer_id', new_user_id=new_user_id, referrer_id=referrer_id
            )
            return False

        if new_user.referred_by_id != referrer_id:
            logger.error('Пользователь не привязан к рефереру', new_user_id=new_user_id, referrer_id=referrer_id)
            return False

        campaign_id = await get_user_campaign_id(db, new_user_id)
        await create_referral_earning(
            db=db,
            user_id=referrer_id,
            referral_id=new_user_id,
            amount_kopeks=0,
            reason='referral_registration_pending',
            campaign_id=campaign_id,
        )

        try:
            from app.services.referral_contest_service import referral_contest_service

            await referral_contest_service.on_referral_registration(db, new_user_id)
        except Exception as exc:
            logger.debug('Не удалось записать конкурсную регистрацию', exc=exc)

        if bot:
            commission_percent = get_effective_referral_commission_percent(referrer)
            fmt = settings.format_price
            minimum = fmt(settings.REFERRAL_MINIMUM_TOPUP_KOPEKS)

            # The invited person: who invited them and what the first top-up brings.
            friend_texts = get_texts(new_user.language)
            if settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS > 0:
                referral_notification = friend_texts.t(
                    'REFERRAL_WELCOME_BONUS',
                    '🎁 <b>Приглашение от друга: {name}</b>\n'
                    'Пополните баланс от {min}, и мы добавим {bonus} в подарок.',
                )
            else:
                referral_notification = friend_texts.t('REFERRAL_WELCOME', '🤝 <b>Приглашение от друга: {name}</b>')
            referral_notification = referral_notification.format(
                name=html.escape(referrer.full_name or ''),
                min=minimum,
                bonus=fmt(settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS),
            )
            await send_referral_notification(bot, new_user.telegram_id, referral_notification, user=new_user)

            # The inviter: who came and what they will get, in one sentence.
            texts = get_texts(referrer.language)
            inviter_title = texts.t('REFERRAL_NEW_FRIEND_TITLE', '🤝 <b>Новый друг по вашей ссылке: {name}</b>')
            if settings.REFERRAL_INVITER_BONUS_KOPEKS > 0 and commission_percent > 0:
                terms = texts.t(
                    'REFERRAL_NEW_FRIEND_BONUS_AND_PERCENT',
                    'Когда друг пополнит баланс от {min}, вам придут {bonus}, а потом {percent}% с каждой его оплаты.',
                )
            elif settings.REFERRAL_INVITER_BONUS_KOPEKS > 0:
                terms = texts.t('REFERRAL_NEW_FRIEND_BONUS', 'Когда друг пополнит баланс от {min}, вам придут {bonus}.')
            elif commission_percent > 0:
                terms = texts.t('REFERRAL_NEW_FRIEND_PERCENT', 'С каждой его оплаты вам будут приходить {percent}%.')
            else:
                terms = ''
            inviter_notification = inviter_title.format(name=html.escape(new_user.full_name or ''))
            if terms:
                inviter_notification += '\n' + terms.format(
                    min=minimum, bonus=fmt(settings.REFERRAL_INVITER_BONUS_KOPEKS), percent=commission_percent
                )
            await send_referral_notification(
                bot,
                referrer.telegram_id,
                inviter_notification,
                user=referrer,
                referral_name=new_user.full_name,
                reply_markup=_invite_more_keyboard(texts),
            )

        logger.info(
            '✅ Зарегистрирован реферал для . Бонусы будут выданы после пополнения.',
            new_user_id=new_user_id,
            referrer_id=referrer_id,
        )
        return True

    except Exception as e:
        logger.error('Ошибка обработки реферальной регистрации', error=e)
        return False


async def process_referral_topup(db: AsyncSession, user_id: int, topup_amount_kopeks: int, bot: Bot = None):
    try:
        user = await get_user_by_id(db, user_id)
        if not user or not user.referred_by_id:
            logger.debug('Пользователь не является рефералом, пропуск комиссии', user_id=user_id)
            return True

        referrer = await get_user_by_id(db, user.referred_by_id)
        if not referrer:
            logger.error(
                'Реферер не найден, комиссия не начислена', referred_by_id=user.referred_by_id, user_id=user_id
            )
            return False

        campaign_id = await get_user_campaign_id(db, user.id)
        commission_percent = get_effective_referral_commission_percent(referrer)

        logger.info(
            'Обработка реферального пополнения',
            user_id=user_id,
            referrer_id=referrer.id,
            topup_amount_kopeks=topup_amount_kopeks,
            campaign_id=campaign_id,
            commission_percent=commission_percent,
            has_made_first_topup=user.has_made_first_topup,
        )
        qualifies_for_first_bonus = topup_amount_kopeks >= settings.REFERRAL_MINIMUM_TOPUP_KOPEKS
        commission_amount = 0
        if commission_percent > 0:
            commission_amount = int(topup_amount_kopeks * commission_percent / 100)

        if not user.has_made_first_topup:
            if not qualifies_for_first_bonus:
                logger.info(
                    'Пополнение на ₽ меньше минимума для первого бонуса, но комиссия будет начислена',
                    user_id=user_id,
                    topup_amount_kopeks=topup_amount_kopeks / 100,
                )

                if commission_amount > 0 and await _is_commission_limit_reached(db, referrer.id, user.id):
                    return True

                if commission_amount > 0:
                    balance_ok = await add_user_balance(
                        db,
                        referrer,
                        commission_amount,
                        f'Комиссия {commission_percent}% с пополнения {user.full_name}',
                        transaction_type=TransactionType.REFERRAL_REWARD,
                        bot=bot,
                    )

                    if balance_ok:
                        await create_referral_earning(
                            db=db,
                            user_id=referrer.id,
                            referral_id=user.id,
                            amount_kopeks=commission_amount,
                            reason='referral_commission_topup',
                            campaign_id=campaign_id,
                        )

                        logger.info(
                            '💰 Комиссия с пополнения: получил ₽ (до первого бонуса)',
                            telegram_id=referrer.telegram_id,
                            commission_amount=commission_amount / 100,
                        )

                        if bot:
                            commission_notification = _commission_notification(
                                referrer, user, topup_amount_kopeks, commission_amount, commission_percent
                            )
                            await send_referral_notification(
                                bot,
                                referrer.telegram_id,
                                commission_notification,
                                user=referrer,
                                bonus_kopeks=commission_amount,
                                referral_name=user.full_name,
                                reply_markup=_invite_more_keyboard(get_texts(referrer.language)),
                            )
                    else:
                        logger.error(
                            'Не удалось начислить комиссию на баланс, ReferralEarning не создан',
                            referrer_id=referrer.id,
                            commission_amount=commission_amount,
                        )

                return True

            user.has_made_first_topup = True
            await db.commit()

            try:
                await db.execute(
                    delete(ReferralEarning).where(
                        ReferralEarning.user_id == referrer.id,
                        ReferralEarning.referral_id == user.id,
                        ReferralEarning.reason == 'referral_registration_pending',
                    )
                )
                await db.commit()
                logger.info("🗑️ Удалена запись 'ожидание пополнения' для реферала", user_id=user.id)
            except Exception as e:
                logger.error('Ошибка удаления записи ожидания', error=e)

            if settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS > 0:
                bonus_ok = await add_user_balance(
                    db,
                    user,
                    settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS,
                    'Бонус за первое пополнение по реферальной программе',
                    transaction_type=TransactionType.REFERRAL_REWARD,
                    bot=bot,
                )
                if bonus_ok:
                    logger.info(
                        '💰 Реферал получил бонус ₽',
                        user_id=user.id,
                        REFERRAL_FIRST_TOPUP_BONUS_KOPEKS=settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS / 100,
                    )

                    if bot:
                        friend_texts = get_texts(user.language)
                        bonus_notification = friend_texts.t(
                            'REFERRAL_FRIEND_BONUS',
                            '🎁 <b>+{bonus} на баланс</b>\nЭто подарок за первое пополнение по приглашению друга.',
                        ).format(bonus=settings.format_price(settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS))
                        await send_referral_notification(
                            bot,
                            user.telegram_id,
                            bonus_notification,
                            user=user,
                            bonus_kopeks=settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS,
                        )
                else:
                    logger.error(
                        'Не удалось начислить бонус за первое пополнение',
                        user_id=user.id,
                        bonus_kopeks=settings.REFERRAL_FIRST_TOPUP_BONUS_KOPEKS,
                    )

            commission_amount = int(topup_amount_kopeks * commission_percent / 100)
            inviter_bonus = settings.REFERRAL_INVITER_BONUS_KOPEKS + commission_amount

            if inviter_bonus > 0:
                balance_ok = await add_user_balance(
                    db,
                    referrer,
                    inviter_bonus,
                    f'Бонус за первое пополнение реферала {user.full_name}',
                    transaction_type=TransactionType.REFERRAL_REWARD,
                    bot=bot,
                )

                if balance_ok:
                    await create_referral_earning(
                        db=db,
                        user_id=referrer.id,
                        referral_id=user.id,
                        amount_kopeks=inviter_bonus,
                        reason='referral_first_topup',
                        campaign_id=campaign_id,
                    )

                    referrer_id = referrer.telegram_id or referrer.email or f'user#{referrer.id}'
                    logger.info(
                        '💰 Реферер получил бонус ₽', referrer_id=referrer_id, inviter_bonus=inviter_bonus / 100
                    )

                    if bot:
                        # «+175 ₽ от друга», what it is made of, and what comes next (msg 15 of the audit).
                        texts = get_texts(referrer.language)
                        fmt = settings.format_price
                        breakdown = []
                        if settings.REFERRAL_INVITER_BONUS_KOPEKS > 0:
                            breakdown.append(
                                texts.t('REFERRAL_FIRST_TOPUP_BONUS_LINE', '🎁 {bonus} за первое пополнение').format(
                                    bonus=fmt(settings.REFERRAL_INVITER_BONUS_KOPEKS)
                                )
                            )
                        if commission_amount > 0:
                            percent_line = texts.t(
                                'REFERRAL_FIRST_TOPUP_PERCENT_LINE', '📈 {commission} — {percent}% от его оплаты'
                            )
                            breakdown.append(
                                percent_line.format(commission=fmt(commission_amount), percent=commission_percent)
                            )
                        parts = [
                            texts.t('REFERRAL_INCOME_TITLE', '💰 <b>+{amount} от друга</b>').format(
                                amount=fmt(inviter_bonus)
                            )
                            + '\n'
                            + texts.t(
                                'REFERRAL_FIRST_TOPUP_TEXT', 'Ваш друг {name} впервые пополнил баланс на {amount}.'
                            ).format(name=html.escape(user.full_name or ''), amount=fmt(topup_amount_kopeks))
                        ]
                        if len(breakdown) > 1:
                            # One part needs no breakdown: the title already says it.
                            parts.append('\n'.join(breakdown))
                        if commission_percent > 0:
                            parts.append(
                                texts.t(
                                    'REFERRAL_FIRST_TOPUP_NEXT',
                                    'Дальше {percent}% с каждой его оплаты будут приходить на ваш баланс.',
                                ).format(percent=commission_percent)
                            )
                        await send_referral_notification(
                            bot,
                            referrer.telegram_id,
                            '\n\n'.join(parts),
                            user=referrer,
                            bonus_kopeks=inviter_bonus,
                            referral_name=user.full_name,
                            reply_markup=_invite_more_keyboard(texts),
                        )
                else:
                    logger.error(
                        'Не удалось начислить бонус на баланс, ReferralEarning не создан',
                        referrer_id=referrer.id,
                        inviter_bonus=inviter_bonus,
                    )

        elif commission_amount > 0:
            if await _is_commission_limit_reached(db, referrer.id, user.id):
                return True

            balance_ok = await add_user_balance(
                db,
                referrer,
                commission_amount,
                f'Комиссия {commission_percent}% с пополнения {user.full_name}',
                transaction_type=TransactionType.REFERRAL_REWARD,
                bot=bot,
            )

            if balance_ok:
                await create_referral_earning(
                    db=db,
                    user_id=referrer.id,
                    referral_id=user.id,
                    amount_kopeks=commission_amount,
                    reason='referral_commission_topup',
                    campaign_id=campaign_id,
                )

                referrer_id = referrer.telegram_id or referrer.email or f'user#{referrer.id}'
                logger.info(
                    '💰 Комиссия с пополнения: получил ₽',
                    referrer_id=referrer_id,
                    commission_amount=commission_amount / 100,
                )

                if bot:
                    commission_notification = _commission_notification(
                        referrer, user, topup_amount_kopeks, commission_amount, commission_percent
                    )
                    await send_referral_notification(
                        bot,
                        referrer.telegram_id,
                        commission_notification,
                        user=referrer,
                        bonus_kopeks=commission_amount,
                        referral_name=user.full_name,
                        reply_markup=_invite_more_keyboard(get_texts(referrer.language)),
                    )
            else:
                logger.error(
                    'Не удалось начислить комиссию на баланс, ReferralEarning не создан',
                    referrer_id=referrer.id,
                    commission_amount=commission_amount,
                )

        return True

    except Exception as e:
        logger.error('Ошибка обработки пополнения реферала', error=e)
        return False


async def process_referral_purchase(
    db: AsyncSession, user_id: int, purchase_amount_kopeks: int, transaction_id: int = None, bot: Bot = None
):
    """Process referral commission for balance-based subscription purchases.

    INTENTIONALLY UNUSED. This function is NOT called from subscription purchase flows.
    Commission is only earned when referred users make actual payments through payment
    providers (via process_referral_topup). Balance-based subscription purchases
    (from admin credits, campaign bonuses, or promo codes) do NOT trigger commission,
    because the partner already received commission at the time the user topped up
    their balance. Calling this would cause double-commission.

    Kept for potential future use cases where balance-independent purchase tracking
    is needed (e.g. audit trail records with zero commission).
    """
    try:
        user = await get_user_by_id(db, user_id)
        if not user or not user.referred_by_id:
            return True

        referrer = await get_user_by_id(db, user.referred_by_id)
        if not referrer:
            logger.error('Реферер не найден', referred_by_id=user.referred_by_id)
            return False

        commission_percent = get_effective_referral_commission_percent(referrer)

        commission_amount = int(purchase_amount_kopeks * commission_percent / 100)

        if commission_amount > 0:
            await add_user_balance(
                db, referrer, commission_amount, f'Комиссия {commission_percent}% с покупки {user.full_name}', bot=bot
            )

            campaign_id = await get_user_campaign_id(db, user.id)
            await create_referral_earning(
                db=db,
                user_id=referrer.id,
                referral_id=user.id,
                amount_kopeks=commission_amount,
                reason='referral_commission',
                referral_transaction_id=transaction_id,
                campaign_id=campaign_id,
            )

            referrer_id = referrer.telegram_id or referrer.email or f'user#{referrer.id}'
            logger.info(
                '💰 Комиссия с покупки: получил ₽', referrer_id=referrer_id, commission_amount=commission_amount / 100
            )

            if bot:
                purchase_commission_notification = _commission_notification(
                    referrer, user, purchase_amount_kopeks, commission_amount, commission_percent, purchase=True
                )
                await send_referral_notification(
                    bot,
                    referrer.telegram_id,
                    purchase_commission_notification,
                    user=referrer,
                    bonus_kopeks=commission_amount,
                    referral_name=user.full_name,
                )

        if not user.has_had_paid_subscription:
            user.has_had_paid_subscription = True
            await db.commit()
            logger.info('✅ Пользователь отмечен как имевший платную подписку', user_id=user_id)

        return True

    except Exception as e:
        logger.error('Ошибка обработки покупки реферала', error=e)
        import traceback

        logger.error('Полный traceback', format_exc=traceback.format_exc())
        return False
