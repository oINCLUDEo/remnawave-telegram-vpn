import html
from datetime import UTC, datetime

import structlog
from aiogram import types
from aiogram.fsm.context import FSMContext
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import User
from app.keyboards.icons import STYLE_PAY, icon_button, tg_emoji
from app.keyboards.inline import get_back_keyboard
from app.localization.texts import get_texts
from app.services.payment_service import PaymentService
from app.states import BalanceStates
from app.utils.decorators import error_handler
from app.utils.payment_utils import get_topup_amount_error, get_topup_amount_prompt, topup_methods_callback


logger = structlog.get_logger(__name__)


def _card_unavailable_text(texts) -> str:
    return texts.t('PAYMENT_CARD_UNAVAILABLE', 'Оплата картой временно недоступна. Выберите другой способ оплаты.')


def _sbp_unavailable_text(texts) -> str:
    return texts.t('PAYMENT_SBP_UNAVAILABLE', 'Оплата по СБП временно недоступна. Выберите другой способ оплаты.')


async def _send_create_failed(message: types.Message, texts, amount_kopeks: int) -> None:
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


def _invoice_text(texts, title: str, extra_line: str | None = None) -> str:
    """One invoice for card and СБП: amount and method, when the money arrives, the payee."""
    lines = [title, texts.t('PAYMENT_INVOICE_ARRIVES', 'Деньги придут на баланс сразу после оплаты.')]
    if extra_line:
        lines.append(extra_line)
    statement_name = (settings.YOOKASSA_STATEMENT_NAME or '').strip()
    if statement_name:
        # Named as in the bank statement, so the user knows the payment goes where it should.
        lines.append(
            texts.t(
                'PAYMENT_INVOICE_STATEMENT_NAME',
                '<blockquote>Получатель в выписке банка: «{name}»</blockquote>',
            ).format(name=html.escape(statement_name))
        )
    return '\n'.join(lines)


def _invoice_keyboard(
    texts, amount_kopeks: int, local_payment_id: int, confirmation_url: str | None
) -> types.InlineKeyboardMarkup:
    rows = []
    if confirmation_url:
        # The amount on the button answers "how much will be charged".
        pay_label = texts.t('PAYMENT_PAY_BUTTON', 'Оплатить {amount}').format(amount=texts.format_price(amount_kopeks))
        rows.append([icon_button('payment', pay_label, url=confirmation_url, style=STYLE_PAY)])
    rows.append(
        [
            types.InlineKeyboardButton(
                text=texts.t('PAYMENT_CHECK_BUTTON', 'Проверить оплату'),
                callback_data=f'check_yookassa_{local_payment_id}',
            ),
            types.InlineKeyboardButton(text=texts.BACK, callback_data=topup_methods_callback(amount_kopeks)),
        ]
    )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


async def _delete_amount_prompt(message: types.Message, state: FSMContext, log_label: str) -> None:
    """Remove the bot's own messages before the invoice: the amount prompt or the methods screen.

    A typed amount stays in the chat with its 👌 reaction.
    """
    state_data = await state.get_data()
    prompt_message_id = state_data.get('yookassa_prompt_message_id')
    prompt_chat_id = state_data.get('yookassa_prompt_chat_id', message.chat.id)

    sender = getattr(message, 'from_user', None)  # an old screen may be InaccessibleMessage
    if sender and sender.is_bot:
        try:
            await message.delete()
        except Exception as delete_error:  # pragma: no cover - зависит от прав бота
            logger.warning(
                'Не удалось удалить сообщение бота перед счётом', log_label=log_label, delete_error=delete_error
            )

    if prompt_message_id and prompt_message_id != message.message_id:
        try:
            await message.bot.delete_message(prompt_chat_id, prompt_message_id)
        except Exception as delete_error:  # pragma: no cover - диагностический лог
            logger.warning(
                'Не удалось удалить сообщение с запросом суммы', log_label=log_label, delete_error=delete_error
            )


