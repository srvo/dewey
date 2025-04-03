import sqlalchemy as sa
from sqlalchemy import Column
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class CleanClientProfiles(Base):
    __tablename__ = "clean_client_profiles"

    id = Column(sa.Integer)
    name = Column(sa.String)
    email = Column(sa.String)
    household_id = Column(sa.Integer)
    primary_data_source = Column(sa.String)
    created_at = Column(sa.DateTime)
    updated_at = Column(sa.DateTime)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class ClientCommunicationsIndex(Base):
    __tablename__ = "client_communications_index"

    thread_id = Column(sa.String)
    client_email = Column(sa.String)
    subject = Column(sa.String)
    client_message = Column(sa.String)
    client_msg_id = Column(sa.String)
    response_msg_id = Column(sa.String)
    response_message = Column(sa.String)
    actual_received_time = Column(sa.DateTime)
    actual_response_time = Column(sa.DateTime)
    # SQLAlchemy workaround: Adding virtual primary key
    id = Column(sa.Integer, primary_key=True)
    __mapper_args__ = {"primary_key": ["id"]}
    # Note: This column doesn't exist in the database


class ClientDataSources(Base):
    __tablename__ = "client_data_sources"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    client_profile_id = Column(sa.Integer)
    source_type = Column(sa.String)
    source_id = Column(sa.String)
    submission_time = Column(sa.DateTime)
    raw_data = Column(sa.String)
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class ClientProfiles(Base):
    __tablename__ = "client_profiles"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    email = Column(sa.String)
    name = Column(sa.String)
    pronouns = Column(sa.String)
    phone = Column(sa.String)
    address_street = Column(sa.String)
    address_apt = Column(sa.String)
    address_city = Column(sa.String)
    address_state = Column(sa.String)
    address_zip = Column(sa.String)
    address_country = Column(sa.String)
    occupation = Column(sa.String)
    employer = Column(sa.String)
    job_title = Column(sa.String)
    annual_income = Column(sa.String)
    birthday = Column(sa.Date)
    marital_status = Column(sa.String)
    net_worth = Column(sa.String)
    emergency_fund_available = Column(sa.Boolean)
    investment_experience = Column(sa.String)
    investment_goals = Column(sa.String)
    risk_tolerance = Column(sa.String)
    preferred_investment_amount = Column(sa.String)
    preferred_account_types = Column(sa.String)
    long_term_horizon = Column(sa.String)
    market_decline_reaction = Column(sa.String)
    portfolio_check_frequency = Column(sa.String)
    interests = Column(sa.String)
    activist_activities = Column(sa.String)
    ethical_considerations = Column(sa.String)
    referral_source = Column(sa.String)
    referrer_name = Column(sa.String)
    newsletter_opt_in = Column(sa.Boolean)
    contact_preference = Column(sa.String)
    work_situation = Column(sa.String)
    additional_notes = Column(sa.String)
    review_existing_accounts = Column(sa.Boolean)
    primary_data_source = Column(sa.String)
    intake_timestamp = Column(sa.DateTime)
    household_id = Column(sa.Integer)
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class Contacts(Base):
    __tablename__ = "contacts"

    email = Column(sa.String)
    first_name = Column(sa.String)
    last_name = Column(sa.String)
    full_name = Column(sa.String)
    company = Column(sa.String)
    job_title = Column(sa.String)
    phone = Column(sa.String)
    country = Column(sa.String)
    source = Column(sa.String)
    domain = Column(sa.String)
    last_interaction_date = Column(sa.DateTime)
    first_seen_date = Column(sa.DateTime)
    last_updated = Column(sa.DateTime)
    tags = Column(sa.String)
    notes = Column(sa.String)
    metadata_col = Column(sa.String)
    event_id = Column(sa.String)
    event_summary = Column(sa.String)
    event_time = Column(sa.DateTime)
    website = Column(sa.Integer)
    address_1 = Column(sa.String)
    address_2 = Column(sa.Integer)
    city = Column(sa.String)
    state = Column(sa.String)
    zip = Column(sa.Integer)
    current_client = Column(sa.Integer)
    investment_professional = Column(sa.Integer)
    last_contact = Column(sa.Integer)
    email_verified = Column(sa.Integer)
    social_media = Column(sa.Integer)
    breached_sites = Column(sa.Integer)
    related_domains = Column(sa.Integer)
    password_leaks = Column(sa.Integer)
    pastebin_records = Column(sa.Integer)
    is_newsletter = Column(sa.Boolean)
    is_client = Column(sa.Boolean)
    is_free_money = Column(sa.Boolean)
    last_outreach = Column(sa.Integer)
    lead_source = Column(sa.Integer)
    birthdate = Column(sa.Integer)
    employment_status = Column(sa.Integer)
    is_partnered = Column(sa.Boolean)
    partner_name = Column(sa.Integer)
    investment_experience = Column(sa.BigInteger)
    social_instagram = Column(sa.Integer)
    social_linkedin = Column(sa.Integer)
    social_tiktok = Column(sa.Integer)
    subscriber_since = Column(sa.DateTime)
    email_opens = Column(sa.BigInteger)
    email_clicks = Column(sa.BigInteger)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class Contributions(Base):
    __tablename__ = "contributions"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    account = Column(sa.String)
    household = Column(sa.String)
    maximum_contribution = Column(sa.Float)
    ytd_contributions = Column(sa.Float)
    projected = Column(sa.Float)
    year = Column(sa.Integer)
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class DiversificationSheets(Base):
    __tablename__ = "diversification_sheets"

    symbol = Column(sa.String)
    name = Column(sa.String)
    allocation = Column(sa.String)
    current_weight = Column(sa.String)
    target_weight = Column(sa.String)
    drift = Column(sa.String)
    market_value = Column(sa.String)
    last_price = Column(sa.String)
    shares = Column(sa.String)
    yield_value = Column(sa.String)
    yield_contribution = Column(sa.String)
    sector = Column(sa.String)
    country = Column(sa.String)
    strategy = Column(sa.String)
    risk_score = Column(sa.String)
    correlation = Column(sa.String)
    beta = Column(sa.String)
    volatility = Column(sa.String)
    sharpe_ratio = Column(sa.String)
    notes = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class EmailAnalyses(Base):
    __tablename__ = "email_analyses"

    msg_id = Column(sa.String, primary_key=True, nullable=False)
    thread_id = Column(sa.String)
    subject = Column(sa.String)
    from_address = Column(sa.String)
    analysis_date = Column(sa.DateTime)
    raw_analysis = Column(sa.JSON)
    automation_score = Column(sa.Float)
    content_value = Column(sa.Float)
    human_interaction = Column(sa.Float)
    time_value = Column(sa.Float)
    business_impact = Column(sa.Float)
    uncertainty_score = Column(sa.Float)
    metadata_col = Column(sa.JSON)
    priority = Column(sa.Integer)
    label_ids = Column(sa.JSON)
    snippet = Column(sa.String)
    internal_date = Column(sa.BigInteger)
    size_estimate = Column(sa.Integer)
    message_parts = Column(sa.JSON)
    draft_id = Column(sa.String)
    draft_message = Column(sa.JSON)
    attachments = Column(sa.JSON)
    status = Column(sa.String, default="new")
    error_message = Column(sa.String)
    batch_id = Column(sa.String)
    import_timestamp = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class EmailFeedback(Base):
    __tablename__ = "email_feedback"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    msg_id = Column(sa.String)
    subject = Column(sa.String)
    original_priority = Column(sa.Integer)
    assigned_priority = Column(sa.Integer)
    suggested_priority = Column(sa.Integer)
    feedback_comments = Column(sa.String)
    add_to_topics = Column(sa.String)
    timestamp = Column(sa.DateTime)


