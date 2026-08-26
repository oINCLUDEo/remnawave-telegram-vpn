"""
InfrastructureServer model — tracks VPN servers with payment schedules.

billing_type:
  'fixed'  — fixed monthly fee; billing_day = day of month, monthly_cost_rub = price
  'hourly' — dynamic usage-based billing; estimated_hourly_rate_rub for forecasting;
             actual cost entered manually each period via /add_expense or server panel
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, Integer, Numeric, String, Text

from app.database.models import AwareDateTime, Base
from sqlalchemy.sql import func


class InfrastructureServer(Base):
    __tablename__ = "infrastructure_servers"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)             # "Aeza Amsterdam #1"
    provider = Column(String(50), nullable=True)           # "Aeza", "Hetzner", "Selectel"
    location = Column(String(100), nullable=True)          # "Amsterdam, NL"

    billing_type = Column(String(20), nullable=False, default="fixed")
    # fixed billing
    monthly_cost_rub = Column(Numeric(10, 2), nullable=True)
    billing_day = Column(Integer, nullable=True)           # 1–28; day of month payment is due
    next_payment_date = Column(Date, nullable=True)        # computed & updated on each sync
    # hourly / dynamic billing
    estimated_hourly_rate_rub = Column(Numeric(10, 4), nullable=True)

    remind_days_before = Column(Integer, nullable=False, default=3)
    is_active = Column(Boolean, nullable=False, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())
    updated_at = Column(AwareDateTime(), default=func.now(), onupdate=func.now())