@error_handler
async def start_yookassa_payment(callback: types.CallbackQuery, db_user: User, state: FSMContext):
    texts = get_texts(db_user.language)

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

    if not settings.is_yookassa_enabled():
        await callback.answer(_card_unavailable_text(texts), show_alert=True)
        return

    message_text = get_topup_amount_prompt(db_user.language, 'yookassa', tg_emoji('payment'))

    keyboard = get_back_keyboard(db_user.language)

    await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='HTML')

    await state.set_state(BalanceStates.waiting_for_amount)
    await state.update_data(payment_method='yookassa')
    await state.update_data(
        yookassa_prompt_message_id=callback.message.message_id,
        yookassa_prompt_chat_id=callback.message.chat.id,
    )
    await callback.answer()


@error_handler
async def start_yookassa_sbp_payment(callback: types.CallbackQuery, db_user: User, state: FSMContext):
    texts = get_texts(db_user.language)

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

    if not settings.is_yookassa_enabled() or not settings.YOOKASSA_SBP_ENABLED:
        await callback.answer(_sbp_unavailable_text(texts), show_alert=True)
        return

    message_text = get_topup_amount_prompt(db_user.language, 'yookassa_sbp', '🏦')

    keyboard = get_back_keyboard(db_user.language)

    await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='HTML')

    await state.set_state(BalanceStates.waiting_for_amount)
    await state.update_data(payment_method='yookassa_sbp')
    await state.update_data(
        yookassa_prompt_message_id=callback.message.message_id,
        yookassa_prompt_chat_id=callback.message.chat.id,
    )
    await callback.answer()


@error_handler
async def process_yookassa_payment_amount(
    message: types.Message, db_user: User, db: AsyncSession, amount_kopeks: int, state: FSMContext
):
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

    if not settings.is_yookassa_enabled():
        await message.answer(_card_unavailable_text(texts))
        return

    limit_error = get_topup_amount_error(db_user.language, 'yookassa', amount_kopeks)
    if limit_error:
        await message.answer(limit_error, reply_markup=get_back_keyboard(db_user.language))
        return

    try:
        payment_service = PaymentService(message.bot)

        payment_result = await payment_service.create_yookassa_payment(
            db=db,
            user_id=db_user.id,
            amount_kopeks=amount_kopeks,
            description=settings.get_balance_payment_description(amount_kopeks, telegram_user_id=db_user.telegram_id),
            receipt_email=None,
            receipt_phone=None,
            metadata={
                'user_telegram_id': str(db_user.telegram_id),
                'user_username': db_user.username or '',
                'purpose': 'balance_topup',
            },
        )

        confirmation_url = (payment_result or {}).get('confirmation_url')
        if not confirmation_url:
            await _send_create_failed(message, texts, amount_kopeks)
            await state.clear()
            return

        keyboard = _invoice_keyboard(texts, amount_kopeks, payment_result['local_payment_id'], confirmation_url)

        await _delete_amount_prompt(message, state, 'card')

        title = texts.t('PAYMENT_INVOICE_CARD_TITLE', '{icon} <b>Оплата {amount} картой</b>').format(
            icon=tg_emoji('payment'), amount=texts.format_price(amount_kopeks)
        )
        invoice_message = await message.answer(_invoice_text(texts, title), reply_markup=keyboard, parse_mode='HTML')

        try:
            from app.services import payment_service as payment_module

            payment = await payment_module.get_yookassa_payment_by_local_id(db, payment_result['local_payment_id'])
            if payment:
                metadata = dict(getattr(payment, 'metadata_json', {}) or {})
                metadata['invoice_message'] = {
                    'chat_id': invoice_message.chat.id,
                    'message_id': invoice_message.message_id,
                }
                await db.execute(
                    update(payment.__class__)
                    .where(payment.__class__.id == payment.id)
                    .values(metadata_json=metadata, updated_at=datetime.now(UTC))
                )
                await db.commit()
        except Exception as error:  # pragma: no cover - диагностический лог
            logger.warning('Не удалось сохранить сообщение YooKassa', error=error)

        await state.update_data(
            yookassa_invoice_message_id=invoice_message.message_id,
            yookassa_invoice_chat_id=invoice_message.chat.id,
        )

        await state.clear()
        logger.info(
            'Создан платеж YooKassa для пользователя ₽, ID',
            telegram_id=db_user.telegram_id,
            value=amount_kopeks // 100,
            payment_result=payment_result['yookassa_payment_id'],
        )

    except Exception as e:
        logger.error('Ошибка создания YooKassa платежа', error=e)
        await _send_create_failed(message, texts, amount_kopeks)
        await state.clear()


