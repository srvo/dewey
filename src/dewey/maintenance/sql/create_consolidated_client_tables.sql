-- Consolidated client profile table that merges data from all onboarding sources

-- Main consolidated client profile table
CREATE TABLE IF NOT EXISTS client_profiles (
    id INTEGER PRIMARY KEY,
    email VARCHAR,
    name VARCHAR,
    pronouns VARCHAR,
    -- Contact information
    phone VARCHAR,
    address_street VARCHAR,
    address_apt VARCHAR,
    address_city VARCHAR,
    address_state VARCHAR,
    address_zip VARCHAR,
    address_country VARCHAR,
    -- Professional information
    occupation VARCHAR,
    employer VARCHAR,
    job_title VARCHAR,
    annual_income VARCHAR,
    -- Personal information
    birthday DATE,
    marital_status VARCHAR,
    -- Investment profile
    net_worth VARCHAR,
    emergency_fund_available BOOLEAN,
    investment_experience VARCHAR,
    investment_goals VARCHAR,
    risk_tolerance VARCHAR,
    preferred_investment_amount VARCHAR,
    preferred_account_types VARCHAR,
    long_term_horizon VARCHAR,
    market_decline_reaction VARCHAR,
    portfolio_check_frequency VARCHAR,
    -- Personal interests and values
    interests VARCHAR,
    activist_activities VARCHAR,
    ethical_considerations TEXT,
    -- Referral information
    referral_source VARCHAR,
    referrer_name VARCHAR,
    -- Engagement tracking
    newsletter_opt_in BOOLEAN,
    contact_preference VARCHAR,
    -- Additional information
    work_situation TEXT,
    additional_notes TEXT,
    review_existing_accounts BOOLEAN,
    -- Data source tracking
    primary_data_source VARCHAR, -- Which form/source provided the majority of the data
    intake_timestamp TIMESTAMP,  -- When the client first submitted information
    -- Links to related tables
    household_id INTEGER,        -- Link to households table
    -- Standard timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store all the raw form submissions for reference/debugging
CREATE TABLE IF NOT EXISTS client_data_sources (
    id INTEGER PRIMARY KEY,
    client_profile_id INTEGER,
    source_type VARCHAR,           -- 'intake_questionnaire', 'onboarding_response', 'forminator', 'legitimate_onboarding'
    source_id VARCHAR,             -- Original ID from the source system
    submission_time TIMESTAMP,
    raw_data TEXT,                 -- JSON blob of the original data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_profile_id) REFERENCES client_profiles(id)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_client_profiles_email ON client_profiles(email);
CREATE INDEX IF NOT EXISTS idx_client_profiles_name ON client_profiles(name);
CREATE INDEX IF NOT EXISTS idx_client_profiles_household ON client_profiles(household_id);
CREATE INDEX IF NOT EXISTS idx_client_data_sources_profile ON client_data_sources(client_profile_id);
CREATE INDEX IF NOT EXISTS idx_client_data_sources_type ON client_data_sources(source_type);

-- Add comments
COMMENT ON TABLE client_profiles IS 'Consolidated table containing all client information merged from various onboarding sources';
COMMENT ON TABLE client_data_sources IS 'Reference table tracking the original data sources that populated the client profiles';
