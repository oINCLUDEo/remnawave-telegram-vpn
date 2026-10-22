import html

import structlog
from aiogram import types
from aiogram.fsm.context import FSMContext

from app.config import settings
from app.database.models import User
from app.external.telegram_stars import TelegramStarsService
from app.keyboards.icons import STYLE_PAY
from app.keyboards.inline import get_back_keyboard
from app.localization.texts import get_texts
from app.services.payment_service import PaymentService
from app.states import BalanceStates
from app.utils.decorators import error_handler
from app.utils.payment_utils import get_topup_amount_prompt, topup_methods_callback


logger = structlog.get_logger(__name__)


def _stars_unavailable_text(texts) -> str:
    return texts.t('PAYMENT_STARS_UNAVAILABLE', 'Оплата звёздами временно недоступна. Выберите другой способ оплаты.')


@error_handler
async def start_stars_payment(callback: types.CallbackQuery, db_user: User, state: FSMContext):
    texts = get_texts(db_user.language)

    if not settings.TELEGRAM_STARS_ENABLED:
        await callback.answer(_stars_unavailable_text(texts), show_alert=True)
        return

    # Проверка ограничения на пополнение
    if getattr(db_user, 'restriction_topup', False):
        reason = html.escape(getattr(db_user, 'restriction_reason', None) or 'Действие ограничено администратором')
        support_url = settings.get_support_contact_url()
        keyboard = []
        if support_url:
            keyboard.append([types.InlineKeyboardButton(text='🆘 Обжаловать', url=support_url)])
        keyboard.append([types.InlineKeyboardButton(text=texts.BACK, callback_data='menu_balance')])

        await callback.message.edit_text(
            f'🚫 <b>Пополнение ограничено</b>\n\n{reason}\n\n'
            'Если вы считаете это ошибкой, вы можете обжаловать решение.',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        await callback.answer()
        return

    message_text = get_topup_amount_prompt(db_user.language, 'stars', '⭐')

    keyboard = get_back_keyboard(db_user.language)

    await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='HTML')

    await state.update_data(
        stars_prompt_message_id=callback.message.message_id,
        stars_prompt_chat_id=callback.message.chat.id,
    )

    await state.set_state(BalanceStates.waiting_for_amount)
    await state.update_data(payment_method='stars')
    await callback.answer()


@error_handler
async def process_stars_payment_amount(message: types.Message, db_user: User, amount_kopeks: int, state: FSMContext):
    texts = get_texts(db_user.language)

    # Проверка ограничения на пополнение
    if getattr(db_user, 'restriction_topup', False):
        reason = html.escape(getattr(db_user, 'restriction_reason', None) or 'Действие ограничено администратором')
        support_url = settings.get_support_contact_url()
        keyboard = []
        if support_url:
            keyboard.append([types.InlineKeyboardButton(text='🆘 Обжаловать', url=support_url)])
        keyboard.append([types.InlineKeyboardButton(text=texts.BACK, callback_data='menu_balance')])

        await message.answer(
            f'🚫 <b>Пополнение ограничено</b>\n\n{reason}\n\n'
            'Если вы считаете это ошибкой, вы можете обжаловать решение.',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode='HTML',
        )
        await state.clear()
        return

    texts = get_texts(db_user.language)

    if not settings.TELEGRAM_STARS_ENABLED:
        await message.answer(_stars_unavailable_text(texts))
        return

    try:
        amount_rubles = amount_kopeks / 100
        stars_amount = TelegramStarsService.calculate_stars_from_rubles(amount_rubles)

        payment_service = PaymentService(message.bot)
        invoice_link = await payment_service.create_stars_invoice(
            amount_kopeks=amount_kopeks,
            description=f'Пополнение баланса на {texts.format_price(amount_kopeks)}',
            payload=f'balance_{db_user.id}_{amount_kopeks}',
        )

        # Same invoice as for card and СБП: the amount on a green button, no instructions.
        pay_label = texts.t('PAYMENT_PAY_BUTTON', 'Оплатить {amount}').format(amount=texts.format_price(amount_kopeks))
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text=f'⭐ {pay_label}', url=invoice_link, style=STYLE_PAY)],
                [types.InlineKeyboardButton(text=texts.BACK, callback_data=topup_methods_callback(amount_kopeks))],
            ]
        )

        state_data = await state.get_data()

        prompt_message_id = state_data.get('stars_prompt_message_id')
        prompt_chat_id = state_data.get('stars_prompt_chat_id', message.chat.id)

        # Only the bot's own messages go: a typed amount stays with its 👌 reaction.
        sender = getattr(message, 'from_user', None)  # an old screen may be InaccessibleMessage
        if sender and sender.is_bot:
            try:
                await message.delete()
            except Exception as delete_error:  # pragma: no cover - зависит от прав бота
                logger.warning('Не удалось удалить сообщение бота перед счётом Stars', delete_error=delete_error)

        if prompt_message_id and prompt_message_id != message.message_id:
            try:
                await message.bot.delete_message(prompt_chat_id, prompt_message_id)
            except Exception as delete_error:  # pragma: no cover - диагностический лог
                logger.warning('Не удалось удалить сообщение с запросом суммы Stars', delete_error=delete_error)

        invoice_text = texts.t(
            'STARS_INVOICE_TEXT',
            '⭐ <b>Оплата {amount} звёздами</b>\nСпишется {stars} ⭐, деньги придут на баланс сразу после оплаты.',
        ).format(amount=texts.format_price(amount_kopeks), stars=stars_amount)
        invoice_message = await message.answer(invoice_text, reply_markup=keyboard, parse_mode='HTML')

        await state.update_data(
            stars_invoice_message_id=invoice_message.message_id,
            stars_invoice_chat_id=invoice_message.chat.id,
        )

        await state.set_state(None)

    except Exception as e:
        logger.error('Ошибка создания Stars invoice', error=e)
        await message.answer(
            texts.t(
                'PAYMENT_CREATE_FAILED',
                '❌ Не удалось открыть страницу оплаты. Попробуйте ещё раз или выберите другой способ оплаты.',
            ),
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text=texts.BACK, callback_data=topup_methods_callback(amount_kopeks))]
                ]
            ),
        )
