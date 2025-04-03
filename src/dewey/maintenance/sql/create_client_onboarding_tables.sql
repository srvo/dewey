-- Client onboarding and intake data tables schema for DuckDB

-- 1. Client Intake Questionnaire table
CREATE TABLE IF NOT EXISTS client_intake_questionnaire (
    id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP,
    email VARCHAR,
    name VARCHAR,
    pronouns VARCHAR,
    address VARCHAR,
    phone VARCHAR,
    occupation VARCHAR,
    occupation_duration VARCHAR,
    life_changes_planned BOOLEAN,
    investment_amount VARCHAR,
    account_types VARCHAR,
    risk_tolerance VARCHAR,
    net_worth VARCHAR,
    annual_income VARCHAR,
    emergency_fund_available BOOLEAN,
    investment_goals VARCHAR,
    primary_objective VARCHAR,
    portfolio_check_frequency VARCHAR,
    long_term_horizon VARCHAR,
    market_drop_action VARCHAR,
    interests VARCHAR,
    activist_activities VARCHAR,
    ethical_considerations VARCHAR,
    referral_source VARCHAR,
    linked_household_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Onboarding Responses table for email communications
CREATE TABLE IF NOT EXISTS onboarding_responses (
    id INTEGER PRIMARY KEY,
    date TIMESTAMP,
    email VARCHAR,
    name VARCHAR,
    subject VARCHAR,
    message TEXT,
    form_type VARCHAR,
    linked_household_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Forminator Onboarding Form table for detailed client information
CREATE TABLE IF NOT EXISTS forminator_onboarding (
    id INTEGER PRIMARY KEY,
    submission_time TIMESTAMP,
    user_id VARCHAR,
    user_ip VARCHAR,
    user_email VARCHAR,
    name VARCHAR,
    pronouns VARCHAR,
    address_street VARCHAR,
    address_apt VARCHAR,
    address_city VARCHAR,
    address_state VARCHAR,
    address_zip VARCHAR,
    address_country VARCHAR,
    birthday DATE,
    phone VARCHAR,
    employer VARCHAR,
    job_position VARCHAR,
    marital_status VARCHAR,
    work_situation TEXT,
    newsletter_opt_in BOOLEAN,
    website_socials VARCHAR,
    contact_preference VARCHAR,
    investment_experience VARCHAR,
    investment_familiarity VARCHAR,
    emergency_fund_available BOOLEAN,
    worked_with_advisor BOOLEAN,
    other_accounts BOOLEAN,
    referral_source VARCHAR,
    referrer_name VARCHAR,
    account_types VARCHAR,
    risk_profile VARCHAR,
    additional_info TEXT,
    review_existing_accounts BOOLEAN,
    linked_household_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Legitimate Onboarding Form Responses table
CREATE TABLE IF NOT EXISTS legitimate_onboarding (
    id INTEGER PRIMARY KEY,
    date TIMESTAMP,
    name VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    company VARCHAR,
    message TEXT,
    key_points TEXT,
    wants_newsletter BOOLEAN,
    linked_household_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on key fields
CREATE INDEX IF NOT EXISTS idx_questionnaire_email ON client_intake_questionnaire(email);
CREATE INDEX IF NOT EXISTS idx_questionnaire_name ON client_intake_questionnaire(name);
CREATE INDEX IF NOT EXISTS idx_questionnaire_household ON client_intake_questionnaire(linked_household_id);

CREATE INDEX IF NOT EXISTS idx_onboarding_resp_email ON onboarding_responses(email);
CREATE INDEX IF NOT EXISTS idx_onboarding_resp_name ON onboarding_responses(name);
CREATE INDEX IF NOT EXISTS idx_onboarding_resp_household ON onboarding_responses(linked_household_id);

CREATE INDEX IF NOT EXISTS idx_forminator_email ON forminator_onboarding(user_email);
CREATE INDEX IF NOT EXISTS idx_forminator_name ON forminator_onboarding(name);
CREATE INDEX IF NOT EXISTS idx_forminator_household ON forminator_onboarding(linked_household_id);

CREATE INDEX IF NOT EXISTS idx_legitimate_email ON legitimate_onboarding(email);
CREATE INDEX IF NOT EXISTS idx_legitimate_name ON legitimate_onboarding(name);
CREATE INDEX IF NOT EXISTS idx_legitimate_household ON legitimate_onboarding(linked_household_id);

-- Add comments
COMMENT ON TABLE client_intake_questionnaire IS 'Table containing client intake questionnaire responses with personal and investment data';
COMMENT ON TABLE onboarding_responses IS 'Table containing email communications with clients during onboarding process';
COMMENT ON TABLE forminator_onboarding IS 'Table containing detailed client information from web form submissions';
COMMENT ON TABLE legitimate_onboarding IS 'Table containing verified onboarding form responses from potential clients';
