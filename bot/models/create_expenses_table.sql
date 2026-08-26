-- Run this once on the production database to create the manual expenses table.
-- Safe to run multiple times (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS manual_expenses (
    id          SERIAL PRIMARY KEY,
    amount_rub  NUMERIC(10, 2)  NOT NULL,
    category    VARCHAR(50)     NOT NULL,
    -- categories: 'infrastructure' | 'marketing_ads' | 'other'
    subcategory VARCHAR(100),
    expense_date DATE           NOT NULL DEFAULT CURRENT_DATE,
    comment     TEXT,
    created_at  TIMESTAMPTZ     DEFAULT NOW()
);

-- Index for monthly queries used by the sync
CREATE INDEX IF NOT EXISTS ix_manual_expenses_date
    ON manual_expenses (expense_date);
