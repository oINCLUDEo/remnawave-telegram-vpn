"""
Daily server payment reminder service.

Runs every day at 09:00 Moscow time.
Sends a Telegram notification to ADMIN_NOTIFICATIONS_CHAT_ID for servers
due within `server.remind_days_before` days.

Hourly servers are listed as a separate section — actual costs must be
entered manually via 💸 Добавить расход after each billing period.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from aiogram import Bot
from sqlalchemy import select

from app.config import settings
from app.database.database import AsyncSessionLocal
from bot.models.servers import InfrastructureServer


logger = structlog.get_logger(__name__)

_MOSCOW_TZ = ZoneInfo("Europe/Moscow")
_REMIND_HOUR = 9
_REMIND_MINUTE = 0


class ServerReminderService:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self.bot: Bot | None = None

    def set_bot(self, bot: Bot) -> None:
        self.bot = bot

    def is_running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        await self.stop()
        if not self.bot:
            logger.warning("Server reminder: bot instance not set, skipping")
            return
        self._task = asyncio.create_task(self._daily_loop())
        logger.info("🖥 Сервис напоминаний о серверах запущен: ежедневно в %02d:%02d МСК",
                    _REMIND_HOUR, _REMIND_MINUTE)

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None

    def _next_run_utc(self) -> datetime:
        now_msk = datetime.now(_MOSCOW_TZ)
        target = now_msk.replace(hour=_REMIND_HOUR, minute=_REMIND_MINUTE, second=0, microsecond=0)
        if now_msk >= target:
            target += timedelta(days=1)
        return target.astimezone(UTC)

    async def _daily_loop(self) -> None:
        try:
            while True:
                delay = (self._next_run_utc() - datetime.now(UTC)).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)
                try:
                    await self._check_and_notify()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.error("Ошибка проверки напоминаний серверов", exc_info=exc)
        except asyncio.CancelledError:
            logger.info("Сервис напоминаний серверов остановлен")
            raise

    async def _check_and_notify(self) -> None:
        chat_id = settings.ADMIN_NOTIFICATIONS_CHAT_ID
        if not chat_id:
            return

        today = date.today()

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(InfrastructureServer).where(
                    InfrastructureServer.is_active.is_(True)
                )
            )
            servers = list(result.scalars().all())

        # Fixed billing — check upcoming payments
        due_soon: list[tuple[int, InfrastructureServer]] = []
        for s in servers:
            if s.billing_type != "fixed" or s.next_payment_date is None:
                continue
            days_left = (s.next_payment_date - today).days
            if 0 <= days_left <= s.remind_days_before:
                due_soon.append((days_left, s))

        if not due_soon and not any(s.billing_type == "hourly" for s in servers):
            return

        lines = ["🖥 <b>Напоминание об оплате серверов</b>\n"]

        if due_soon:
            due_soon.sort(key=lambda x: x[0])
            for days_left, s in due_soon:
                if days_left == 0:
                    when = "сегодня‼️"
                elif days_left == 1:
                    when = "завтра❗"
                else:
                    when = f"через {days_left} дн."
                lines.append(
                    f"⚠️ <b>{s.name}</b> — {s.monthly_cost_rub} ₽ ({when})\n"
                    f"   {s.provider or ''} {s.location or ''}"
                )

        # Hourly servers — informational
        hourly = [s for s in servers if s.billing_type == "hourly"]
        if hourly:
            lines.append("\n⏱ <b>Почасовые серверы (введи расход вручную):</b>")
            for s in hourly:
                rate = f"≈ {s.estimated_hourly_rate_rub} ₽/ч" if s.estimated_hourly_rate_rub else "ставка не задана"
                lines.append(f"• {s.name} — {rate}")

        if len(lines) <= 1:
            return

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text="\n".join(lines),
                parse_mode="HTML",
            )
            logger.info("Напоминание о серверах отправлено", due_count=len(due_soon))
        except Exception as exc:
            logger.error("Не удалось отправить напоминание о серверах", exc_info=exc)

    async def send_now(self) -> None:
        """Force-check and notify immediately (for testing or /sync_sheets trigger)."""
        await self._check_and_notify()


server_reminder_service = ServerReminderService()