class EmailPreferences(Base):
    __tablename__ = "email_preferences"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    override_rules = Column(sa.String)
    topic_weight = Column(sa.Float)
    sender_weight = Column(sa.Float)
    content_value_weight = Column(sa.Float)
    sender_history_weight = Column(sa.Float)
    priority_map = Column(sa.String)
    timestamp = Column(sa.DateTime)


class Emails(Base):
    __tablename__ = "emails"

    msg_id = Column(sa.String, primary_key=True, nullable=False)
    thread_id = Column(sa.String)
    subject = Column(sa.String)
    from_address = Column(sa.String)
    analysis_date = Column(sa.DateTime)
    raw_analysis = Column(sa.JSON)
    automation_score = Column(sa.Float)
    content_value = Column(sa.Float)
    human_interaction = Column(sa.Float)
    time_value = Column(sa.Float)
    business_impact = Column(sa.Float)
    uncertainty_score = Column(sa.Float)
    metadata_col = Column(sa.JSON)
    priority = Column(sa.Integer)
    label_ids = Column(sa.JSON)
    snippet = Column(sa.String)
    internal_date = Column(sa.BigInteger)
    size_estimate = Column(sa.Integer)
    message_parts = Column(sa.JSON)
    draft_id = Column(sa.String)
    draft_message = Column(sa.JSON)
    attachments = Column(sa.JSON)
    status = Column(sa.String, default="new")
    error_message = Column(sa.String)
    batch_id = Column(sa.String)
    import_timestamp = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class EntityAnalytics(Base):
    __tablename__ = "entity_analytics"

    id = Column(sa.Integer)
    category = Column(sa.String)
    term = Column(sa.String)
    count = Column(sa.Integer)
    timestamp = Column(sa.String)
    context = Column(sa.String)
    metadata_col = Column(sa.String)
    materiality_score = Column(sa.Float)
    confidence_score = Column(sa.Float)
    sentiment_score = Column(sa.Float)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class ExcludeSheets(Base):
    __tablename__ = "exclude_sheets"

    company = Column(sa.String)
    symbol = Column(sa.String)
    isin = Column(sa.String)
    category = Column(sa.String)
    criteria = Column(sa.String)
    concerned_groups = Column(sa.String)
    decision = Column(sa.String)
    date = Column(sa.String)
    notes = Column(sa.String)
    col_9 = Column(sa.String)
    col_10 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class FamilyOffices(Base):
    __tablename__ = "family_offices"

    office_id = Column(sa.String)
    firm_name = Column(sa.String)
    contact_first_name = Column(sa.String)
    contact_last_name = Column(sa.String)
    contact_title = Column(sa.String)
    phone_number = Column(sa.String)
    fax_number = Column(sa.String)
    email_address = Column(sa.String)
    company_email = Column(sa.String)
    street_address = Column(sa.String)
    city = Column(sa.String)
    state_province = Column(sa.String)
    postal_code = Column(sa.String)
    country = Column(sa.String)
    investment_areas = Column(sa.String)
    year_founded = Column(sa.String)
    aum_mil = Column(sa.String)
    client_average = Column(sa.String)
    client_minimum = Column(sa.String)
    additional_info = Column(sa.String)
    website = Column(sa.String)
    etc = Column(sa.String)
    mf_sf = Column(sa.String)
    v5_contact = Column(sa.String)
    created_at = Column(sa.DateTime)
    updated_at = Column(sa.DateTime)
    id = Column(sa.Integer)
    aum_numeric = Column(sa.Float)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class GrowthSheets(Base):
    __tablename__ = "growth_sheets"

    tick = Column(sa.String)
    symbol = Column(sa.String)
    si = Column(sa.String)
    name = Column(sa.String)
    target = Column(sa.String)
    current = Column(sa.String)
    position_chg = Column(sa.String)
    model_portfolio = Column(sa.String)
    last_close = Column(sa.String)
    si_sum = Column(sa.String)
    pct_change = Column(sa.String)
    yield_value = Column(sa.String)
    yield_contribution = Column(sa.String)
    sector = Column(sa.String)
    country = Column(sa.String)
    usa = Column(sa.String)
    asia = Column(sa.String)
    latam = Column(sa.String)
    europe = Column(sa.String)
    real_estate = Column(sa.String)
    infrastructure = Column(sa.String)
    innovation = Column(sa.String)
    lending = Column(sa.String)
    market_cap_3_11_2024 = Column(sa.String)
    real_estate_1 = Column(sa.String)
    infrastructure_1 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class Holdings(Base):
    __tablename__ = "holdings"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    ticker = Column(sa.String)
    description = Column(sa.String)
    aum_percentage = Column(sa.Float)
    price = Column(sa.Float)
    quantity = Column(sa.Float)
    value = Column(sa.Float)
    as_of_date = Column(sa.Date)
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class Households(Base):
    __tablename__ = "households"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    name = Column(sa.String)
    num_accounts = Column(sa.Integer)
    account_groups = Column(sa.String)
    cash_percentage = Column(sa.Float)
    balance = Column(sa.Float)
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class IncomeSheets(Base):
    __tablename__ = "income_sheets"

    tick = Column(sa.String)
    symbol = Column(sa.String)
    name = Column(sa.String)
    target = Column(sa.String)
    current = Column(sa.String)
    model_portfolio = Column(sa.String)
    drift = Column(sa.String)
    last_close = Column(sa.String)
    yield_value = Column(sa.String)
    yield_cont = Column(sa.String)
    social_impact = Column(sa.String)
    sustainable_infrastructure = Column(sa.String)
    energy_infrastructure = Column(sa.String)
    private_companies = Column(sa.String)
    public_companies = Column(sa.String)
    social_impact_1 = Column(sa.String)
    infrastructure = Column(sa.String)
    private_companies_1 = Column(sa.String)
    public_companies_1 = Column(sa.String)
    legacy_exposure = Column(sa.String)
    duration = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class MarkdownSections(Base):
    __tablename__ = "markdown_sections"

    id = Column(sa.Integer)
    title = Column(sa.String)
    content = Column(sa.String)
    section_type = Column(sa.String)
    source_file = Column(sa.String)
    created_at = Column(sa.DateTime)
    word_count = Column(sa.Integer)
    sentiment = Column(sa.String)
    has_pii = Column(sa.Boolean)
    readability = Column(sa.String)
    avg_sentence_length = Column(sa.Float)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class MasterClients(Base):
    __tablename__ = "master_clients"

    client_id = Column(sa.Integer)
    name = Column(sa.String)
    email = Column(sa.String)
    phone = Column(sa.String)
    pronouns = Column(sa.String)
    full_address = Column(sa.String)
    occupation = Column(sa.String)
    employer = Column(sa.String)
    job_title = Column(sa.String)
    annual_income = Column(sa.String)
    birthday = Column(sa.Date)
    marital_status = Column(sa.String)
    net_worth = Column(sa.String)
    investment_experience = Column(sa.String)
    investment_goals = Column(sa.String)
    risk_tolerance = Column(sa.String)
    preferred_investment_amount = Column(sa.String)
    preferred_account_types = Column(sa.String)
    interests = Column(sa.String)
    ethical_considerations = Column(sa.String)
    contact_preference = Column(sa.String)
    primary_data_source = Column(sa.String)
    intake_timestamp = Column(sa.DateTime)
    household_id = Column(sa.String)
    company = Column(sa.String)
    contact_last_interaction = Column(sa.DateTime)
    contact_tags = Column(sa.String)
    contact_notes = Column(sa.String)
    newsletter_subscriber = Column(sa.Boolean)
    email_opens = Column(sa.BigInteger)
    email_clicks = Column(sa.BigInteger)
    last_email_date = Column(sa.DateTime)
    recent_email_subjects = Column(sa.String)
    account_groups = Column(sa.String)
    portfolios = Column(sa.String)
    total_balance = Column(sa.Float)
    num_accounts = Column(sa.BigInteger)
    created_at = Column(sa.DateTime)
    updated_at = Column(sa.DateTime)
    # SQLAlchemy workaround: Adding virtual primary key
    id = Column(sa.Integer, primary_key=True)
    __mapper_args__ = {"primary_key": ["id"]}
    # Note: This column doesn't exist in the database