@error_handler
async def process_yookassa_sbp_payment_amount(
    message: types.Message, db_user: User, db: AsyncSession, amount_kopeks: int, state: FSMContext
):
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

    if not settings.is_yookassa_enabled() or not settings.YOOKASSA_SBP_ENABLED:
        await message.answer(_sbp_unavailable_text(texts))
        return

    limit_error = get_topup_amount_error(db_user.language, 'yookassa_sbp', amount_kopeks)
    if limit_error:
        await message.answer(limit_error, reply_markup=get_back_keyboard(db_user.language))
        return

    try:
        payment_service = PaymentService(message.bot)

        payment_result = await payment_service.create_yookassa_sbp_payment(
            db=db,
            user_id=db_user.id,
            amount_kopeks=amount_kopeks,
            description=settings.get_balance_payment_description(amount_kopeks, telegram_user_id=db_user.telegram_id),
            receipt_email=None,
            receipt_phone=None,
            metadata={
                'user_telegram_id': str(db_user.telegram_id),
                'user_username': db_user.username or '',
                'purpose': 'balance_topup_sbp',
            },
        )

        if not payment_result:
            await _send_create_failed(message, texts, amount_kopeks)
            await state.clear()
            return

        confirmation_url = payment_result.get('confirmation_url')
        qr_confirmation_data = payment_result.get('qr_confirmation_data')

        if not confirmation_url and not qr_confirmation_data:
            await _send_create_failed(message, texts, amount_kopeks)
            await state.clear()
            return

        # Подготовим QR-код для вставки в основное сообщение
        qr_photo = None
        if qr_confirmation_data:
            try:
                # Импортируем необходимые модули для генерации QR-кода
                from io import BytesIO

                import qrcode
                from aiogram.types import BufferedInputFile

                # Создаем QR-код из полученных данных
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(qr_confirmation_data)
                qr.make(fit=True)

                img = qr.make_image(fill_color='black', back_color='white')

                # Сохраняем изображение в байты
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)

                qr_photo = BufferedInputFile(img_bytes.getvalue(), filename='qrcode.png')
            except ImportError:
                logger.warning('qrcode библиотека не установлена, QR-код не будет сгенерирован')
            except Exception as e:
                logger.error('Ошибка генерации QR-кода', error=e)

        # Если нет QR-данных из YooKassa, но есть URL, генерируем QR-код из URL
        if not qr_photo and confirmation_url:
            try:
                # Импортируем необходимые модули для генерации QR-кода
                from io import BytesIO

                import qrcode
                from aiogram.types import BufferedInputFile

                # Создаем QR-код из URL
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(confirmation_url)
                qr.make(fit=True)

                img = qr.make_image(fill_color='black', back_color='white')

                # Сохраняем изображение в байты
                img_bytes = BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)

                qr_photo = BufferedInputFile(img_bytes.getvalue(), filename='qrcode.png')
            except ImportError:
                logger.warning('qrcode библиотека не установлена, QR-код не будет сгенерирован')
            except Exception as e:
                logger.error('Ошибка генерации QR-кода из URL', error=e)

        if not confirmation_url and not qr_photo:
            # No link and the QR code could not be drawn: there is nothing to pay with.
            await _send_create_failed(message, texts, amount_kopeks)
            await state.clear()
            return

        keyboard = _invoice_keyboard(texts, amount_kopeks, payment_result['local_payment_id'], confirmation_url)

        await _delete_amount_prompt(message, state, 'sbp')

        title = texts.t('PAYMENT_INVOICE_SBP_TITLE', '🏦 <b>Оплата {amount} по СБП</b>').format(
            amount=texts.format_price(amount_kopeks)
        )
        qr_line = None
        if qr_photo:
            # From a computer people pay by scanning the code with their phone.
            qr_line = texts.t(
                'PAYMENT_INVOICE_SBP_QR',
                'Если вы за компьютером, отсканируйте QR-код камерой телефона.',
            )
        message_text = _invoice_text(texts, title, qr_line)

        if qr_photo:
            invoice_message = await message.answer_photo(
                photo=qr_photo, caption=message_text, reply_markup=keyboard, parse_mode='HTML'
            )
        else:
            invoice_message = await message.answer(message_text, reply_markup=keyboard, parse_mode='HTML')

        try:
            from app.services import payment_service as payment_module

            payment = await payment_module.get_yookassa_payment_by_local_id(db, payment_result['local_payment_id'])
            if payment:
                metadata = dict(getattr(payment, 'metadata_json', {}) or {})
                metadata['invoice_message'] = {
                    'chat_id': invoice_message.chat.id,
                    'message_id': invoice_message.message_id,
                }
                await db.execute(
                    update(payment.__class__)
                    .where(payment.__class__.id == payment.id)
                    .values(metadata_json=metadata, updated_at=datetime.now(UTC))
                )
                await db.commit()
        except Exception as error:  # pragma: no cover - диагностический лог
            logger.warning('Не удалось сохранить сообщение YooKassa (СБП)', error=error)

        await state.update_data(
            yookassa_invoice_message_id=invoice_message.message_id,
            yookassa_invoice_chat_id=invoice_message.chat.id,
        )

        await state.clear()
        logger.info(
            'Создан платеж YooKassa СБП для пользователя ₽, ID',
            telegram_id=db_user.telegram_id,
            value=amount_kopeks // 100,
            payment_result=payment_result['yookassa_payment_id'],
        )

    except Exception as e:
        logger.error('Ошибка создания YooKassa СБП платежа', error=e)
        await _send_create_failed(message, texts, amount_kopeks)
        await state.clear()


