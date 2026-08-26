-- Run once on production DB. Safe to re-run (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS infrastructure_servers (
    id                        SERIAL PRIMARY KEY,
    name                      VARCHAR(100)   NOT NULL,
    provider                  VARCHAR(50),
    location                  VARCHAR(100),
    billing_type              VARCHAR(20)    NOT NULL DEFAULT 'fixed',
    -- fixed billing
    monthly_cost_rub          NUMERIC(10,2),
    billing_day               INTEGER,
    next_payment_date         DATE,
    -- hourly / dynamic billing
    estimated_hourly_rate_rub NUMERIC(10,4),
    -- settings
    remind_days_before        INTEGER        NOT NULL DEFAULT 3,
    is_active                 BOOLEAN        NOT NULL DEFAULT true,
    notes                     TEXT,
    created_at                TIMESTAMPTZ    DEFAULT NOW(),
    updated_at                TIMESTAMPTZ    DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_infra_servers_next_payment
    ON infrastructure_servers (next_payment_date)
    WHERE is_active = true;
