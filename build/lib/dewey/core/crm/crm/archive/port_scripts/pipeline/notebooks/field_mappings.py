# Common variations of field names found across your CSV files
CONTACT_FIELDS = {
    'first_name': [name.lower() for name in [
        'first_name', 'first', 'firstname', 'given_name',
        'contact first name', 'your information - name'  # From FOD V5.csv and onboarding form
    ]],
    'last_name': [name.lower() for name in [
        'last_name', 'last', 'lastname', 'surname',
        'contact last name'  # From FOD V5.csv
    ]],
    'email': [name.lower() for name in [
        'email', 'email_address', 'contact_email', 'e-mail',
        'user email', 'corporate email', 'Email Address',
        'your information - email address'  # From onboarding form
    ]],
    'phone': [
        'phone', 'phone_number', 'contact_phone', 'telephone',
        'primary phone', 'phone type',  # From Entity file
        'your information - phone number'  # From onboarding form
    ],
    'company': [
        'company', 'employer', 'organization', 'firm',
        'firm name', 'entity name'  # From FOD V5 and Entity files
    ],
    'title': [
        'title', 'job_title', 'position', 'job_position',
        'contact title/position',  # From FOD V5
        'your information - title/job position'  # From onboarding form
    ],
    'address': [
        'address', 'street_address', 'mailing_address',
        'primary street', 'street address|address-1-street_address',  # From Entity file
        'your information - address - street address'  # From onboarding form
    ],
    'city': [
        'city', 'municipality',
        'primary city',  # From Entity file
        'your information - address - city'  # From onboarding form
    ],
    'state': [
        'state', 'province', 'state/province',
        'primary state',  # From Entity file
        'your information - address - state/province'  # From onboarding form
    ],
    'zip': [
        'zip', 'postal_code', 'zip_code',
        'primary zip',  # From Entity file
        'your information - address - zip / postal code'  # From onboarding form
    ],
    'pronouns': [
        'pronouns',
        'your information - pronouns'  # From onboarding form
    ],
    'notes': [
        'notes', 'additional company/contact information',
        'bio', 'alert'  # From Entity file
    ]
}