class ObserveSheets(Base):
    __tablename__ = "observe_sheets"

    col_0 = Column(sa.String)
    col_1 = Column(sa.String)
    col_2 = Column(sa.String)
    col_3 = Column(sa.String)
    col_4 = Column(sa.String)
    col_5 = Column(sa.String)
    col_6 = Column(sa.String)
    col_7 = Column(sa.String)
    col_8 = Column(sa.String)
    col_9 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class OpenAccounts(Base):
    __tablename__ = "open_accounts"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    name = Column(sa.String)
    household = Column(sa.String)
    qualified_rep_code = Column(sa.String)
    account_group = Column(sa.String)
    portfolio = Column(sa.String)
    tax_iq = Column(sa.String)
    fee_schedule = Column(sa.String)
    custodian = Column(sa.String)
    balance = Column(sa.Float)
    created_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")
    updated_at = Column(sa.DateTime, default="CURRENT_TIMESTAMP")


class OverviewTablesSheets(Base):
    __tablename__ = "overview_tables_sheets"

    col_0 = Column(sa.String)
    col_1 = Column(sa.String)
    col_2 = Column(sa.String)
    col_3 = Column(sa.String)
    col_4 = Column(sa.String)
    col_5 = Column(sa.String)
    col_6 = Column(sa.String)
    col_7 = Column(sa.String)
    col_8 = Column(sa.String)
    col_9 = Column(sa.String)
    col_10 = Column(sa.String)
    col_11 = Column(sa.String)
    col_12 = Column(sa.String)
    col_13 = Column(sa.String)
    col_14 = Column(sa.String)
    col_15 = Column(sa.String)
    col_16 = Column(sa.String)
    col_17 = Column(sa.String)
    col_18 = Column(sa.String)
    col_19 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class PodcastEpisodes(Base):
    __tablename__ = "podcast_episodes"

    title = Column(sa.String)
    link = Column(sa.String)
    published = Column(sa.DateTime)
    description = Column(sa.String)
    audio_url = Column(sa.String)
    audio_type = Column(sa.String)
    audio_length = Column(sa.BigInteger)
    duration_minutes = Column(sa.Float)
    transcript = Column(sa.String)
    created_at = Column(sa.DateTime)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class PortfolioScreenerSheets(Base):
    __tablename__ = "portfolio_screener_sheets"

    col_0 = Column(sa.String)
    col_1 = Column(sa.String)
    col_2 = Column(sa.String)
    col_3 = Column(sa.String)
    col_4 = Column(sa.String)
    col_5 = Column(sa.String)
    col_6 = Column(sa.String)
    col_7 = Column(sa.String)
    col_8 = Column(sa.String)
    col_9 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class PreferredsSheets(Base):
    __tablename__ = "preferreds_sheets"

    symbol_cusip = Column(sa.String)
    symbol = Column(sa.String)
    tick = Column(sa.String)
    note = Column(sa.String)
    C4 = Column(sa.String)
    security_description = Column(sa.String)
    ipo_date = Column(sa.String)
    cpn_rate_ann_amt = Column(sa.String)
    liqpref_callprice = Column(sa.String)
    call_date_matur_date = Column(sa.String)
    moodys_s_p_dated = Column(sa.String)
    fifteen_pct_tax_rate = Column(sa.String)
    conv = Column(sa.String)
    ipo_prospectus = Column(sa.String)
    distribution_dates = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class ResearchAnalyses(Base):
    __tablename__ = "research_analyses"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    company = Column(sa.String)
    timestamp = Column(sa.DateTime)
    content = Column(sa.String)
    summary = Column(sa.String)
    ethical_score = Column(sa.Float)
    risk_level = Column(sa.String)


