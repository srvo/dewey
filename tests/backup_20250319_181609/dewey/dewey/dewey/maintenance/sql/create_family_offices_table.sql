-- Create Family Offices table based on the structure of "List for Sloane.xlsx - FOD V5.csv"
CREATE TABLE IF NOT EXISTS family_offices (
    office_id INTEGER,                -- Office #
    firm_name TEXT,                   -- Firm Name
    contact_first_name TEXT,          -- Contact First Name
    contact_last_name TEXT,           -- Contact Last Name
    contact_title TEXT,               -- Contact Title/Position
    phone_number TEXT,                -- Phone Number
    fax_number TEXT,                  -- Fax Number
    email_address TEXT,               -- Email Address
    company_email TEXT,               -- Company Email Address
    street_address TEXT,              -- Company Street Address
    city TEXT,                        -- City
    state_province TEXT,              -- State/Province
    postal_code TEXT,                 -- Postal/Zip Code
    country TEXT,                     -- Country
    investment_areas TEXT,            -- Company's Areas of Investments/Interest
    year_founded INTEGER,             -- Year Founded
    aum_mil DOUBLE,                   -- AUM ($US Mil unless otherwise noted)
    client_average DOUBLE,            -- Client Ave
    client_minimum DOUBLE,            -- Client Min
    additional_info TEXT,             -- Additional Company/Contact Information
    website TEXT,                     -- Website
    etc TEXT,                         -- ETC
    mf_sf TEXT,                       -- MF/SF (Multi-Family/Single Family)
    v5_contact TEXT,                  -- V5 Contact
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on key fields
CREATE INDEX IF NOT EXISTS idx_family_offices_id ON family_offices(office_id);
CREATE INDEX IF NOT EXISTS idx_family_offices_name ON family_offices(firm_name);
CREATE INDEX IF NOT EXISTS idx_family_offices_mf_sf ON family_offices(mf_sf);

-- Comment to explain the table's purpose
COMMENT ON TABLE family_offices IS 'Table containing Family Office data, sourced from "List for Sloane.xlsx - FOD V5.csv"'; 