-- Client-related tables schema for DuckDB

-- 1. Households table
CREATE TABLE IF NOT EXISTS households (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    num_accounts INTEGER,
    account_groups VARCHAR,
    cash_percentage DOUBLE,
    balance DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Holdings table
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY,
    ticker VARCHAR,
    description VARCHAR,
    aum_percentage DOUBLE,
    price DOUBLE,
    quantity DOUBLE,
    value DOUBLE,
    as_of_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Contributions table
CREATE TABLE IF NOT EXISTS contributions (
    id INTEGER PRIMARY KEY,
    account VARCHAR,
    household VARCHAR,
    maximum_contribution DOUBLE,
    ytd_contributions DOUBLE,
    projected DOUBLE,
    year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Open Accounts table
CREATE TABLE IF NOT EXISTS open_accounts (
    id INTEGER PRIMARY KEY,
    name VARCHAR,
    household VARCHAR,
    qualified_rep_code VARCHAR,
    account_group VARCHAR,
    portfolio VARCHAR,
    tax_iq VARCHAR,
    fee_schedule VARCHAR,
    custodian VARCHAR,
    balance DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on key fields
CREATE INDEX IF NOT EXISTS idx_households_name ON households(name);

CREATE INDEX IF NOT EXISTS idx_holdings_ticker ON holdings(ticker);
CREATE INDEX IF NOT EXISTS idx_holdings_as_of_date ON holdings(as_of_date);

CREATE INDEX IF NOT EXISTS idx_contributions_account ON contributions(account);
CREATE INDEX IF NOT EXISTS idx_contributions_household ON contributions(household);

CREATE INDEX IF NOT EXISTS idx_open_accounts_name ON open_accounts(name);
CREATE INDEX IF NOT EXISTS idx_open_accounts_household ON open_accounts(household);

-- Add comments
COMMENT ON TABLE households IS 'Table containing household data from client portfolio management';
COMMENT ON TABLE holdings IS 'Table containing all holdings across client portfolios';
COMMENT ON TABLE contributions IS 'Table tracking contributions to client accounts';
COMMENT ON TABLE open_accounts IS 'Table containing all open client accounts and their details'; 