class ResearchIterations(Base):
    __tablename__ = "research_iterations"

    id = Column(sa.BigInteger)
    company_ticker = Column(sa.String)
    iteration_type = Column(sa.String)
    source_count = Column(sa.Integer)
    date_range = Column(sa.Integer)
    previous_iteration_id = Column(sa.Integer)
    summary = Column(sa.String)
    key_changes = Column(sa.Integer)
    risk_factors = Column(sa.String)
    opportunities = Column(sa.Integer)
    confidence_metrics = Column(sa.String)
    status = Column(sa.String)
    reviewer_notes = Column(sa.String)
    reviewed_by = Column(sa.Integer)
    reviewed_at = Column(sa.DateTime)
    prompt_template = Column(sa.Integer)
    model_version = Column(sa.Integer)
    created_at = Column(sa.DateTime)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.BigInteger, primary_key=True)


class ResearchResults(Base):
    __tablename__ = "research_results"

    id = Column(sa.BigInteger)
    company_ticker = Column(sa.String)
    summary = Column(sa.String)
    risk_score = Column(sa.Integer)
    confidence_score = Column(sa.Integer)
    recommendation = Column(sa.String)
    structured_data = Column(sa.String)
    raw_results = Column(sa.String)
    search_queries = Column(sa.String)
    source_date_range = Column(sa.Integer)
    total_sources = Column(sa.Integer)
    source_categories = Column(sa.String)
    last_iteration_id = Column(sa.Integer)
    first_analyzed_at = Column(sa.DateTime)
    last_updated_at = Column(sa.DateTime)
    meta_info = Column(sa.String)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.BigInteger, primary_key=True)


class ResearchSearchResults(Base):
    __tablename__ = "research_search_results"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    search_id = Column(sa.Integer)
    timestamp = Column(sa.DateTime)
    title = Column(sa.String)
    link = Column(sa.String)
    snippet = Column(sa.String)
    source = Column(sa.String)


class ResearchSearches(Base):
    __tablename__ = "research_searches"

    id = Column(sa.Integer, primary_key=True, nullable=False)
    timestamp = Column(sa.DateTime)
    query_col = Column(sa.String)
    num_results = Column(sa.Integer)


class ResearchSources(Base):
    __tablename__ = "research_sources"

    id = Column(sa.BigInteger)
    ticker = Column(sa.String)
    url = Column(sa.String)
    title = Column(sa.String)
    snippet = Column(sa.String)
    source_type = Column(sa.String)
    category = Column(sa.String)
    created_at = Column(sa.DateTime)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.BigInteger, primary_key=True)


class RiskBasedPortfoliosSheets(Base):
    __tablename__ = "risk_based_portfolios_sheets"

    col_0 = Column(sa.String)
    col_1 = Column(sa.String)
    col_2 = Column(sa.String)
    col_3 = Column(sa.String)
    col_4 = Column(sa.String)
    col_5 = Column(sa.String)
    col_6 = Column(sa.String)
    col_7 = Column(sa.String)
    col_8 = Column(sa.String)
    col_9 = Column(sa.String)
    col_10 = Column(sa.String)
    col_11 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class TickHistorySheets(Base):
    __tablename__ = "tick_history_sheets"

    ticker = Column(sa.String)
    old_tick = Column(sa.String)
    new_tick = Column(sa.String)
    date = Column(sa.String)
    isin = Column(sa.String)
    month = Column(sa.String)
    year = Column(sa.String)
    monthyear = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class UniverseSheets(Base):
    __tablename__ = "universe_sheets"

    excluded = Column(sa.String)
    workflow = Column(sa.String)
    ticker = Column(sa.String)
    isin = Column(sa.String)
    tick = Column(sa.String)
    security_name = Column(sa.String)
    note = Column(sa.String)
    last_tick_date = Column(sa.String)
    category = Column(sa.String)
    sector = Column(sa.String)
    benchmark = Column(sa.String)
    fund = Column(sa.String)
    col_12 = Column(sa.String)
    col_13 = Column(sa.String)
    col_14 = Column(sa.String)
    col_15 = Column(sa.String)
    col_16 = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


