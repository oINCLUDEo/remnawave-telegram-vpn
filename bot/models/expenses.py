"""
ManualExpense model — tracks infrastructure, marketing, and other cash expenses
that are not recorded in the transactions table.

Run bot/models/create_expenses_table.sql once to create the table.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Column, Date, Integer, Numeric, String, Text
from sqlalchemy.sql import func

from app.database.models import AwareDateTime, Base


class ManualExpense(Base):
    __tablename__ = "manual_expenses"

    id = Column(Integer, primary_key=True)

    # Amount in rubles (not kopeks — entered manually by admin)
    amount_rub = Column(Numeric(10, 2), nullable=False)

    # Category: 'infrastructure' | 'marketing_ads' | 'other'
    category = Column(String(50), nullable=False)

    # Human-readable label: e.g. "Aeza Amsterdam", "Selectel S3", "Telegram посев"
    subcategory = Column(String(100), nullable=True)

    expense_date = Column(Date, nullable=False, default=date.today)
    comment = Column(Text, nullable=True)
    created_at = Column(AwareDateTime(), default=func.now())

    CATEGORY_LABELS = {
        "infrastructure": "🖥 Инфраструктура",
        "marketing_ads": "📢 Реклама",
        "other": "📦 Прочее",
    }

    @property
    def category_label(self) -> str:
        return self.CATEGORY_LABELS.get(self.category, self.category)
