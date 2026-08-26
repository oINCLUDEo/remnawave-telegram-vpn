"""Mobile tariff catalog endpoint.

GET /mobile/v1/tariffs — returns all tariffs available to the user with
their periods, prices (with promo-group discounts applied), traffic and
device limits, and optional description text.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.cabinet.dependencies import get_cabinet_db, get_current_cabinet_user
from app.database.crud.tariff import get_tariffs_for_user
from app.database.models import User
from app.utils.pricing_utils import format_period_description


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    '/tariffs',
    summary='Каталог тарифов',
    description=(
        'Возвращает список тарифов, доступных пользователю, '
        'с периодами, ценами (с учётом скидок промогруппы) и описанием.'
    ),
    tags=['mobile'],
)
async def get_mobile_tariffs(
    user: User = Depends(get_current_cabinet_user),
    db: AsyncSession = Depends(get_cabinet_db),
) -> dict:
    """Return tariff catalog for the authenticated mobile user."""
    try:
        if user.status != 'active':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Учётная запись заблокирована',
            )

        # Resolve promo group for discount calculation and tariff filtering
        promo_group = (
            user.get_primary_promo_group()
            if hasattr(user, 'get_primary_promo_group')
            else None
        )
        if promo_group is None:
            promo_group = getattr(user, 'promo_group', None)
        promo_group_id = promo_group.id if promo_group else None

        tariffs = await get_tariffs_for_user(db, promo_group_id=promo_group_id)
        language = getattr(user, 'language', 'ru') or 'ru'

        logger.info(
            'Mobile /tariffs: resolved',
            user_id=user.id,
            promo_group_id=promo_group_id,
            tariffs_count=len(tariffs),
            tariff_ids=[t.id for t in tariffs],
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error('Mobile /tariffs DB error', user_id=user.id, error=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='Ошибка при получении тарифов',
        ) from exc

    # Build response outside the DB session
    from app.services.pricing_engine import pricing_engine

    result = []
    for tariff in tariffs:
        period_prices: dict = tariff.period_prices or {}
        periods = []

        for period_str, price_kopeks_raw in sorted(
            period_prices.items(), key=lambda kv: int(kv[0])
        ):
            try:
                period_days = int(period_str)
                base_kopeks = int(price_kopeks_raw)
            except (ValueError, TypeError):
                continue

            if period_days <= 0 or base_kopeks < 0:
                continue  # skip disabled periods

            months = max(1, period_days // 30)
            label = format_period_description(period_days, language)

            # Apply promo-group discount for this period
            final_kopeks = base_kopeks
            discount_pct = 0
            if promo_group and hasattr(promo_group, 'get_discount_percent'):
                discount_pct = promo_group.get_discount_percent('period', period_days)
                if discount_pct > 0:
                    final_kopeks = pricing_engine.apply_discount(base_kopeks, discount_pct)

            period_data: dict = {
                'id': f'days:{period_days}',
                'days': period_days,
                'months': months,
                'label': label,
                'price_kopeks': final_kopeks,
            }
            if discount_pct > 0 and final_kopeks != base_kopeks:
                period_data['original_price_kopeks'] = base_kopeks
                period_data['discount_percent'] = discount_pct

            periods.append(period_data)

        if not periods:
            logger.debug(
                'Mobile /tariffs: tariff skipped (no valid periods)',
                tariff_id=tariff.id, tariff_name=tariff.name,
                period_prices=tariff.period_prices,
            )
            continue  # skip tariffs with no configured periods

        device_price_kop = getattr(tariff, 'device_price_kopeks', None)
        # Apply promo-group discount to device price as well
        if device_price_kop and promo_group and hasattr(promo_group, 'get_discount_percent'):
            dev_disc = promo_group.get_discount_percent('device', 0)
            if dev_disc > 0:
                device_price_kop = pricing_engine.apply_discount(device_price_kop, dev_disc)

        result.append({
            'id': tariff.id,
            'name': tariff.name,
            'description': getattr(tariff, 'description', None),
            'traffic_limit_gb': tariff.traffic_limit_gb or 0,
            'device_limit': tariff.device_limit or 1,
            'tier_level': getattr(tariff, 'tier_level', 1) or 1,
            'device_price_kopeks': device_price_kop,
            'periods': periods,
        })

    logger.info(
        'Mobile /tariffs: response built',
        user_id=user.id,
        result_count=len(result),
    )
    return {'tariffs': result}