class WeightingHistorySheets(Base):
    __tablename__ = "weighting_history_sheets"

    C0 = Column(sa.String)
    name = Column(sa.String)
    sector = Column(sa.String)
    last_price = Column(sa.String)
    five_yr_revenue_cagr = Column(sa.String)
    dividend_yield = Column(sa.String)
    p_fcf = Column(sa.String)
    id = Column(sa.Integer)
    # SQLAlchemy workaround: Adding primary key to id column
    id = Column(sa.Integer, primary_key=True)


TABLE_SCHEMAS = {
    "clean_client_profiles": """CREATE TABLE IF NOT EXISTS clean_client_profiles (
    id INTEGER,
    name VARCHAR,
    email VARCHAR,
    household_id INTEGER,
    primary_data_source VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)""",
    "client_communications_index": """CREATE TABLE IF NOT EXISTS client_communications_index (
    thread_id VARCHAR,
    client_email VARCHAR,
    subject VARCHAR,
    client_message VARCHAR,
    client_msg_id VARCHAR,
    response_msg_id VARCHAR,
    response_message VARCHAR,
    actual_received_time TIMESTAMP,
    actual_response_time TIMESTAMP
)""",
    "client_data_sources": """CREATE TABLE IF NOT EXISTS client_data_sources (
    id INTEGER NOT NULL PRIMARY KEY,
    client_profile_id INTEGER,
    source_type VARCHAR,
    source_id VARCHAR,
    submission_time TIMESTAMP,
    raw_data VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "client_profiles": """CREATE TABLE IF NOT EXISTS client_profiles (
    id INTEGER NOT NULL PRIMARY KEY,
    email VARCHAR,
    name VARCHAR,
    pronouns VARCHAR,
    phone VARCHAR,
    address_street VARCHAR,
    address_apt VARCHAR,
    address_city VARCHAR,
    address_state VARCHAR,
    address_zip VARCHAR,
    address_country VARCHAR,
    occupation VARCHAR,
    employer VARCHAR,
    job_title VARCHAR,
    annual_income VARCHAR,
    birthday DATE,
    marital_status VARCHAR,
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
    interests VARCHAR,
    activist_activities VARCHAR,
    ethical_considerations VARCHAR,
    referral_source VARCHAR,
    referrer_name VARCHAR,
    newsletter_opt_in BOOLEAN,
    contact_preference VARCHAR,
    work_situation VARCHAR,
    additional_notes VARCHAR,
    review_existing_accounts BOOLEAN,
    primary_data_source VARCHAR,
    intake_timestamp TIMESTAMP,
    household_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "contacts": """CREATE TABLE IF NOT EXISTS contacts (
    email VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    full_name VARCHAR,
    company VARCHAR,
    job_title VARCHAR,
    phone VARCHAR,
    country VARCHAR,
    source VARCHAR,
    domain VARCHAR,
    last_interaction_date TIMESTAMP,
    first_seen_date TIMESTAMP,
    last_updated TIMESTAMP,
    tags VARCHAR,
    notes VARCHAR,
    metadata VARCHAR,
    event_id VARCHAR,
    event_summary VARCHAR,
    event_time TIMESTAMP,
    website INTEGER,
    address_1 VARCHAR,
    address_2 INTEGER,
    city VARCHAR,
    state VARCHAR,
    zip INTEGER,
    current_client INTEGER,
    investment_professional INTEGER,
    last_contact INTEGER,
    email_verified INTEGER,
    social_media INTEGER,
    breached_sites INTEGER,
    related_domains INTEGER,
    password_leaks INTEGER,
    pastebin_records INTEGER,
    is_newsletter BOOLEAN,
    is_client BOOLEAN,
    is_free_money BOOLEAN,
    last_outreach INTEGER,
    lead_source INTEGER,
    birthdate INTEGER,
    employment_status INTEGER,
    is_partnered BOOLEAN,
    partner_name INTEGER,
    investment_experience BIGINT,
    social_instagram INTEGER,
    social_linkedin INTEGER,
    social_tiktok INTEGER,
    subscriber_since TIMESTAMP,
    email_opens BIGINT,
    email_clicks BIGINT,
    id INTEGER
)""",
    "contributions": """CREATE TABLE IF NOT EXISTS contributions (
    id INTEGER NOT NULL PRIMARY KEY,
    account VARCHAR,
    household VARCHAR,
    maximum_contribution DOUBLE,
    ytd_contributions DOUBLE,
    projected DOUBLE,
    year INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "diversification_sheets": """CREATE TABLE IF NOT EXISTS diversification_sheets (
    symbol VARCHAR,
    name VARCHAR,
    allocation VARCHAR,
    current_weight VARCHAR,
    target_weight VARCHAR,
    drift VARCHAR,
    market_value VARCHAR,
    last_price VARCHAR,
    shares VARCHAR,
    yield VARCHAR,
    yield_contribution VARCHAR,
    sector VARCHAR,
    country VARCHAR,
    strategy VARCHAR,
    risk_score VARCHAR,
    correlation VARCHAR,
    beta VARCHAR,
    volatility VARCHAR,
    sharpe_ratio VARCHAR,
    notes VARCHAR,
    id INTEGER
)""",
    "email_analyses": """CREATE TABLE IF NOT EXISTS email_analyses (
    msg_id VARCHAR NOT NULL PRIMARY KEY,
    thread_id VARCHAR,
    subject VARCHAR,
    from_address VARCHAR,
    analysis_date TIMESTAMP,
    raw_analysis JSON,
    automation_score FLOAT,
    content_value FLOAT,
    human_interaction FLOAT,
    time_value FLOAT,
    business_impact FLOAT,
    uncertainty_score FLOAT,
    metadata JSON,
    priority INTEGER,
    label_ids JSON,
    snippet VARCHAR,
    internal_date BIGINT,
    size_estimate INTEGER,
    message_parts JSON,
    draft_id VARCHAR,
    draft_message JSON,
    attachments JSON,
    status VARCHAR DEFAULT \'new\',
    error_message VARCHAR,
    batch_id VARCHAR,
    import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "email_feedback": """CREATE TABLE IF NOT EXISTS email_feedback (
    id INTEGER NOT NULL PRIMARY KEY,
    msg_id VARCHAR,
    subject VARCHAR,
    original_priority INTEGER,
    assigned_priority INTEGER,
    suggested_priority INTEGER,
    feedback_comments VARCHAR,
    add_to_topics VARCHAR,
    timestamp TIMESTAMP
)""",
    "email_preferences": """CREATE TABLE IF NOT EXISTS email_preferences (
    id INTEGER NOT NULL PRIMARY KEY,
    override_rules VARCHAR,
    topic_weight DOUBLE,
    sender_weight DOUBLE,
    content_value_weight DOUBLE,
    sender_history_weight DOUBLE,
    priority_map VARCHAR,
    timestamp TIMESTAMP
)""",
    "emails": """CREATE TABLE IF NOT EXISTS emails (
    msg_id VARCHAR NOT NULL PRIMARY KEY,
    thread_id VARCHAR,
    subject VARCHAR,
    from_address VARCHAR,
    analysis_date TIMESTAMP,
    raw_analysis JSON,
    automation_score FLOAT,
    content_value FLOAT,
    human_interaction FLOAT,
    time_value FLOAT,
    business_impact FLOAT,
    uncertainty_score FLOAT,
    metadata JSON,
    priority INTEGER,
    label_ids JSON,
    snippet VARCHAR,
    internal_date BIGINT,
    size_estimate INTEGER,
    message_parts JSON,
    draft_id VARCHAR,
    draft_message JSON,
    attachments JSON,
    status VARCHAR DEFAULT \'new\',
    error_message VARCHAR,
    batch_id VARCHAR,
    import_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "entity_analytics": """CREATE TABLE IF NOT EXISTS entity_analytics (
    id INTEGER,
    category VARCHAR,
    term VARCHAR,
    count INTEGER,
    timestamp VARCHAR,
    context VARCHAR,
    metadata VARCHAR,
    materiality_score DOUBLE,
    confidence_score DOUBLE,
    sentiment_score DOUBLE
)""",
    "exclude_sheets": """CREATE TABLE IF NOT EXISTS exclude_sheets (
    company VARCHAR,
    symbol VARCHAR,
    isin VARCHAR,
    category VARCHAR,
    criteria VARCHAR,
    concerned_groups VARCHAR,
    decision VARCHAR,
    date VARCHAR,
    notes VARCHAR,
    col_9 VARCHAR,
    col_10 VARCHAR,
    id INTEGER
)""",
    "family_offices": """CREATE TABLE IF NOT EXISTS family_offices (
    office_id VARCHAR,
    firm_name VARCHAR,
    contact_first_name VARCHAR,
    contact_last_name VARCHAR,
    contact_title VARCHAR,
    phone_number VARCHAR,
    fax_number VARCHAR,
    email_address VARCHAR,
    company_email VARCHAR,
    street_address VARCHAR,
    city VARCHAR,
    state_province VARCHAR,
    postal_code VARCHAR,
    country VARCHAR,
    investment_areas VARCHAR,
    year_founded VARCHAR,
    aum_mil VARCHAR,
    client_average VARCHAR,
    client_minimum VARCHAR,
    additional_info VARCHAR,
    website VARCHAR,
    etc VARCHAR,
    mf_sf VARCHAR,
    v5_contact VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    id INTEGER,
    aum_numeric DOUBLE
)""",
    "growth_sheets": """CREATE TABLE IF NOT EXISTS growth_sheets (
    tick VARCHAR,
    symbol VARCHAR,
    si VARCHAR,
    name VARCHAR,
    target VARCHAR,
    current VARCHAR,
    position_chg VARCHAR,
    model_portfolio VARCHAR,
    last_close VARCHAR,
    si_sum VARCHAR,
    pct change VARCHAR,
    yield VARCHAR,
    yield_contribution VARCHAR,
    sector VARCHAR,
    country VARCHAR,
    usa VARCHAR,
    asia VARCHAR,
    latam VARCHAR,
    europe VARCHAR,
    real_estate VARCHAR,
    infrastructure VARCHAR,
    innovation VARCHAR,
    lending VARCHAR,
    market_cap_3_11_2024 VARCHAR,
    real_estate_1 VARCHAR,
    infrastructure_1 VARCHAR,
    id INTEGER
)""",
    "holdings": """CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER NOT NULL PRIMARY KEY,
    ticker VARCHAR,
    description VARCHAR,
    aum_percentage DOUBLE,
    price DOUBLE,
    quantity DOUBLE,
    value DOUBLE,
    as_of_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "households": """CREATE TABLE IF NOT EXISTS households (
    id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR,
    num_accounts INTEGER,
    account_groups VARCHAR,
    cash_percentage DOUBLE,
    balance DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""",
    "income_sheets": """CREATE TABLE IF NOT EXISTS income_sheets (
    tick VARCHAR,
    symbol VARCHAR,
    name VARCHAR,
    target VARCHAR,
    current VARCHAR,
    model_portfolio VARCHAR,
    drift VARCHAR,
    last_close VARCHAR,
    yield VARCHAR,
    yield_cont VARCHAR,
    social_impact VARCHAR,
    sustainable_infrastructure VARCHAR,
    energy_infrastructure VARCHAR,
    private_companies VARCHAR,
    public_companies VARCHAR,
    social_impact_1 VARCHAR,
    infrastructure VARCHAR,
    private_companies_1 VARCHAR,
    public_companies_1 VARCHAR,
    legacy_exposure VARCHAR,
    duration VARCHAR,
    id INTEGER
)""",
    "markdown_sections": """CREATE TABLE IF NOT EXISTS markdown_sections (
    id INTEGER,
    title VARCHAR,
    content VARCHAR,
    section_type VARCHAR,
    source_file VARCHAR,
    created_at TIMESTAMP,
    word_count INTEGER,
    sentiment VARCHAR,
    has_pii BOOLEAN,
    readability VARCHAR,
    avg_sentence_length FLOAT
)""",
    "master_clients": """CREATE TABLE IF NOT EXISTS master_clients (
    client_id INTEGER,
    name VARCHAR,
    email VARCHAR,
    phone VARCHAR,
    pronouns VARCHAR,
    full_address VARCHAR,
    occupation VARCHAR,
    employer VARCHAR,
    job_title VARCHAR,
    annual_income VARCHAR,
    birthday DATE,
    marital_status VARCHAR,
    net_worth VARCHAR,
    investment_experience VARCHAR,
    investment_goals VARCHAR,
    risk_tolerance VARCHAR,
    preferred_investment_amount VARCHAR,
    preferred_account_types VARCHAR,
    interests VARCHAR,
    ethical_considerations VARCHAR,
    contact_preference VARCHAR,
    primary_data_source VARCHAR,
    intake_timestamp TIMESTAMP,
    household_id VARCHAR,
    company VARCHAR,
    contact_last_interaction TIMESTAMP,
    contact_tags VARCHAR,
    contact_notes VARCHAR,
    newsletter_subscriber BOOLEAN,
    email_opens BIGINT,
    email_clicks BIGINT,
    last_email_date TIMESTAMP,
    recent_email_subjects VARCHAR[],
    account_groups VARCHAR,
    portfolios VARCHAR,
    total_balance DOUBLE,
    num_accounts BIGINT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)""",
    "observe_sheets": """CREATE TABLE IF NOT EXISTS observe_sheets (
    col_0 VARCHAR,
    col_1 VARCHAR,
    col_2 VARCHAR,
    col_3 VARCHAR,
    col_4 VARCHAR,
    col_5 VARCHAR,
    col_6 VARCHAR,
    col_7 VARCHAR,
    col_8 VARCHAR,
    col_9 VARCHAR,
    id INTEGER
)""",
    "open_accounts": """CREATE TABLE IF NOT EXISTS open_accounts (
    id INTEGER NOT NULL PRIMARY KEY,
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
)""",
    "overview_tables_sheets": """CREATE TABLE IF NOT EXISTS overview_tables_sheets (
    col_0 VARCHAR,
    col_1 VARCHAR,
    col_2 VARCHAR,
    col_3 VARCHAR,
    col_4 VARCHAR,
    col_5 VARCHAR,
    col_6 VARCHAR,
    col_7 VARCHAR,
    col_8 VARCHAR,
    col_9 VARCHAR,
    col_10 VARCHAR,
    col_11 VARCHAR,
    col_12 VARCHAR,
    col_13 VARCHAR,
    col_14 VARCHAR,
    col_15 VARCHAR,
    col_16 VARCHAR,
    col_17 VARCHAR,
    col_18 VARCHAR,
    col_19 VARCHAR,
    id INTEGER
)""",
    "podcast_episodes": """CREATE TABLE IF NOT EXISTS podcast_episodes (
    title VARCHAR,
    link VARCHAR,
    published TIMESTAMP,
    description VARCHAR,
    audio_url VARCHAR,
    audio_type VARCHAR,
    audio_length BIGINT,
    duration_minutes DOUBLE,
    transcript VARCHAR,
    created_at TIMESTAMP,
    id INTEGER
)""",
    "portfolio_screener_sheets": """CREATE TABLE IF NOT EXISTS portfolio_screener_sheets (
    col_0 VARCHAR,
    col_1 VARCHAR,
    col_2 VARCHAR,
    col_3 VARCHAR,
    col_4 VARCHAR,
    col_5 VARCHAR,
    col_6 VARCHAR,
    col_7 VARCHAR,
    col_8 VARCHAR,
    col_9 VARCHAR,
    id INTEGER
)""",
    "preferreds_sheets": """CREATE TABLE IF NOT EXISTS preferreds_sheets (
    symbol
cusip VARCHAR,
    symbol VARCHAR,
    tick VARCHAR,
    note VARCHAR,
    C4 VARCHAR,
    security_description VARCHAR,
    ipo_date VARCHAR,
    cpn_rate
ann_amt VARCHAR,
    liqpref
callprice VARCHAR,
    call_date
matur_date VARCHAR,
    moodys_s&p
dated VARCHAR,
    15pct
tax_rate VARCHAR,
    conv VARCHAR,
    ipo_prospectus VARCHAR,
    distribution_dates VARCHAR,
    id INTEGER
)""",
    "research_analyses": """CREATE TABLE IF NOT EXISTS research_analyses (
    id INTEGER NOT NULL PRIMARY KEY,
    company VARCHAR,
    timestamp TIMESTAMP,
    content VARCHAR,
    summary VARCHAR,
    ethical_score FLOAT,
    risk_level VARCHAR
)""",
    "research_iterations": """CREATE TABLE IF NOT EXISTS research_iterations (
    id BIGINT,
    company_ticker VARCHAR,
    iteration_type VARCHAR,
    source_count INTEGER,
    date_range INTEGER,
    previous_iteration_id INTEGER,
    summary VARCHAR,
    key_changes INTEGER,
    risk_factors VARCHAR,
    opportunities INTEGER,
    confidence_metrics VARCHAR,
    status VARCHAR,
    reviewer_notes VARCHAR,
    reviewed_by INTEGER,
    reviewed_at TIMESTAMP,
    prompt_template INTEGER,
    model_version INTEGER,
    created_at TIMESTAMP
)""",
    "research_results": """CREATE TABLE IF NOT EXISTS research_results (
    id BIGINT,
    company_ticker VARCHAR,
    summary VARCHAR,
    risk_score INTEGER,
    confidence_score INTEGER,
    recommendation VARCHAR,
    structured_data VARCHAR,
    raw_results VARCHAR,
    search_queries VARCHAR,
    source_date_range INTEGER,
    total_sources INTEGER,
    source_categories VARCHAR,
    last_iteration_id INTEGER,
    first_analyzed_at TIMESTAMP,
    last_updated_at TIMESTAMP,
    meta_info VARCHAR
)""",
    "research_search_results": """CREATE TABLE IF NOT EXISTS research_search_results (
    id INTEGER NOT NULL PRIMARY KEY,
    search_id INTEGER,
    timestamp TIMESTAMP,
    title VARCHAR,
    link VARCHAR,
    snippet VARCHAR,
    source VARCHAR
)""",
    "research_searches": """CREATE TABLE IF NOT EXISTS research_searches (
    id INTEGER NOT NULL PRIMARY KEY,
    timestamp TIMESTAMP,
    query VARCHAR,
    num_results INTEGER
)""",
    "research_sources": """CREATE TABLE IF NOT EXISTS research_sources (
    id BIGINT,
    ticker VARCHAR,
    url VARCHAR,
    title VARCHAR,
    snippet VARCHAR,
    source_type VARCHAR,
    category VARCHAR,
    created_at TIMESTAMP
)""",
    "risk_based_portfolios_sheets": """CREATE TABLE IF NOT EXISTS risk_based_portfolios_sheets (
    col_0 VARCHAR,
    col_1 VARCHAR,
    col_2 VARCHAR,
    col_3 VARCHAR,
    col_4 VARCHAR,
    col_5 VARCHAR,
    col_6 VARCHAR,
    col_7 VARCHAR,
    col_8 VARCHAR,
    col_9 VARCHAR,
    col_10 VARCHAR,
    col_11 VARCHAR,
    id INTEGER
)""",
    "tick_history_sheets": """CREATE TABLE IF NOT EXISTS tick_history_sheets (
    ticker VARCHAR,
    old_tick VARCHAR,
    new_tick VARCHAR,
    date VARCHAR,
    isin VARCHAR,
    month VARCHAR,
    year VARCHAR,
    monthyear VARCHAR,
    id INTEGER
)""",
    "universe_sheets": """CREATE TABLE IF NOT EXISTS universe_sheets (
    excluded VARCHAR,
    workflow VARCHAR,
    ticker VARCHAR,
    isin VARCHAR,
    tick VARCHAR,
    security_name VARCHAR,
    note VARCHAR,
    last_tick_date VARCHAR,
    category VARCHAR,
    sector VARCHAR,
    benchmark VARCHAR,
    fund VARCHAR,
    col_12 VARCHAR,
    col_13 VARCHAR,
    col_14 VARCHAR,
    col_15 VARCHAR,
    col_16 VARCHAR,
    id INTEGER
)""",
    "weighting_history_sheets": """CREATE TABLE IF NOT EXISTS weighting_history_sheets (
    C0 VARCHAR,
    name VARCHAR,
    sector VARCHAR,
    last_price VARCHAR,
    5yr_revenue_cagr VARCHAR,
    dividend_yield VARCHAR,
    p_fcf VARCHAR,
    id INTEGER
)""",
}


TABLE_INDEXES = {
    "client_data_sources": [
        """CREATE INDEX IF NOT EXISTS idx_client_data_sources_id ON client_data_sources(id)""",
    ],
    "client_profiles": [
        """CREATE INDEX IF NOT EXISTS idx_client_profiles_id ON client_profiles(id)""",
    ],
    "contributions": [
        """CREATE INDEX IF NOT EXISTS idx_contributions_id ON contributions(id)""",
    ],
    "email_analyses": [
        """CREATE INDEX IF NOT EXISTS idx_email_analyses_msg_id ON email_analyses(msg_id)""",
    ],
    "email_feedback": [
        """CREATE INDEX IF NOT EXISTS idx_email_feedback_id ON email_feedback(id)""",
    ],
    "email_preferences": [
        """CREATE INDEX IF NOT EXISTS idx_email_preferences_id ON email_preferences(id)""",
    ],
    "emails": [
        """CREATE INDEX IF NOT EXISTS idx_emails_msg_id ON emails(msg_id)""",
    ],
    "holdings": [
        """CREATE INDEX IF NOT EXISTS idx_holdings_id ON holdings(id)""",
    ],
    "households": [
        """CREATE INDEX IF NOT EXISTS idx_households_id ON households(id)""",
    ],
    "open_accounts": [
        """CREATE INDEX IF NOT EXISTS idx_open_accounts_id ON open_accounts(id)""",
    ],
    "research_analyses": [
        """CREATE INDEX IF NOT EXISTS idx_research_analyses_id ON research_analyses(id)""",
    ],
    "research_search_results": [
        """CREATE INDEX IF NOT EXISTS idx_research_search_results_id ON research_search_results(id)""",
    ],
    "research_searches": [
        """CREATE INDEX IF NOT EXISTS idx_research_searches_id ON research_searches(id)""",
    ],
}