@error_handler
async def check_yookassa_payment_status(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    """One phrase per status: the alert only answers whether the money has arrived."""
    texts = get_texts(db_user.language)
    try:
        local_payment_id = int(callback.data.split('_')[-1])

        from app.database.crud.yookassa import get_yookassa_payment_by_local_id

        payment = await get_yookassa_payment_by_local_id(db, local_payment_id)

        if not payment:
            await callback.answer(
                texts.t('PAYMENT_STATUS_NOT_FOUND', 'Платёж не найден. Создайте новый платёж.'), show_alert=True
            )
            return

        amount = texts.format_price(payment.amount_kopeks)
        metadata = payment.metadata_json if isinstance(payment.metadata_json, dict) else {}
        is_topup = str(metadata.get('purpose', '')).startswith('balance_topup')

        if payment.is_succeeded and (payment.transaction_id or not is_topup):
            if is_topup:
                text = texts.t('PAYMENT_STATUS_ON_BALANCE', '{amount} уже на балансе.')
            else:
                text = texts.t('PAYMENT_STATUS_PAID', 'Оплата {amount} прошла.')
        elif payment.status in ('succeeded', 'waiting_for_capture'):
            # Paid, but the webhook has not credited the balance yet.
            text = texts.t('PAYMENT_STATUS_PROCESSING', 'Оплата прошла, деньги появятся на балансе через минуту.')
        elif payment.is_failed:
            text = texts.t('PAYMENT_STATUS_CANCELED', 'Платёж отменён, деньги не списаны. Создайте новый платёж.')
        else:
            text = texts.t('PAYMENT_STATUS_PENDING', 'Оплата ещё не пришла. Если вы уже заплатили, подождите минуту.')

        await callback.answer(text.format(amount=amount), show_alert=True)

    except Exception as e:
        logger.error('Ошибка проверки статуса платежа', error=e)
        await callback.answer(
            texts.t('PAYMENT_STATUS_CHECK_FAILED', '❌ Не удалось проверить оплату. Попробуйте ещё раз через минуту.'),
            show_alert=True,
        )
